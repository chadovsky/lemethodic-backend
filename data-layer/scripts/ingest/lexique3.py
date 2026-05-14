"""
Lexique3 ingestion.

Source: http://www.lexique.org/databases/Lexique383/Lexique383.tsv
~140k French word forms with frequency, lemma, POS, phonology, etc.

This is the second full template, demonstrating CSV/TSV ingestion.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import click
import pandas as pd

from scripts.ingest.base import Ingester

LEXIQUE_URL = "http://www.lexique.org/databases/Lexique383/Lexique383.tsv"

# Map of Lexique POS codes → our pos_pattern conventions
POS_MAP = {
    "VER": "VERB",
    "NOM": "NOUN",
    "ADJ": "ADJ",
    "ADV": "ADV",
    "PRE": "PREP",
    "ART:def": "DET",
    "ART:ind": "DET",
    "PRO:per": "PRON",
    "PRO:dem": "PRON",
    "PRO:pos": "PRON",
    "CON": "CONJ",
}


class Lexique3Ingester(Ingester):
    source_name = "Lexique3"
    source_version = "3.83"
    batch_size = 2000

    def download(self) -> None:
        self.tsv_path = self.raw_dir / "Lexique383.tsv"
        self.http_download(LEXIQUE_URL, self.tsv_path)

    def iter_rows(self) -> Iterator[dict]:
        self.log.info(f"Reading {self.tsv_path}")
        df = pd.read_csv(
            self.tsv_path,
            sep="\t",
            low_memory=False,
            encoding="utf-8",
            on_bad_lines="skip",
        )
        self.log.info(f"Loaded {len(df)} rows from Lexique3")

        # Lexique fields:
        # ortho, phon, lemme, cgram, genre, nombre, freqlemfilms2, freqlemlivres,
        # freqfilms2, freqlivres, infover, nbhomogr, nbhomoph, islem, nblettres,
        # nbphons, cvcv, p_cvcv, voisorth, voisphon, puorth, puphon, syll,
        # nbsyll, cv-cv, orthrenv, phonrenv, orthosyll, cgramortho, deflem,
        # defobs, old20, pld20, morphoder, nbmorph

        for _, row in df.iterrows():
            ortho = row.get("ortho")
            if not isinstance(ortho, str) or not ortho.strip():
                continue

            yield {
                "surface_fr": ortho.strip(),
                "lemma_fr": str(row.get("lemme", "")).strip() or None,
                "language": "fr",
                "pos_pattern": POS_MAP.get(str(row.get("cgram", "")).strip(), None),
                "frequency_subtitles": _safe_float(row.get("freqlemfilms2")),
                "frequency_books": _safe_float(row.get("freqlemlivres")),
            }


def _safe_float(v) -> float | None:
    try:
        f = float(v)
        if pd.isna(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


@click.command()
@click.option("--config", default="config.yml")
def main(config: str) -> None:
    Lexique3Ingester().run()


if __name__ == "__main__":
    main()
