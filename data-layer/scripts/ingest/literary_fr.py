"""
Literary / academic French ingester for DALF C1/C2 chunks (D-024).

Three source streams feed a shared spaCy-backed phrase extractor that yields
3-15-token noun-phrase / multi-word-expression chunks:

  1) Project Gutenberg FR — curated PD post-1850 literary corpus
     (Hugo / Flaubert / Maupassant / Zola). Pre-1850 works are skipped per the
     ticket constraint (archaic French throws CEFR estimation off).
  2) HuggingFace UniversalCEFR — `kwiqiz_fr` and `readme_fr` filtered to
     `cefr_level in ('C1', 'C2')`.
  3) French Wikipedia — `Catégorie:Article de qualité` and
     `Catégorie:Bon article` (vetted high-register prose, CC-BY-SA-3.0).

CEFR labelling policy: only propagate `cefr_level` when the source dataset
itself explicitly labels each row's level (UniversalCEFR/readme_fr +
kwiqiz_fr both carry per-row `cefr_level`). Gutenberg and Wikipedia chunks
land with `cefr_level = NULL` — their per-chunk level comes from D-021 LLM
enrichment. Earlier auto-tagging the entire Gutenberg sweep as C1 polluted
the C1 bucket with A1 vocabulary like "homme" / "eau" / "vivre"; the
heuristic is intentionally removed.
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Iterator, Optional

import click
import requests
from tqdm import tqdm

from scripts.common import LICENSE_REGISTRY
from scripts.ingest.base import Ingester


# ---------------------------------------------------------------------------
# License registry — registered at import so the base class picks them up.
# ---------------------------------------------------------------------------

LICENSE_REGISTRY.setdefault("Gutenberg_FR", {
    "license": "Public Domain",
    "attribution": "Project Gutenberg — public-domain text archive.",
    "url": "https://www.gutenberg.org",
    "commercial_use": "Yes (PD).",
})
LICENSE_REGISTRY.setdefault("Wikipedia_FR_Quality", {
    "license": "CC-BY-SA-3.0",
    "attribution": "Wikipédia FR contributors — Articles de qualité / Bons articles.",
    "url": "https://fr.wikipedia.org",
    "commercial_use": "Yes, with share-alike + attribution.",
})


# ---------------------------------------------------------------------------
# Curated Gutenberg corpus — every entry's first publication year is >= 1850.
# (Balzac and Stendhal are intentionally excluded: both wrote almost entirely
# before 1850 and the ticket forbids pre-1850 archaic French.)
# ---------------------------------------------------------------------------

GUTENBERG_WORKS: list[tuple[int, str, str, int]] = [
    # (gutenberg_id, author, title, year)
    (17489, "Hugo", "Les Misérables — Tome I", 1862),
    (17493, "Hugo", "Les Misérables — Tome II", 1862),
    (17494, "Hugo", "Les Misérables — Tome III", 1862),
    (17518, "Hugo", "Les Misérables — Tome IV", 1862),
    (17519, "Hugo", "Les Misérables — Tome V", 1862),
    (5423, "Hugo", "L'Homme qui rit", 1869),
    (35345, "Hugo", "Quatrevingt-treize", 1874),
    (14155, "Flaubert", "Madame Bovary", 1857),
    (16234, "Flaubert", "Salammbô", 1862),
    (12723, "Flaubert", "L'Éducation sentimentale", 1869),
    (3258, "Maupassant", "Bel-Ami", 1885),
    (3266, "Maupassant", "Une vie", 1883),
    (3265, "Maupassant", "Pierre et Jean", 1888),
    (5711, "Zola", "Germinal", 1885),
    (8558, "Zola", "L'Assommoir", 1877),
    (17511, "Zola", "Nana", 1880),
    (16433, "Zola", "La Bête humaine", 1890),
]

GUTENBERG_URL_PATTERNS = [
    "https://www.gutenberg.org/cache/epub/{id}/pg{id}.txt",
    "https://www.gutenberg.org/files/{id}/{id}-0.txt",
    "https://www.gutenberg.org/files/{id}/{id}-8.txt",
]

_HEADER_RE = re.compile(
    r"\*+\s*START OF (?:THE|THIS) PROJECT GUTENBERG.*?\*+",
    re.IGNORECASE | re.DOTALL,
)
_FOOTER_RE = re.compile(
    r"\*+\s*END OF (?:THE|THIS) PROJECT GUTENBERG.*?\*+",
    re.IGNORECASE | re.DOTALL,
)
_WS_RE = re.compile(r"\s+")


def _strip_gutenberg_boilerplate(text: str) -> str:
    """Drop the leading license header and trailing footer, if present."""
    m = _HEADER_RE.search(text)
    if m:
        text = text[m.end():]
    m = _FOOTER_RE.search(text)
    if m:
        text = text[:m.start()]
    return text


# ---------------------------------------------------------------------------
# spaCy phrase extractor — cached at module scope so we pay the model load
# cost (≈5 s) once per process even when all three sub-ingesters run.
# ---------------------------------------------------------------------------

_NLP = None


def _get_nlp(log=None):
    global _NLP
    if _NLP is None:
        import spacy
        if log:
            log.info("Loading spaCy fr_core_news_lg (one-time)")
        _NLP = spacy.load("fr_core_news_lg", disable=["ner", "lemmatizer"])
        # Defensive: the default 1 MB cap is enough for our windowed callers.
        _NLP.max_length = 1_500_000
    return _NLP


class _PhraseExtractor:
    """Yield 3-15-token NP-flavoured phrases from a passage of French prose."""

    MIN_TOKENS = 3
    MAX_TOKENS = 15
    MIN_CHAR_LEN = 8

    def __init__(self, log=None):
        self.log = log

    def iter_phrases(self, text: str) -> Iterator[dict]:
        """
        Run spaCy on `text` and yield phrase dicts:
            {'surface': str, 'token_count': int}

        Strategy:
          (a) walk noun_chunks; expand each one to include the head's trailing
              `amod` children — French models' noun_chunks miss postnominal
              adjectives ('la situation économique mondiale' arrives as just
              'la situation économique').
          (b) additionally emit a longer span that grafts the head's first
              `nmod` subtree onto the expanded chunk so we capture
              'les habitudes de consommation' rather than just 'les habitudes'.
        """
        if not text or len(text.strip()) < 50:
            return
        nlp = _get_nlp(self.log)
        text = text.strip()
        if len(text) > nlp.max_length:
            text = text[: nlp.max_length]
        try:
            doc = nlp(text)
        except Exception as exc:
            if self.log:
                self.log.debug(f"spaCy parse failure (skipping passage): {exc}")
            return

        for nc in doc.noun_chunks:
            expanded = self._expand_with_amods(doc, nc)
            phrase = self._yield_chunk(expanded)
            if phrase is not None:
                yield phrase
            with_pp = self._expand_with_nmod(doc, expanded)
            if with_pp is not None:
                phrase2 = self._yield_chunk(with_pp)
                if phrase2 is not None:
                    yield phrase2

    def _yield_chunk(self, span) -> Optional[dict]:
        tokens = [t for t in span if not t.is_space]
        if len(tokens) < self.MIN_TOKENS or len(tokens) > self.MAX_TOKENS:
            return None
        if tokens[0].is_punct or tokens[-1].is_punct:
            return None
        # Reject spans containing line breaks reconstructed by spaCy as one token.
        surface = " ".join(t.text for t in tokens)
        surface = _WS_RE.sub(" ", surface).strip()
        if len(surface) < self.MIN_CHAR_LEN:
            return None
        # Reject mostly-PROPN spans — proper-noun runs in 19th-c. fiction
        # are character names that don't generalise to language learning.
        propn = sum(1 for t in tokens if t.pos_ == "PROPN")
        content = sum(1 for t in tokens if t.pos_ in ("NOUN", "VERB", "ADJ"))
        if propn > content or content < 1:
            return None
        if any(t.like_num or t.is_digit for t in tokens):
            return None
        if surface.isupper() or sum(c.isalpha() for c in surface) < 6:
            return None
        return {"surface": surface, "token_count": len(tokens)}

    def _expand_with_amods(self, doc, span):
        """Stretch `span` rightward over any of the head noun's trailing amods."""
        head = span.root
        right_edge = span.end - 1
        for child in head.children:
            if child.dep_ == "amod" and child.i > right_edge:
                right_edge = child.i
        if right_edge == span.end - 1:
            return span
        return doc[span.start: right_edge + 1]

    def _expand_with_nmod(self, doc, span):
        """
        Append the first nominal modifier (`nmod`) subtree of the head noun.

        French model encodes 'les habitudes **de consommation**' as
        `consommation` being an `nmod` child of `habitudes` (with `de` itself
        being a `case` child of `consommation`); the PP arrives via `nmod`,
        not via a direct preposition child of the head, so we follow `nmod`
        edges rather than direct `ADP` rights.
        """
        head = span.root
        candidates = sorted(
            (c for c in head.children if c.dep_ == "nmod" and c.i >= span.end),
            key=lambda t: t.i,
        )
        if not candidates:
            return None
        nmod = candidates[0]
        right_edge = max(t.i for t in nmod.subtree)
        if right_edge - span.start > self.MAX_TOKENS + 1:
            return None
        return doc[span.start: right_edge + 1]


