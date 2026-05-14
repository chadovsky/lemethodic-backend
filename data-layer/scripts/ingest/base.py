"""
Base class for source ingestion. Each source script subclasses Ingester.

Provides:
- Download helpers (HTTP + git + huggingface)
- Progress reporting via tqdm
- Batch-committed upserts
- Idempotent re-runs
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterator, Optional

import requests
from sqlalchemy.orm import Session
from tqdm import tqdm

from scripts.common import (
    LICENSE_REGISTRY,
    batch_commit,
    db_session,
    ensure_dirs,
    insert_example,
    load_config,
    setup_logger,
    upsert_chunk,
)


class Ingester(ABC):
    """Base ingester. Subclass and implement the abstract methods."""

    #: Source name as stored in chunk_sources (e.g. 'UniversalCEFR')
    source_name: str = "override_me"

    #: Source version string (e.g. '3.83'). Optional.
    source_version: Optional[str] = None

    #: Batch commit size (rows between commits)
    batch_size: int = 500

    def __init__(self) -> None:
        self.cfg = load_config()
        ensure_dirs()
        self.raw_dir = Path(self.cfg["data"]["raw_dir"]) / self.source_name.lower()
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.log = setup_logger(f"ingest_{self.source_name.lower()}")
        self.license_info = LICENSE_REGISTRY.get(self.source_name, {})

    # -- Subclasses implement these -------------------------------------

    @abstractmethod
    def download(self) -> None:
        """Fetch the raw data into self.raw_dir. Skip if already present."""
        ...

    @abstractmethod
    def iter_rows(self) -> Iterator[dict]:
        """
        Yield one chunk dict per row. Required key: surface_fr.
        Optional keys map to upsert_chunk parameters.
        Optionally yield {'_examples': [{'example_fr':..., 'example_en':...}, ...]}
        for example sentences linked to this chunk.
        """
        ...

    # -- Generic pipeline -----------------------------------------------

    def run(self) -> None:
        self.log.info(f"Starting ingest: {self.source_name}")
        self.download()
        with db_session() as session:
            counter = 0
            for row in tqdm(self.iter_rows(), desc=self.source_name, unit="rows"):
                try:
                    self._upsert_row(session, row)
                    counter += 1
                    if batch_commit(session, self.batch_size, counter):
                        self.log.debug(f"Committed batch at {counter} rows")
                except Exception as e:
                    self.log.error(f"Row failure ({row.get('surface_fr', '?')[:60]}): {e}")
            session.commit()
            self.log.info(f"Ingest complete: {counter} rows processed")

    def _upsert_row(self, session: Session, row: dict) -> None:
        examples = row.pop("_examples", [])
        surface = row.pop("surface_fr", None)
        if not surface or not surface.strip():
            return

        chunk_id = upsert_chunk(
            session=session,
            surface_fr=surface,
            source_name=self.source_name,
            source_version=self.source_version,
            source_license=self.license_info.get("license"),
            contributed_fields=list(row.keys()),
            **row,
        )

        for ex in examples:
            insert_example(
                session=session,
                chunk_id=chunk_id,
                example_fr=ex.get("example_fr", ""),
                example_en=ex.get("example_en"),
                cefr_level=ex.get("cefr_level"),
                source_name=self.source_name,
            )

    # -- Download helpers -----------------------------------------------

    def http_download(self, url: str, dest: Path) -> Path:
        if dest.exists():
            self.log.info(f"Already downloaded: {dest.name}")
            return dest
        self.log.info(f"Downloading {url}")
        r = requests.get(url, stream=True, timeout=30)
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        with open(dest, "wb") as f, tqdm(
            total=total, unit="B", unit_scale=True, desc=dest.name
        ) as bar:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
                bar.update(len(chunk))
        return dest

    def git_clone(self, url: str, dest: Path) -> Path:
        if dest.exists() and (dest / ".git").exists():
            self.log.info(f"Already cloned: {dest}")
            return dest
        self.log.info(f"Cloning {url}")
        subprocess.check_call(["git", "clone", "--depth", "1", url, str(dest)])
        return dest
