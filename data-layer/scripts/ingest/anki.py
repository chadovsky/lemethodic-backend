"""
Anki deck ingestion.

Source: AnkiWeb shared decks (manually downloaded by user; see manifest).
Format: .apkg is a zip containing collection.anki2 (SQLite) and media files.

SKELETON — each deck has its own field layout. User maintains a per-deck
config in raw/anki/manifest.yml.
"""

from __future__ import annotations

import html
import json
import re
import sqlite3
import zipfile
from collections import Counter
from pathlib import Path
from typing import Iterator, Optional

import click
import yaml

from scripts.ingest.base import Ingester


class AnkiIngester(Ingester):
    source_name = "AnkiWeb"
    source_version = "user_curated"
    batch_size = 200

    def __init__(self) -> None:
        super().__init__()
        # Override Ingester's derived raw_dir (raw/ankiweb/) to match the
        # documented drop path (raw/anki/) used throughout this module.
        self.raw_dir = Path(self.cfg["data"]["raw_dir"]) / "anki"
        self.raw_dir.mkdir(parents=True, exist_ok=True)

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
        extract_dir = self.raw_dir / apkg_path.stem
        extract_dir.mkdir(exist_ok=True)
        with zipfile.ZipFile(apkg_path, "r") as z:
            z.extractall(extract_dir)

        collection_path = extract_dir / "collection.anki2"
        if not collection_path.exists():
            self.log.warning(f"No collection.anki2 in {apkg_path}")
            return

        conn = sqlite3.connect(str(collection_path))
        try:
            # col.models is a JSON blob mapping model_id -> model definition.
            # We need the model name for each note so the manifest can map
            # per-model field orderings (a single .apkg may bundle several
            # note types, each with its own field layout).
            models_json = conn.execute("SELECT models FROM col").fetchone()[0]
            models = json.loads(models_json)
            mid_to_name = {int(mid): m.get("name", "") for mid, m in models.items()}
            rows = conn.execute("SELECT id, mid, flds FROM notes").fetchall()
        finally:
            conn.close()

        self.log.info(f"  {len(rows)} notes across {len(mid_to_name)} model(s)")

        cefr_level = deck_entry.get("cefr_level")
        sep = deck_entry.get("field_separator", "\x1f")
        per_model_cfg = deck_entry.get("models") or {}
        default_field_order = deck_entry.get("field_order")

        skipped_by_model: Counter[str] = Counter()
        emitted_by_model: Counter[str] = Counter()

        for _id, mid, flds in rows:
            model_name = mid_to_name.get(int(mid), "")
            field_order = _resolve_field_order(
                model_name, per_model_cfg, default_field_order
            )
            if field_order is None:
                skipped_by_model[model_name] += 1
                continue

            mapped = _map_fields(flds.split(sep), field_order)
            fr = _strip_html(mapped.get("fr", ""))
            if not fr:
                skipped_by_model[model_name] += 1
                continue
            en = _strip_html(mapped.get("en", "")) or None

            emitted_by_model[model_name] += 1
            yield {
                "surface_fr": fr,
                "surface_en": en,
                "language": "fr",
                "cefr_level": cefr_level,
                "_examples": [],
            }

        for name, n in emitted_by_model.most_common():
            self.log.info(f"  emitted {n} from model {name!r}")
        for name, n in skipped_by_model.most_common():
            self.log.info(f"  skipped {n} from model {name!r} (no mapping or empty fr)")


def _resolve_field_order(
    model_name: str,
    per_model_cfg: dict,
    default_field_order: Optional[list],
) -> Optional[list]:
    """Return field_order for this model, or None if the model is unmapped.

    Lookup order:
      1. `models[<model_name>].field_order` (exact match)
      2. deck-level `field_order` fallback
      3. None -> skip
    """
    model_cfg = per_model_cfg.get(model_name)
    if model_cfg and model_cfg.get("field_order"):
        return model_cfg["field_order"]
    return default_field_order


def _map_fields(parts: list, field_order: list) -> dict:
    """Map field-content slots onto named keys. `_` / null = skip slot."""
    mapped: dict = {}
    for slot_name, value in zip(field_order, parts):
        if not slot_name or slot_name == "_":
            continue
        mapped[slot_name] = value
    return mapped


# Anki cards routinely embed: HTML tags, [sound:foo.mp3] / [image:bar.jpg] /
# [type:fr] markers, {{c1::word::hint}} cloze syntax, named HTML entities
# (&nbsp;, &amp;), <style>/<script> blocks with CSS or JS, and stray
# whitespace from the template's <div> wrapping. The stripper handles all of
# them so the resulting surface form is the bare French text.

_RE_STYLE_SCRIPT = re.compile(r"<(style|script)\b[^>]*>.*?</\1\s*>", re.DOTALL | re.IGNORECASE)
_RE_MEDIA_MARKER = re.compile(r"\[(?:sound|image|type|anki)[^]]*\]", re.IGNORECASE)
_RE_CLOZE = re.compile(r"\{\{c\d+::(.*?)(?:::[^}]*)?\}\}", re.DOTALL)
_RE_TAG = re.compile(r"<[^>]+>")
_RE_WS = re.compile(r"\s+")


def _strip_html(text: str) -> str:
    """Strip HTML tags, Anki-specific markup, and collapse whitespace."""
    if not text:
        return ""
    text = _RE_STYLE_SCRIPT.sub(" ", text)
    text = _RE_MEDIA_MARKER.sub(" ", text)
    text = _RE_CLOZE.sub(r"\1", text)
    text = _RE_TAG.sub(" ", text)
    text = html.unescape(text)
    return _RE_WS.sub(" ", text).strip()


@click.command()
@click.option("--config", default="config.yml")
def main(config: str) -> None:
    AnkiIngester().run()


if __name__ == "__main__":
    main()
