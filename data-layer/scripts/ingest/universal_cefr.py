"""
UniversalCEFR ingestion via HuggingFace datasets.

Source: https://huggingface.co/UniversalCEFR
505k CEFR-labeled texts across 13 languages including FR/EN/ES/PT/AR.

This is the FULL TEMPLATE — other source scripts follow this pattern.
"""

from __future__ import annotations

import sys
from typing import Iterator

import click

from scripts.ingest.base import Ingester

# Map of language → list of dataset names on UniversalCEFR org.
# The actual list of UniversalCEFR datasets evolves; query the HF Hub when
# you run this for the first time and update this dict.
# Each entry: (dataset_name, split, language_code)
SOURCES = {
    "fr": [
        ("UniversalCEFR/cefr_sp_fr", "train", "fr"),
        # Add more FR datasets discovered during F3.1.2 here.
    ],
    "en": [
        ("UniversalCEFR/cefr_sp_en", "train", "en"),
    ],
    "es": [
        ("UniversalCEFR/cefr_sp_es", "train", "es"),
    ],
    "pt": [
        ("UniversalCEFR/cefr_sp_pt", "train", "pt"),
    ],
    "ar": [
        ("UniversalCEFR/cefr_sp_ar", "train", "ar"),
    ],
}


class UniversalCEFRIngester(Ingester):
    source_name = "UniversalCEFR"
    source_version = "2024.1"
    batch_size = 500

    def __init__(self, languages: list[str] | None = None) -> None:
        super().__init__()
        primary = self.cfg["languages"]["primary"]
        others = self.cfg["languages"].get("others", [])
        self.languages = languages or [primary] + list(others)

    def download(self) -> None:
        """HuggingFace `datasets` library handles caching automatically."""
        # No explicit download — the iterator does it lazily.
        # We just verify the datasets library is importable.
        try:
            import datasets  # noqa: F401
        except ImportError:
            raise RuntimeError(
                "datasets library not installed. Run `pip install -r requirements.txt`."
            )
        self.log.info(f"Will pull from HuggingFace for languages: {self.languages}")

    def iter_rows(self) -> Iterator[dict]:
        from datasets import load_dataset

        for lang in self.languages:
            datasets_for_lang = SOURCES.get(lang, [])
            if not datasets_for_lang:
                self.log.warning(f"No UniversalCEFR datasets configured for language '{lang}', skipping")
                continue

            for dataset_name, split, lang_code in datasets_for_lang:
                self.log.info(f"Loading {dataset_name} [{split}]")
                try:
                    ds = load_dataset(dataset_name, split=split, streaming=False)
                except Exception as e:
                    self.log.error(f"Failed to load {dataset_name}: {e}")
                    continue

                self.log.info(f"  {len(ds)} rows in {dataset_name}")
                for row in ds:
                    parsed = self._parse_row(row, lang_code)
                    if parsed:
                        yield parsed

    def _parse_row(self, row: dict, lang_code: str) -> dict | None:
        """
        Map UniversalCEFR row → chunk dict.

        UniversalCEFR rows typically have fields like 'text', 'label' (CEFR),
        'language', 'source_dataset'. Exact schema varies per sub-dataset;
        adjust here as you encounter variants.
        """
        # Find the text content (field name varies)
        surface = (
            row.get("text")
            or row.get("sentence")
            or row.get("content")
            or row.get("input")
        )
        if not surface or not isinstance(surface, str):
            return None
        surface = surface.strip()
        if len(surface) > 200:
            # UniversalCEFR has long paragraphs; we want chunks/sentences.
            # Long passages stay as examples but not as chunks.
            # For now, skip; could be split into sentences in a v2.
            return None

        # Find the CEFR level (field name varies)
        cefr = (
            row.get("label")
            or row.get("cefr")
            or row.get("cefr_level")
            or row.get("level")
        )
        if isinstance(cefr, int):
            # Some datasets encode CEFR as int 0..5 = A1..C2
            cefr = ["A1", "A2", "B1", "B2", "C1", "C2"][cefr] if 0 <= cefr <= 5 else None
        elif isinstance(cefr, str):
            cefr = cefr.upper().strip()
            if cefr not in ("A1", "A2", "B1", "B2", "C1", "C2"):
                cefr = None

        return {
            "surface_fr": surface if lang_code == "fr" else surface,  # noqa
            "language": lang_code,
            "cefr_level": cefr,
        }


@click.command()
@click.option("--config", default="config.yml", help="Path to config.yml")
@click.option("--language", multiple=True, help="Override languages from config")
def main(config: str, language: tuple) -> None:
    langs = list(language) if language else None
    UniversalCEFRIngester(languages=langs).run()


if __name__ == "__main__":
    main()