# ---------------------------------------------------------------------------
# Source 1 — Project Gutenberg
# ---------------------------------------------------------------------------

class GutenbergLiteraryIngester(Ingester):
    source_name = "Gutenberg_FR"
    source_version = "curated-2026-05"
    batch_size = 500

    WINDOW_CHARS = 200_000

    def __init__(self) -> None:
        super().__init__()
        self.extractor = _PhraseExtractor(log=self.log)
        self.text_files: list[tuple[Path, dict]] = []

    def download(self) -> None:
        for gid, author, title, year in GUTENBERG_WORKS:
            if year < 1850:
                self.log.info(f"Skip pre-1850: {author} — {title} ({year})")
                continue
            dest = self.raw_dir / f"pg{gid}.txt"
            if dest.exists() and dest.stat().st_size > 5_000:
                self.text_files.append((dest, {"author": author, "title": title, "year": year}))
                continue
            fetched = False
            for pattern in GUTENBERG_URL_PATTERNS:
                url = pattern.format(id=gid)
                try:
                    self.http_download(url, dest)
                    if dest.exists() and dest.stat().st_size > 5_000:
                        fetched = True
                        break
                    if dest.exists():
                        dest.unlink()
                except Exception as e:
                    self.log.debug(f"  pg{gid} {pattern} failed: {e}")
                    if dest.exists():
                        try:
                            dest.unlink()
                        except OSError:
                            pass
            if fetched:
                self.text_files.append((dest, {"author": author, "title": title, "year": year}))
            else:
                self.log.warning(f"Could not fetch Gutenberg #{gid} — {title}")

    def iter_rows(self) -> Iterator[dict]:
        for path, meta in self.text_files:
            try:
                raw = path.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                self.log.error(f"Read failure {path.name}: {e}")
                continue
            cleaned = _strip_gutenberg_boilerplate(raw)
            self.log.info(
                f"Extract {meta['author']} — {meta['title']} ({meta['year']}) — {len(cleaned):,} chars"
            )
            for window in _windows(cleaned, self.WINDOW_CHARS):
                for phrase in self.extractor.iter_phrases(window):
                    yield {
                        "surface_fr": phrase["surface"],
                        "language": "fr",
                        # No auto-CEFR — Gutenberg literary prose contains
                        # vocabulary at every level (A1 'homme' through C2
                        # registerised lexis); Groq enrichment scores per chunk.
                        "register": "formal",
                        "is_quebec_specific": False,
                        "chunk_type": "phrase",
                    }


