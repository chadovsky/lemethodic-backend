"""
CollFrEn ingestion.

Source: https://github.com/TalnUPF/CollFrEn
Bilingual English-French collocations annotated with Mel'cuk lexical
functions and manually disambiguated against BabelNet.

Format: the bilingual data lives in
    data/collocations/french/FR_disambiguated_SyntagmaticLF_v1b.xlsx
sheet `FR_v1_23OCT20_SYNTAGMATIC` (~6.7k rows). Each row pairs a French
KEYWORD (collocation base) with a French VALUE (collocate) plus their
English translations. We assemble (keyword, value) into a single
collocation surface — the position is derived from the postposed/anteposed
subcategorisation columns when present, otherwise we fall back to
keyword-then-value.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator, Optional

import click

from scripts.ingest.base import Ingester

COLLFREN_REPO = "https://github.com/TalnUPF/CollFrEn.git"

# Path inside the cloned repo where the bilingual disambiguated workbook lives.
FR_XLSX_RELPATH = Path("data/collocations/french/FR_disambiguated_SyntagmaticLF_v1b.xlsx")
FR_DATA_SHEET = "FR_v1_23OCT20_SYNTAGMATIC"

# Column indices on the data sheet (0-indexed). Header row is row 0.
COL_LEX_FUNC = 0
COL_KEYWORD = 1
COL_TRANSLATION_KEYW = 2
COL_KEYW_POS = 3
COL_ANTEPOSED = 6
COL_VALUE = 7
COL_TRANSLATION_VAL = 8
COL_TRANSLATION_VAL_2 = 9
COL_POSTPOSED = 10

# Strip CollFrEn annotation markers from a surface form:
#   "_à la tête_"  -> "à la tête"  (canonical-form underscores)
#   "[le] moral"   -> "moral"      (optional articles / placeholders)
#   "[NX ~]"       -> ""           (subcategorisation slots)
_BRACKET_RE = re.compile(r"\[[^\]]*\]")
_UNDERSCORE_RE = re.compile(r"_+")
_WHITESPACE_RE = re.compile(r"\s+")


def _clean(token: Optional[str]) -> str:
    if not token or not isinstance(token, str):
        return ""
    s = _BRACKET_RE.sub(" ", token)
    s = _UNDERSCORE_RE.sub(" ", s)
    s = _WHITESPACE_RE.sub(" ", s).strip()
    return s


def _value_first(postposed: Optional[str]) -> bool:
    """
    Return True when the keyword sits postposed to the value, i.e. the
    surface order is `value keyword`. CollFrEn marks this with `~` (the
    keyword placeholder) inside the postposed/intraposed subcategorisation
    column — patterns such as "[~]", "[ART ~]", "[NX ~]".
    """
    if not postposed or not isinstance(postposed, str):
        return False
    return "~" in postposed


class CollFrEnIngester(Ingester):
    source_name = "CollFrEn"
    source_version = "1.0"
    batch_size = 500

    def download(self) -> None:
        self.repo_dir = self.raw_dir / "repo"
        self.git_clone(COLLFREN_REPO, self.repo_dir)

    def iter_rows(self) -> Iterator[dict]:
        try:
            import openpyxl
        except ImportError as e:
            raise RuntimeError(
                "openpyxl required for CollFrEn ingestion. "
                "Run `pip install -r requirements.txt`."
            ) from e

        xlsx_path = self.repo_dir / FR_XLSX_RELPATH
        if not xlsx_path.exists():
            self.log.error(f"CollFrEn workbook not found at {xlsx_path}")
            return

        self.log.info(f"Reading {xlsx_path} sheet={FR_DATA_SHEET}")
        wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
        if FR_DATA_SHEET not in wb.sheetnames:
            self.log.error(
                f"Expected sheet '{FR_DATA_SHEET}' not found. Available: {wb.sheetnames}"
            )
            return

        ws = wb[FR_DATA_SHEET]
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i == 0:
                continue  # header
            parsed = self._parse_row(row)
            if parsed:
                yield parsed

    def _parse_row(self, row: tuple) -> Optional[dict]:
        if not row or len(row) <= COL_POSTPOSED:
            return None

        lex_func = row[COL_LEX_FUNC]
        keyword_raw = row[COL_KEYWORD]
        value_raw = row[COL_VALUE]

        keyword = _clean(keyword_raw)
        value = _clean(value_raw)
        if not keyword or not value:
            return None

        if _value_first(row[COL_POSTPOSED]):
            surface_fr = f"{value} {keyword}"
        else:
            surface_fr = f"{keyword} {value}"

        translation_keyw = _clean(row[COL_TRANSLATION_KEYW])
        translation_val = _clean(row[COL_TRANSLATION_VAL])
        if translation_keyw and translation_val:
            if _value_first(row[COL_POSTPOSED]):
                surface_en = f"{translation_val} {translation_keyw}"
            else:
                surface_en = f"{translation_keyw} {translation_val}"
        else:
            surface_en = translation_keyw or translation_val or None

        # Map CollFrEn's coarse keyword POS tag (N/V/R/A) to a chunk_type.
        # Mel'cuk lexical functions are inherently collocational so we tag
        # everything as `collocation` — finer typing happens at enrichment.
        return {
            "surface_fr": surface_fr,
            "surface_en": surface_en or None,
            "language": "fr",
            "chunk_type": "collocation",
            "pos_pattern": lex_func if isinstance(lex_func, str) and lex_func else None,
        }


@click.command()
@click.option("--config", default="config.yml")
def main(config: str) -> None:
    CollFrEnIngester().run()


if __name__ == "__main__":
    main()
