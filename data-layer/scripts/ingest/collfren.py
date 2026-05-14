"""
CollFrEn ingestion.

Source: https://github.com/TalnUPF/CollFrEn
Bilingual English-French collocations with translations.

SKELETON — inspect the repo's notebooks/ folder for the actual JSON/CSV
format, then fill in `iter_rows`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

import click

from scripts.ingest.base import Ingester

COLLFREN_REPO = "https://github.com/TalnUPF/CollFrEn.git"


class CollFrEnIngester(Ingester):
    source_name = "CollFrEn"
    source_version = "1.0"
    batch_size = 500

    def download(self) -> None:
        self.repo_dir = self.raw_dir / "repo"
        self.git_clone(COLLFREN_REPO, self.repo_dir)

    def iter_rows(self) -> Iterator[dict]:
        # TODO: Identify the actual data file location in the cloned repo.
        # Inspect: repo_dir / "data/" or "datasets/" or look at notebooks/
        # for loader code. Typical fields: fr_chunk, en_chunk, lexical_function,
        # fr_base, fr_collocate, etc.

        data_files = list(self.repo_dir.rglob("*.json")) + list(self.repo_dir.rglob("*.tsv"))
        if not data_files:
            self.log.warning(f"No data files found in {self.repo_dir}. Inspect manually.")
            return

        for data_file in data_files:
            self.log.info(f"Reading {data_file}")
            # TODO: branch on file extension and parse accordingly.
            # The following is illustrative — adjust to actual CollFrEn schema.
            if data_file.suffix == ".json":
                with open(data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for entry in data if isinstance(data, list) else data.get("entries", []):
                    parsed = self._parse_entry(entry)
                    if parsed:
                        yield parsed

    def _parse_entry(self, entry: dict) -> dict | None:
        """
        TODO: Map CollFrEn entry → chunk dict.

        Expected entry shape (illustrative, adjust to actual):
        {
          "fr_chunk": "faire la queue",
          "en_chunk": "wait in line",
          "fr_base": "queue",
          "fr_collocate": "faire",
          "lexical_function": "Real1",
          "examples_fr": ["...", "..."],
          "examples_en": ["...", "..."]
        }
        """
        fr = entry.get("fr_chunk") or entry.get("fr") or entry.get("source_fr")
        en = entry.get("en_chunk") or entry.get("en") or entry.get("target_en")

        if not fr or not isinstance(fr, str):
            return None

        examples = []
        for ex_fr, ex_en in zip(
            entry.get("examples_fr", []),
            entry.get("examples_en", []) or [None] * len(entry.get("examples_fr", [])),
        ):
            examples.append({"example_fr": ex_fr, "example_en": ex_en})

        return {
            "surface_fr": fr,
            "surface_en": en,
            "language": "fr",
            "chunk_type": "collocation",
            "_examples": examples,
        }


@click.command()
@click.option("--config", default="config.yml")
def main(config: str) -> None:
    CollFrEnIngester().run()


if __name__ == "__main__":
    main()