# ---------------------------------------------------------------------------
# Source 2 — HuggingFace UniversalCEFR (C1/C2 only)
# ---------------------------------------------------------------------------

class UniversalCEFRCLevelIngester(Ingester):
    """
    Pulls the two FR datasets in the UniversalCEFR org that we discovered via
    `huggingface_hub.list_datasets` (kwiqiz_fr, readme_fr) and emits phrases
    only from rows the dataset itself labels at C1 or C2.

    Re-uses `source_name = "UniversalCEFR"` so chunks land under the same
    provenance bucket as the existing universal_cefr.py ingester. The
    `source_version` namespaces this run inside chunk_sources.
    """

    source_name = "UniversalCEFR"
    source_version = "kwiqiz+readme-c-level"
    batch_size = 500

    DATASETS = [
        # (hf_id, split, dataset_license)
        ("UniversalCEFR/kwiqiz_fr", "train", "CC-BY-NC-4.0"),
        ("UniversalCEFR/readme_fr", "train", "CC-BY-SA-NC-4.0"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.extractor = _PhraseExtractor(log=self.log)

    def download(self) -> None:
        try:
            import datasets  # noqa: F401
        except ImportError as e:
            raise RuntimeError("`datasets` library required.") from e
        if os.environ.get("HF_TOKEN"):
            self.log.info("HF_TOKEN detected — authenticated dataset access enabled")

    def iter_rows(self) -> Iterator[dict]:
        from datasets import load_dataset

        for ds_id, split, lic in self.DATASETS:
            self.log.info(f"Loading {ds_id} [{split}]  (license={lic})")
            try:
                ds = load_dataset(ds_id, split=split, streaming=False)
            except Exception as e:
                self.log.error(f"Failed to load {ds_id}: {e}")
                continue

            kept = 0
            for row in ds:
                level = (row.get("cefr_level") or "").upper().strip()
                if level not in ("C1", "C2"):
                    continue
                text = (row.get("text") or "").strip()
                if not text:
                    continue
                kept += 1
                for phrase in self.extractor.iter_phrases(text):
                    yield {
                        "surface_fr": phrase["surface"],
                        "language": "fr",
                        "cefr_level": level,
                        "register": "formal",
                        "is_quebec_specific": False,
                        "chunk_type": "phrase",
                    }
            self.log.info(f"  {ds_id}: {kept} C1/C2 source rows processed")


# ---------------------------------------------------------------------------
# Source 3 — French Wikipedia featured / good articles
# ---------------------------------------------------------------------------

class WikipediaFRQualityIngester(Ingester):
    source_name = "Wikipedia_FR_Quality"
    source_version = "2026-05"
    batch_size = 500

    CATEGORIES = [
        "Catégorie:Article de qualité",
        "Catégorie:Bon article",
    ]
    API = "https://fr.wikipedia.org/w/api.php"
    UA = "LeMethodicDataLayer/0.1 (https://lemethodic.com)"
    REQUEST_DELAY = 0.4         # ≈2.5 req/s — well below MediaWiki guidance.
    PER_CATEGORY_LIMIT = 300    # Caps the corpus to a manageable footprint.
    MIN_EXTRACT_LEN = 800       # Skip stubs.
    MAX_EXTRACT_CHARS = 400_000

    SKIP_PREFIXES = (
        "Catégorie:", "Discussion:", "Wikipédia:", "Modèle:",
        "Portail:", "Aide:", "Spécial:", "Fichier:",
    )

    def __init__(self) -> None:
        super().__init__()
        self.extractor = _PhraseExtractor(log=self.log)
        self.titles: list[str] = []

    def download(self) -> None:
        cache = self.raw_dir / "titles.txt"
        if cache.exists():
            self.titles = [l for l in cache.read_text(encoding="utf-8").splitlines() if l.strip()]
            self.log.info(f"Reusing {len(self.titles)} cached titles from {cache.name}")
            return
        seen: set[str] = set()
        for cat in self.CATEGORIES:
            self.log.info(f"Listing {cat}")
            try:
                for title in self._iter_category_members(cat, self.PER_CATEGORY_LIMIT):
                    if title.startswith(self.SKIP_PREFIXES):
                        continue
                    seen.add(title)
            except Exception as e:
                self.log.error(f"Category list failed for {cat}: {e}")
        self.titles = sorted(seen)
        cache.write_text("\n".join(self.titles), encoding="utf-8")
        self.log.info(f"Cached {len(self.titles)} titles")

    def iter_rows(self) -> Iterator[dict]:
        if not self.titles:
            self.log.warning("No Wikipedia titles to process — skipping source")
            return
        for title in tqdm(self.titles, desc="wikipedia", unit="page"):
            text = self._fetch_extract(title)
            if not text or len(text) < self.MIN_EXTRACT_LEN:
                continue
            if len(text) > self.MAX_EXTRACT_CHARS:
                text = text[: self.MAX_EXTRACT_CHARS]
            for phrase in self.extractor.iter_phrases(text):
                yield {
                    "surface_fr": phrase["surface"],
                    "language": "fr",
                    # No auto-CEFR — Wikipedia featured / good articles span
                    # every register inside one article; per-phrase level
                    # comes from Groq enrichment downstream.
                    "register": "formal",
                    "is_quebec_specific": False,
                    "chunk_type": "phrase",
                }

    # -- MediaWiki helpers ----------------------------------------------------

    def _iter_category_members(self, cat: str, limit: int) -> Iterator[str]:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": cat,
            "cmlimit": "max",
            "cmtype": "page",
            "format": "json",
        }
        fetched = 0
        while True:
            payload = self._get(params)
            for m in payload.get("query", {}).get("categorymembers", []):
                yield m["title"]
                fetched += 1
                if fetched >= limit:
                    return
            cont = payload.get("continue")
            if not cont:
                return
            params.update(cont)

    def _fetch_extract(self, title: str) -> Optional[str]:
        try:
            payload = self._get({
                "action": "query",
                "prop": "extracts",
                "explaintext": 1,
                "redirects": 1,
                "titles": title,
                "format": "json",
            })
        except Exception as e:
            self.log.debug(f"extract fetch failed ({title}): {e}")
            return None
        pages = payload.get("query", {}).get("pages", {})
        for _, page in pages.items():
            extract = page.get("extract")
            if extract:
                return extract
        return None

    def _get(self, params: dict) -> dict:
        time.sleep(self.REQUEST_DELAY)
        r = requests.get(
            self.API,
            params=params,
            headers={"User-Agent": self.UA, "Accept": "application/json"},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()


# ---------------------------------------------------------------------------
# Helpers + CLI
# ---------------------------------------------------------------------------

def _windows(text: str, size: int) -> Iterator[str]:
    for i in range(0, len(text), size):
        yield text[i: i + size]


_RUNNERS = {
    "gutenberg": GutenbergLiteraryIngester,
    "universalcefr": UniversalCEFRCLevelIngester,
    "wikipedia": WikipediaFRQualityIngester,
}


@click.command()
@click.option(
    "--source",
    type=click.Choice(["all"] + list(_RUNNERS.keys())),
    default="all",
    help="Which sub-source to ingest (default: all three).",
)
@click.option("--config", default="config.yml")
def main(source: str, config: str) -> None:
    targets = list(_RUNNERS.values()) if source == "all" else [_RUNNERS[source]]
    for cls in targets:
        cls().run()


if __name__ == "__main__":
    main()
