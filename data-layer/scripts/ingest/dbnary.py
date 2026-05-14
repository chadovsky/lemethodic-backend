"""
DBnary ingestion.

Source: http://kaiko.getalp.org/static/ontolex/latest/fr_dbnary_ontolex.ttl.bz2
Wiktionary parsed into structured RDF (OntoLex format).

SKELETON — DBnary uses Turtle (.ttl) RDF format. The Python rdflib library
can parse it but consumes a lot of memory on the full dump. Recommended:
use rdflib's streaming parser or pre-filter with `grep` before parsing.
"""

from __future__ import annotations

import bz2
import shutil
from pathlib import Path
from typing import Iterator

import click

from scripts.ingest.base import Ingester

DBNARY_URLS = {
    "fr": "http://kaiko.getalp.org/static/ontolex/latest/fr_dbnary_ontolex.ttl.bz2",
    "en": "http://kaiko.getalp.org/static/ontolex/latest/en_dbnary_ontolex.ttl.bz2",
    # ES, PT, AR may exist; verify.
}


class DBnaryIngester(Ingester):
    source_name = "DBnary"
    source_version = "latest"
    batch_size = 1000

    def __init__(self, language: str = "fr"):
        super().__init__()
        self.language = language

    def download(self) -> None:
        url = DBNARY_URLS.get(self.language)
        if not url:
            raise ValueError(f"No DBnary URL configured for {self.language}")
        self.compressed_path = self.raw_dir / f"{self.language}_dbnary.ttl.bz2"
        self.uncompressed_path = self.raw_dir / f"{self.language}_dbnary.ttl"

        self.http_download(url, self.compressed_path)

        if not self.uncompressed_path.exists():
            self.log.info(f"Decompressing {self.compressed_path}")
            with bz2.open(self.compressed_path, "rb") as fin, \
                 open(self.uncompressed_path, "wb") as fout:
                shutil.copyfileobj(fin, fout)

    def iter_rows(self) -> Iterator[dict]:
        # TODO: Use rdflib streaming parser. Naive `rdflib.Graph().parse()`
        # will OOM on a multi-GB dump. Use `rdflib.parse(format='turtle',
        # source=path)` with iterative processing, or pre-filter the .ttl
        # file for only LexicalEntry triples before parsing.
        #
        # DBnary LexicalEntry structure (OntoLex):
        #   <entry> ontolex:canonicalForm <form> .
        #   <form> ontolex:writtenRep "faire la queue"@fr .
        #   <entry> dbnary:partOfSpeech <verb> .
        #   <entry> skos:definition "wait in line"@en .
        #   <entry> dbnary:senseTranslation <translation> .
        #   <translation> dbnary:writtenForm "wait in line"@en .

        try:
            from rdflib import Graph, Namespace, URIRef
        except ImportError:
            raise RuntimeError("rdflib not installed. pip install rdflib")

        # Placeholder: parse a SMALL subset to validate the pipeline works.
        # Replace with streaming logic before running on full dump.
        self.log.warning(
            "DBnary skeleton: replace this placeholder with streaming parser before full run."
        )

        # TODO: replace with real parsing
        return iter([])

    def _parse_lexical_entry(self, graph, entry_uri) -> dict | None:
        """
        TODO: Given a LexicalEntry URI, extract surface form, POS,
        definitions, translations, examples. Return chunk dict.
        """
        return None


@click.command()
@click.option("--config", default="config.yml")
@click.option("--language", default="fr")
def main(config: str, language: str) -> None:
    DBnaryIngester(language=language).run()


if __name__ == "__main__":
    main()
