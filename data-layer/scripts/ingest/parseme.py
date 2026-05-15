"""
PARSEME ingestion.

Source: https://gitlab.com/parseme/parseme_corpus_fr (+ multilingual companions)
Verbal MWE corpus with categories: idioms, light verb constructions, etc.

.cupt format = CoNLL-U with one extra column (11) carrying the MWE annotation.
Each sentence is a tab-separated block separated by a blank line. The MWE
column is '*' for none, 'N:TYPE' for the head token of MWE N, or 'N' for a
continuation token (potentially with ';' separating multiple MWE memberships).
Tokens belonging to the same MWE id within a sentence are grouped into a
single chunk; discontinuous spans are concatenated in sentence order.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import click

from scripts.ingest.base import Ingester

PARSEME_REPOS = {
    "fr": "https://gitlab.com/parseme/parseme_corpus_fr.git",
    # Add EN, ES, PT once you verify they exist on parseme org.
}

# Map PARSEME MWE categories → our chunk_type values
MWE_TYPE_MAP = {
    "VID": "idiom",            # verbal idiom
    "IRV": "reflexive",        # inherently reflexive verb
    "LVC.full": "light_verb",  # light verb construction (full)
    "LVC.cause": "light_verb", # light verb construction (causative)
    "VPC.full": "phrasal_verb",
    "VPC.semi": "phrasal_verb",
    "MVC": "fixed_expression",
    "IAV": "fixed_expression",
}


class PARSEMEIngester(Ingester):
    source_name = "PARSEME"
    source_version = "1.3"
    batch_size = 500

    def __init__(self, language: str = "fr"):
        super().__init__()
        self.language = language

    def download(self) -> None:
        repo_url = PARSEME_REPOS.get(self.language)
        if not repo_url:
            raise ValueError(f"No PARSEME repo configured for {self.language}")
        self.repo_dir = self.raw_dir / self.language
        self.git_clone(repo_url, self.repo_dir)

    def iter_rows(self) -> Iterator[dict]:
        # Layout varies across PARSEME repos: typically <repo>/<lang>/{train,dev,test}.cupt,
        # but some ship a flat tree or use uppercase. rglob + a case-insensitive
        # fallback handles every variant.
        cupt_files = list(self.repo_dir.rglob("*.cupt"))
        if not cupt_files:
            cupt_files = [
                p for p in self.repo_dir.rglob("*")
                if p.is_file() and p.suffix.lower() == ".cupt"
            ]
        if not cupt_files:
            self.log.warning(f"No .cupt files found in {self.repo_dir}")
            return

        self.log.info(f"Found {len(cupt_files)} .cupt files")
        for cupt_path in sorted(cupt_files):
            self.log.info(f"  parsing {cupt_path.relative_to(self.repo_dir)}")
            yield from self._parse_cupt(cupt_path)

    def _parse_cupt(self, path: Path) -> Iterator[dict]:
        """
        Parse one .cupt file. Each MWE annotation becomes a chunk.

        .cupt format:
        - Sentence-aligned blocks separated by blank lines.
        - Each line: token_id<TAB>form<TAB>lemma<TAB>upos<TAB>xpos<TAB>feats<TAB>head<TAB>deprel<TAB>deps<TAB>misc<TAB>parseme_mwe
        - MWE column: '*' for nothing, or 'N:TYPE' for MWE start, or 'N' for continuation, where N is the MWE id within the sentence.
        """
        with open(path, "r", encoding="utf-8") as f:
            sentence_tokens: list[dict] = []
            for line in f:
                line = line.rstrip("\n")
                if not line:
                    # End of sentence
                    yield from self._extract_mwes(sentence_tokens)
                    sentence_tokens = []
                    continue
                if line.startswith("#"):
                    continue
                cols = line.split("\t")
                if len(cols) < 11:
                    continue
                # Skip multi-word token ranges ("1-2") and empty nodes ("1.1");
                # only keep real, integer-indexed surface tokens — PARSEME MWE
                # annotations live on the integer rows.
                tok_id = cols[0]
                if "-" in tok_id or "." in tok_id:
                    continue
                try:
                    position = int(tok_id)
                except ValueError:
                    continue
                sentence_tokens.append({
                    "id": tok_id,
                    "position": position,
                    "form": cols[1],
                    "lemma": cols[2],
                    "upos": cols[3],
                    "mwe": cols[10],
                })
            # Handle trailing sentence
            if sentence_tokens:
                yield from self._extract_mwes(sentence_tokens)

    def _extract_mwes(self, tokens: list[dict]) -> Iterator[dict]:
        """
        Group tokens by their MWE id and yield one chunk per MWE.

        Discontinuous MWEs (e.g. "se ... demander si" with intervening tokens)
        are reconstructed by concatenating only the tagged member tokens in
        sentence order. The gap is dropped — chunks are stored as canonical
        forms, not as sentence-bound spans. The original sentence remains
        recoverable from the source corpus if a downstream stage needs it.
        """
        # mwe_id -> {"tokens": [tok, ...], "type": str | None}
        mwe_map: dict[str, dict] = {}
        for tok in tokens:
            mwe_field = tok["mwe"]
            if mwe_field == "*" or not mwe_field:
                continue
            for entry in mwe_field.split(";"):
                entry = entry.strip()
                if not entry:
                    continue
                if ":" in entry:
                    mwe_id, mwe_type = entry.split(":", 1)
                else:
                    mwe_id, mwe_type = entry, None
                if mwe_id not in mwe_map:
                    mwe_map[mwe_id] = {"tokens": [], "type": None}
                mwe_map[mwe_id]["tokens"].append(tok)
                # MWE type lives on the head token; preserve it across
                # continuation entries that omit it.
                if mwe_type and not mwe_map[mwe_id]["type"]:
                    mwe_map[mwe_id]["type"] = mwe_type

        for info in mwe_map.values():
            ordered = sorted(info["tokens"], key=lambda t: t["position"])
            # Single-token "MWEs" (stray IRV clitics with no verb captured, or
            # annotation artifacts) are not useful chunks.
            if len(ordered) < 2:
                continue
            surface = " ".join(t["form"] for t in ordered).strip()
            lemma_parts = [t["lemma"] for t in ordered if t["lemma"] and t["lemma"] != "_"]
            lemma = " ".join(lemma_parts).strip() if lemma_parts else None
            if not surface:
                continue
            chunk_type = MWE_TYPE_MAP.get(info["type"], "fixed_expression")
            yield {
                "surface_fr": surface,
                "lemma_fr": lemma,
                "language": self.language,
                "chunk_type": chunk_type,
            }


@click.command()
@click.option("--config", default="config.yml")
@click.option("--language", default="fr")
def main(config: str, language: str) -> None:
    PARSEMEIngester(language=language).run()


if __name__ == "__main__":
    main()
