"""
PARSEME ingestion.

Source: https://gitlab.com/parseme/parseme_corpus_fr (+ multilingual companions)
Verbal MWE corpus with categories: idioms, light verb constructions, etc.

SKELETON — you fill in the .cupt parsing logic.
The .cupt format is CoNLL-U with extra MWE columns. Each sentence is a block
of tab-separated lines; MWE annotations appear in column 11.
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
        # TODO: locate the .cupt files in the cloned repo.
        # Typical layout: <repo>/<lang>/train.cupt + dev.cupt + test.cupt
        # Some repos use uppercase, some lowercase. Check.
        cupt_files = list(self.repo_dir.rglob("*.cupt"))
        if not cupt_files:
            self.log.warning(f"No .cupt files found in {self.repo_dir}")
            return

        self.log.info(f"Found {len(cupt_files)} .cupt files")
        for cupt_path in cupt_files:
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
                sentence_tokens.append({
                    "id": cols[0],
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
        TODO: Handle discontinuous MWEs more gracefully. Current impl
        concatenates tokens in order, which produces literal surface
        strings even when the MWE was split.
        """
        mwe_map: dict[str, dict] = {}  # mwe_id → {tokens, type}
        for tok in tokens:
            mwe_field = tok["mwe"]
            if mwe_field == "*" or not mwe_field:
                continue
            for entry in mwe_field.split(";"):
                if ":" in entry:
                    mwe_id, mwe_type = entry.split(":", 1)
                else:
                    mwe_id, mwe_type = entry, None
                if mwe_id not in mwe_map:
                    mwe_map[mwe_id] = {"tokens": [], "type": None}
                mwe_map[mwe_id]["tokens"].append(tok)
                if mwe_type:
                    mwe_map[mwe_id]["type"] = mwe_type

        for mwe_id, info in mwe_map.items():
            surface = " ".join(t["form"] for t in info["tokens"])
            lemma = " ".join(t["lemma"] for t in info["tokens"] if t["lemma"] != "_")
            chunk_type = MWE_TYPE_MAP.get(info["type"], "fixed_expression")
            yield {
                "surface_fr": surface,
                "lemma_fr": lemma if lemma else None,
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
