"""
Tatoeba ingestion.

Source: https://downloads.tatoeba.org
12M+ human-translated sentence pairs across 400+ languages.

This pipeline adds example sentences to existing chunks (matched on surface
form contained in the example) rather than creating new chunks. Example
sentences attach to chunks whose surface form appears in the sentence.

SKELETON — the linking logic is the interesting part; everything else is straightforward.
"""

from __future__ import annotations

import bz2
import csv
import re
import shutil
import tarfile
from pathlib import Path
from typing import Iterator

import click

from scripts.ingest.base import Ingester
from scripts.common import db_session, insert_example, normalize_surface
from sqlalchemy import text

SENTENCES_URL = "https://downloads.tatoeba.org/exports/per_language/fra/fra_sentences.tsv.bz2"
LINKS_URL = "https://downloads.tatoeba.org/exports/links.tar.bz2"
ENG_SENTENCES_URL = "https://downloads.tatoeba.org/exports/per_language/eng/eng_sentences.tsv.bz2"

# Strip leading/trailing punctuation while preserving in-word apostrophes
# and hyphens (so "n'est", "vas-tu" survive intact but "bonjour," → "bonjour").
_TOKEN_STRIP_RE = re.compile(r"^[^\w]+|[^\w]+$", re.UNICODE)


def _tokenize_for_ngrams(normalized_text: str) -> list[str]:
    out = []
    for tok in normalized_text.split():
        tok = _TOKEN_STRIP_RE.sub("", tok)
        if tok:
            out.append(tok)
    return out


class TatoebaIngester(Ingester):
    source_name = "Tatoeba"
    source_version = "exports"
    batch_size = 1000

    def download(self) -> None:
        self.fra_path = self.raw_dir / "fra_sentences.tsv"
        self.eng_path = self.raw_dir / "eng_sentences.tsv"
        self.links_path = self.raw_dir / "links.csv"

        for url, raw_target, decompressed_target in [
            (SENTENCES_URL, self.raw_dir / "fra_sentences.tsv.bz2", self.fra_path),
            (ENG_SENTENCES_URL, self.raw_dir / "eng_sentences.tsv.bz2", self.eng_path),
        ]:
            self.http_download(url, raw_target)
            if not decompressed_target.exists():
                self.log.info(f"Decompressing {raw_target.name}")
                with bz2.open(raw_target, "rb") as fin, open(decompressed_target, "wb") as fout:
                    shutil.copyfileobj(fin, fout)

        # links.tar.bz2 is a tarball containing links.csv
        links_tarball = self.raw_dir / "links.tar.bz2"
        self.http_download(LINKS_URL, links_tarball)
        if not self.links_path.exists():
            self.log.info(f"Extracting {links_tarball.name}")
            with tarfile.open(links_tarball, "r:bz2") as tar:
                tar.extractall(self.raw_dir)

    def iter_rows(self) -> Iterator[dict]:
        """
        Tatoeba ingestion is different: we don't create chunks, we add
        example sentences to existing chunks. So we bypass the standard
        Ingester.run() flow and override it.
        """
        # No-op; we use custom run() below.
        return iter([])

    def run(self) -> None:
        """Override standard run() because Tatoeba is example-attachment, not chunk creation."""
        self.log.info(f"Starting Tatoeba example attachment")
        self.download()

        # Step 1: Load FR sentences into memory: id → text
        fr_sentences = {}
        self.log.info("Loading FR sentences")
        with open(self.fra_path, "r", encoding="utf-8") as f:
            for row in csv.reader(f, delimiter="\t"):
                if len(row) >= 3:
                    fr_sentences[row[0]] = row[2]
        self.log.info(f"  {len(fr_sentences)} FR sentences")

        # Step 2: Load EN sentences
        en_sentences = {}
        self.log.info("Loading EN sentences")
        with open(self.eng_path, "r", encoding="utf-8") as f:
            for row in csv.reader(f, delimiter="\t"):
                if len(row) >= 3:
                    en_sentences[row[0]] = row[2]
        self.log.info(f"  {len(en_sentences)} EN sentences")

        # Step 3: Iterate FR-EN links
        self.log.info("Iterating FR-EN links and attaching examples")
        with db_session() as session:
            # Pre-load chunk normalized_surfaces → ids for fast lookup
            chunk_map: dict[str, int] = {}
            max_chunk_tokens = 1
            for row in session.execute(text("SELECT id, normalized_surface FROM chunks WHERE language = 'fr'")):
                chunk_map[row.normalized_surface] = row.id
                tok_count = row.normalized_surface.count(" ") + 1
                if tok_count > max_chunk_tokens:
                    max_chunk_tokens = tok_count
            self.log.info(f"  {len(chunk_map)} candidate FR chunks loaded (max {max_chunk_tokens} tokens)")

            # Per-FR-sentence n-gram hash lookup: O(L * max_n) per sentence,
            # so total cost is O(total_tokens * max_n) — independent of chunk
            # count. With 30k chunks × 200k FR-EN pairs × ~10 tokens × max_n=5
            # that's ~10M dict lookups, ~10 s. The DB INSERT (one per match
            # with a WHERE NOT EXISTS dedup probe) dominates wall time, not
            # the lookup — a prefix tree would not move the needle.
            counter = 0
            with open(self.links_path, "r", encoding="utf-8") as f:
                for row in csv.reader(f, delimiter="\t"):
                    if len(row) < 2:
                        continue
                    src_id, tgt_id = row[0], row[1]
                    if src_id not in fr_sentences or tgt_id not in en_sentences:
                        continue
                    fr_text = fr_sentences[src_id]
                    en_text = en_sentences[tgt_id]

                    normalized_fr = normalize_surface(fr_text)
                    tokens = _tokenize_for_ngrams(normalized_fr)
                    matched_ids: set[int] = set()
                    for n in range(1, max_chunk_tokens + 1):
                        for i in range(len(tokens) - n + 1):
                            ngram = " ".join(tokens[i:i + n])
                            cid = chunk_map.get(ngram)
                            if cid:
                                matched_ids.add(cid)

                    for cid in matched_ids:
                        insert_example(session, cid, fr_text, "Tatoeba", en_text)
                        counter += 1

                    if counter > 0 and counter % self.batch_size == 0:
                        session.commit()
                        self.log.info(f"  Attached {counter} examples")

            session.commit()
            self.log.info(f"Tatoeba: attached {counter} example sentences")


@click.command()
@click.option("--config", default="config.yml")
def main(config: str) -> None:
    TatoebaIngester().run()


if __name__ == "__main__":
    main()
