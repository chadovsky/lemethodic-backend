"""
Anki deck ingestion.

Source: AnkiWeb shared decks (manually downloaded by user; see manifest).
Format: .apkg is a zip containing collection.anki2 (SQLite) and media files.

SKELETON — each deck has its own field layout. User maintains a per-deck
config in raw/anki/manifest.yml.
"""

from __future__ import annotations

import json
import sqlite3
import zipfile
from pathlib import Path
from typing import Iterator

import click
import yaml

from scripts.ingest.base import Ingester


class AnkiIngester(Ingester):
    source_name = "AnkiWeb"
    source_version = "user_curated"
    batch_size = 200

    def download(self) -> None:
        # User manually downloads .apkg files to raw/anki/ before running.
        # Verify presence and read the manifest.
        manifest_path = self.raw_dir / "manifest.yml"
        if not manifest_path.exists():
            raise FileNotFoundError(
                f"Anki manifest not found at {manifest_path}. "
                "Create it with one entry per .apkg file describing fields. "
                "See raw/anki/manifest.example.yml in this repo."
            )
        with open(manifest_path, "r", encoding="utf-8") as f:
            self.manifest = yaml.safe_load(f)
        self.log.info(f"Loaded manifest with {len(self.manifest.get('decks', []))} decks")

    def iter_rows(self) -> Iterator[dict]:
        for deck_entry in self.manifest.get("decks", []):
            apkg_path = self.raw_dir / deck_entry["file"]
            if not apkg_path.exists():
                self.log.warning(f"Missing .apkg file: {apkg_path}")
                continue
            self.log.info(f"Processing {deck_entry['name']} from {apkg_path.name}")
            yield from self._iter_deck(apkg_path, deck_entry)

    def _iter_deck(self, apkg_path: Path, deck_entry: dict) -> Iterator[dict]:
        # Extract the .apkg (it's a zip)
        extract_dir = self.raw_dir / apkg_path.stem
        extract_dir.mkdir(exist_ok=True)
        with zipfile.ZipFile(apkg_path, "r") as z:
            z.extractall(extract_dir)

        # Open the Anki SQLite collection
        collection_path = extract_dir / "collection.anki2"
        if not collection_path.exists():
            self.log.warning(f"No collection.anki2 in {apkg_path}")
            return

        conn = sqlite3.connect(str(collection_path))
        try:
            # Anki notes table: `flds` is the field content, separated by \x1f
            rows = conn.execute("SELECT id, flds FROM notes").fetchall()
        finally:
            conn.close()

        self.log.info(f"  {len(rows)} notes in deck")

        # Field mapping from manifest
        # Example deck_entry:
        # {
        #   "file": "french_b2.apkg",
        #   "name": "French B2",
        #   "cefr_level": "B2",
        #   "field_order": ["fr", "en", "ipa", "audio"],
        #   "field_separator": "\x1f"
        # }
        field_order = deck_entry.get("field_order", ["fr", "en"])
        cefr_level = deck_entry.get("cefr_level")
        sep = deck_entry.get("field_separator", "\x1f")

        for _id, flds in rows:
            parts = flds.split(sep)
            mapped = dict(zip(field_order, parts))

            fr = mapped.get("fr", "").strip()
            if not fr:
                continue

            # TODO: Strip HTML tags (Anki cards often have <div>, <br>, [sound:...]).
            fr = _strip_html(fr)
            en = _strip_html(mapped.get("en", ""))

            yield {
                "surface_fr": fr,
                "surface_en": en or None,
                "language": "fr",
                "cefr_level": cefr_level,
                "_examples": [],
            }


def _strip_html(text: str) -> str:
    """Strip HTML tags and Anki-specific markup."""
    import re
    text = re.sub(r"\[sound:[^\]]+\]", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


@click.command()
@click.option("--config", default="config.yml")
def main(config: str) -> None:
    AnkiIngester().run()


if __name__ == "__main__":
    main()
