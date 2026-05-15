"""
DBnary ingestion.

Source: http://kaiko.getalp.org/static/ontolex/latest/fr_dbnary_ontolex.ttl.bz2
Wiktionary parsed into structured RDF (OntoLex format).

The full French dump is multi-GB uncompressed. `rdflib.Graph().parse()` on the
whole file loads every triple into an indexed in-memory graph and blows past
8 GB of RAM. Instead we stream the .ttl line-by-line, split into single-subject
blocks at top-level `.` terminators (quote-aware), and parse each block with a
fresh disposable graph. Cross-subject references (an entry pointing to a form
URI, a sense pointing to a translation URI) are resolved through plain-dict
caches that ride along the stream. Entries are flushed to chunks as soon as
their lemma group's blocks finish — when a new LexicalEntry subject is seen,
the previous entry's data is complete and the chunk is yielded, then its
referenced forms / senses / translations are dropped from the caches. Peak
memory is bounded to the current lemma's payload, not the whole dump.

Real-world DBnary shape (verified against fr_dbnary_ontolex.ttl 2026-05 dump):
    fra:accueil__nom__1 a ontolex:Word, ontolex:LexicalEntry ;
        rdfs:label "accueil"@fr ;
        dbnary:partOfSpeech "-nom-" ;
        lexinfo:partOfSpeech lexinfo:noun ;
        ontolex:canonicalForm fra:__cf_accueil__nom__1 ;
        ontolex:sense fra:__ws_1_accueil__nom__1, ... .
    fra:__cf_accueil__nom__1 a ontolex:Form ;
        ontolex:writtenRep "accueil"@fr .
    fra:__ws_1_accueil__nom__1 a ontolex:LexicalSense ;
        skos:definition [ rdf:value "..."@fr ] ;          # blank node!
        skos:example    [ rdf:value "..."@fr ; ... ] .
    fra:__tr_eng_1_accueil__nom__1 a dbnary:Translation ;
        dbnary:isTranslationOf fra:accueil__nom__1 ;       # points at the ENTRY
        dbnary:targetLanguage  lexvo:eng ;
        dbnary:writtenForm     "welcome"@en .
"""

from __future__ import annotations

import bz2
import shutil
from pathlib import Path
from typing import Iterable, Iterator, Optional

import click

from scripts.ingest.base import Ingester

DBNARY_URLS = {
    "fr": "http://kaiko.getalp.org/static/ontolex/latest/fr_dbnary_ontolex.ttl.bz2",
    "en": "http://kaiko.getalp.org/static/ontolex/latest/en_dbnary_ontolex.ttl.bz2",
}

ONTOLEX = "http://www.w3.org/ns/lemon/ontolex#"
DBNARY = "http://kaiko.getalp.org/dbnary#"
SKOS = "http://www.w3.org/2004/02/skos/core#"
LEXINFO = "http://www.lexinfo.net/ontology/2.0/lexinfo#"
RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS_NS = "http://www.w3.org/2000/01/rdf-schema#"
RDF_VALUE = f"{RDF_NS}value"

# Subjects that look like LexicalEntry-ish RDF types. DBnary stamps entries with multiple
# rdf:type values (ontolex:Word + ontolex:LexicalEntry, or ontolex:MultiWordExpression, etc.).
ENTRY_TYPE_URIS = {
    f"{ONTOLEX}LexicalEntry",
    f"{ONTOLEX}Word",
    f"{ONTOLEX}MultiWordExpression",
    f"{ONTOLEX}Affix",
}

# Map lexinfo POS URIs (and DBnary string POS values) to our pos_pattern convention.
LEXINFO_POS_MAP = {
    f"{LEXINFO}verb": "VERB",
    f"{LEXINFO}noun": "NOUN",
    f"{LEXINFO}commonNoun": "NOUN",
    f"{LEXINFO}properNoun": "PROPN",
    f"{LEXINFO}adjective": "ADJ",
    f"{LEXINFO}adverb": "ADV",
    f"{LEXINFO}preposition": "PREP",
    f"{LEXINFO}conjunction": "CONJ",
    f"{LEXINFO}determiner": "DET",
    f"{LEXINFO}pronoun": "PRON",
    f"{LEXINFO}interjection": "INTJ",
}

STRING_POS_MAP = {
    "verb": "VERB",
    "verbe": "VERB",
    "noun": "NOUN",
    "nom": "NOUN",
    "nom-pr": "PROPN",
    "nom-propre": "PROPN",
    "adjective": "ADJ",
    "adj": "ADJ",
    "adjectif": "ADJ",
    "adverb": "ADV",
    "adv": "ADV",
    "adverbe": "ADV",
    "preposition": "PREP",
    "prep": "PREP",
    "prép": "PREP",
    "préposition": "PREP",
    "conjunction": "CONJ",
    "conj": "CONJ",
    "conjonction": "CONJ",
    "determiner": "DET",
    "det": "DET",
    "art": "DET",
    "article": "DET",
    "determinant": "DET",
    "déterminant": "DET",
    "pronoun": "PRON",
    "pronom": "PRON",
    "interjection": "INTJ",
    "interj": "INTJ",
}

# Target translation language → surface_en column. We only keep English translations
# for now (column is `surface_en`); other languages can be added when the schema grows.
ENGLISH_LANG_TAGS = {"en", "eng"}
ENGLISH_LANG_URIS = {
    "http://lexvo.org/id/iso639-3/eng",
    "http://lexvo.org/id/iso639-1/en",
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
        try:
            import rdflib  # noqa: F401
        except ImportError:
            raise RuntimeError("rdflib not installed. pip install rdflib")

        self.log.info(f"Streaming {self.uncompressed_path}")
        yield from parse_dbnary_stream(
            self._iter_lines(self.uncompressed_path),
            log=self.log,
        )

    @staticmethod
    def _iter_lines(path: Path) -> Iterator[str]:
        with open(path, "r", encoding="utf-8") as f:
            yield from f


# ---------------------------------------------------------------------------
# Streaming parser (factored out for unit-testability)
# ---------------------------------------------------------------------------

def parse_dbnary_stream(
    lines: Iterable[str],
    log=None,
    progress_every: int = 50_000,
) -> Iterator[dict]:
    """
    Stream a DBnary turtle source line-by-line and yield chunk dicts.

    Splits the input into single-subject Turtle blocks, parses each one in
    isolation with rdflib, and accumulates cross-subject references in plain
    dicts. Yields chunks **incrementally** as each lemma group completes: when
    a new LexicalEntry subject is observed, all older pending entries are
    flushed to chunks and their dependent forms/senses/translations are dropped
    from the caches. This bounds peak memory and keeps the downstream DB
    upserter busy from the first few seconds of the run instead of waiting for
    EOF.

    Layout assumption (verified against the real fr_dbnary.ttl dump): each
    lemma's blocks appear contiguously in the file — the LexicalEntry block,
    then its Form / Sense / Page / Translation blocks — followed by the next
    lemma. Translations cite their source via dbnary:isTranslationOf pointing
    at the *entry* URI (not at a sense URI), so the entry URI is what we key
    flush eligibility on.
    """
    from rdflib import BNode, Graph  # noqa: PLC0415

    forms: dict[str, str] = {}              # form URI -> writtenRep
    senses: dict[str, dict] = {}            # sense URI -> {definitions, examples, ...}
    translations: dict[str, dict] = {}      # translation URI -> {written, lang, source}
    entries: dict[str, dict] = {}           # entry URI -> partial entry record
    entry_order: list[str] = []             # FIFO of entry URIs awaiting flush

    prefix_block, body_lines = _split_prefix_preamble(lines)

    block_count = 0
    interesting_count = 0
    parse_errors = 0
    chunks_yielded = 0
    for block_text in _iter_subject_blocks(body_lines):
        block_count += 1
        if log and block_count % progress_every == 0:
            log.info(
                f"  dbnary stream: {block_count:,} blocks scanned, "
                f"{interesting_count:,} parsed, {chunks_yielded:,} chunks yielded, "
                f"pending entries={len(entry_order)}, "
                f"caches: forms={len(forms)} senses={len(senses)} translations={len(translations)}, "
                f"parse_errors={parse_errors}"
            )
        if not _block_is_interesting(block_text):
            continue
        interesting_count += 1
        try:
            g = Graph()
            g.parse(data=prefix_block + block_text, format="turtle")
        except Exception as e:  # noqa: BLE001
            parse_errors += 1
            if log and parse_errors <= 5:
                log.debug(f"Block parse error: {e}")
            continue

        bnode_value: dict = {}
        new_entry_uris: list[str] = []
        for s_, p_, o_ in g:
            p_str_ = str(p_)
            if isinstance(s_, BNode):
                if p_str_ == RDF_VALUE:
                    bnode_value[s_] = (str(o_), getattr(o_, "language", None))
                continue
            if p_str_ == f"{RDF_NS}type" and str(o_) in ENTRY_TYPE_URIS:
                s_str_ = str(s_)
                if s_str_ not in entries and s_str_ not in new_entry_uris:
                    new_entry_uris.append(s_str_)

        for s, p, o in g:
            if isinstance(s, BNode):
                continue
            s_str = str(s)
            p_str = str(p)

            if isinstance(o, BNode) and p_str in (f"{SKOS}definition", f"{SKOS}example"):
                resolved = bnode_value.get(o)
                if resolved is None:
                    continue
                text, lang = resolved
                if not text:
                    continue
                if p_str == f"{SKOS}definition":
                    senses.setdefault(s_str, _new_sense())["definitions"].append((text, lang))
                else:
                    senses.setdefault(s_str, _new_sense())["examples"].append((text, lang))
                continue

            _absorb_triple(s_str, p_str, o, forms, senses, translations, entries)

        if new_entry_uris:
            entry_order.extend(new_entry_uris)
            # Keep the most recent lemma in the cache so its trailing translations
            # (which follow the entry block in the file) can still attach to it.
            while len(entry_order) > 1:
                older = entry_order.pop(0)
                chunk = _flush_entry(older, entries, forms, senses, translations)
                if chunk:
                    chunks_yielded += 1
                    yield chunk

    while entry_order:
        older = entry_order.pop(0)
        chunk = _flush_entry(older, entries, forms, senses, translations)
        if chunk:
            chunks_yielded += 1
            yield chunk

    if log:
        log.info(
            f"DBnary stream complete: {block_count:,} blocks scanned, "
            f"{interesting_count:,} parsed, {chunks_yielded:,} chunks yielded, "
            f"{parse_errors} parse errors. "
            f"Residual caches: forms={len(forms)} senses={len(senses)} translations={len(translations)} entries={len(entries)}"
        )


def _flush_entry(
    entry_uri: str,
    entries: dict[str, dict],
    forms: dict[str, str],
    senses: dict[str, dict],
    translations: dict[str, dict],
) -> Optional[dict]:
    """Build a chunk for `entry_uri` and free its referenced cache entries."""
    entry = entries.pop(entry_uri, None)
    if not entry:
        return None
    chunk = _build_chunk(entry, forms, senses, translations, entry_uri=entry_uri)

    canonical = entry.get("canonical_form_uri")
    if canonical:
        forms.pop(canonical, None)
    for fu in entry.get("other_form_uris", []) or ():
        forms.pop(fu, None)

    sense_uris = entry.get("sense_uris", []) or []
    sense_uri_set = set(sense_uris)
    for su in sense_uris:
        senses.pop(su, None)

    if translations:
        to_drop = [
            tu for tu, tr in translations.items()
            if tr.get("source_sense_uri") == entry_uri
            or tr.get("source_sense_uri") in sense_uri_set
        ]
        for tu in to_drop:
            translations.pop(tu, None)

    return chunk


def _absorb_triple(
    s: str,
    p: str,
    o,
    forms: dict,
    senses: dict,
    translations: dict,
    entries: dict,
) -> None:
    """Sort one triple into the right cache."""
    from rdflib import BNode  # noqa: PLC0415

    if p == f"{RDF_NS}type":
        o_str = str(o)
        if o_str in ENTRY_TYPE_URIS or o_str.endswith("/LexicalEntry"):
            entries.setdefault(s, _new_entry())
        elif o_str == f"{ONTOLEX}LexicalSense":
            senses.setdefault(s, _new_sense())
        elif o_str == f"{ONTOLEX}Form":
            forms.setdefault(s, "")
        elif o_str == f"{DBNARY}Translation":
            translations.setdefault(s, _new_translation())
        return

    if p == f"{ONTOLEX}canonicalForm":
        entries.setdefault(s, _new_entry())["canonical_form_uri"] = str(o)
    elif p == f"{ONTOLEX}otherForm":
        entries.setdefault(s, _new_entry()).setdefault("other_form_uris", []).append(str(o))
    elif p == f"{ONTOLEX}sense":
        entries.setdefault(s, _new_entry()).setdefault("sense_uris", []).append(str(o))
    elif p == f"{LEXINFO}partOfSpeech":
        mapped = _map_pos(str(o))
        entry = entries.setdefault(s, _new_entry())
        if mapped or entry.get("pos") is None:
            entry["pos"] = mapped or entry.get("pos")
    elif p == f"{DBNARY}partOfSpeech":
        # DBnary uses a string literal here, often dashed like "-nom-" or "-verb-".
        mapped = _map_pos(str(o))
        entry = entries.setdefault(s, _new_entry())
        if mapped or entry.get("pos") is None:
            entry["pos"] = mapped or entry.get("pos")
    elif p == f"{RDFS_NS}label":
        text, lang = _literal_parts(o)
        if text:
            entries.setdefault(s, _new_entry())["label"] = text
            entries[s].setdefault("label_lang", lang)

    elif p == f"{ONTOLEX}writtenRep":
        text, _ = _literal_parts(o)
        if text:
            forms[s] = text

    elif p == f"{SKOS}definition":
        # Bnode-wrapped definitions (the common DBnary shape) are resolved by the caller
        # before we get here. The plain-literal shape — `skos:definition "..."@fr` — still
        # passes through this branch as a safety net for non-standard dumps.
        if not isinstance(o, BNode):
            text, lang = _literal_parts(o)
            if text:
                senses.setdefault(s, _new_sense())["definitions"].append((text, lang))
    elif p == f"{SKOS}example":
        if not isinstance(o, BNode):
            text, lang = _literal_parts(o)
            if text:
                senses.setdefault(s, _new_sense())["examples"].append((text, lang))
    elif p == f"{DBNARY}senseNumber":
        text, _ = _literal_parts(o)
        senses.setdefault(s, _new_sense())["sense_number"] = text

    elif p == f"{DBNARY}writtenForm":
        text, lang = _literal_parts(o)
        tr = translations.setdefault(s, _new_translation())
        tr["written"] = text
        if lang:
            tr["lang"] = lang
    elif p == f"{DBNARY}targetLanguage":
        tr = translations.setdefault(s, _new_translation())
        tr["lang_uri"] = str(o)
    elif p == f"{DBNARY}isTranslationOf":
        # In the current dump this points to the *entry* URI; older dumps point to a sense.
        # `_resolve_english_translation` handles both.
        translations.setdefault(s, _new_translation())["source_sense_uri"] = str(o)
    elif p == f"{DBNARY}senseTranslation":
        # Older / alternate predicate: <sense> dbnary:senseTranslation <translation> .
        senses.setdefault(s, _new_sense()).setdefault("translation_uris", []).append(str(o))


def _new_entry() -> dict:
    return {
        "canonical_form_uri": None,
        "other_form_uris": [],
        "sense_uris": [],
        "pos": None,
        "label": None,
        "label_lang": None,
    }


def _new_sense() -> dict:
    return {
        "definitions": [],
        "examples": [],
        "sense_number": None,
        "translation_uris": [],
    }


def _new_translation() -> dict:
    return {
        "written": None,
        "lang": None,
        "lang_uri": None,
        "source_sense_uri": None,
    }


def _literal_parts(o) -> tuple[str, Optional[str]]:
    """Return (text, language_tag) for an rdflib term; '' / None if not a literal."""
    text = str(o) if o is not None else ""
    lang = getattr(o, "language", None)
    return text, lang


def _map_pos(value: str) -> Optional[str]:
    if not value:
        return None
    if value.startswith("http"):
        return LEXINFO_POS_MAP.get(value)
    cleaned = value.strip().lower()
    # DBnary string POS values are typically dashed like "-nom-" or "-verb-pr-"; try both.
    direct = STRING_POS_MAP.get(cleaned)
    if direct:
        return direct
    return STRING_POS_MAP.get(cleaned.strip("-"))


def _build_chunk(
    entry: dict,
    forms: dict[str, str],
    senses: dict[str, dict],
    translations: dict[str, dict],
    entry_uri: Optional[str] = None,
) -> Optional[dict]:
    surface = _resolve_surface(entry, forms)
    if not surface:
        return None

    surface_en = _resolve_english_translation(entry, senses, translations, entry_uri=entry_uri)
    examples = _resolve_examples(entry, senses)

    chunk: dict = {
        "surface_fr": surface,
        "language": "fr",
        "pos_pattern": entry.get("pos"),
        "lemma_fr": surface,
    }
    if surface_en:
        chunk["surface_en"] = surface_en
    if examples:
        chunk["_examples"] = examples
    return chunk


def _resolve_surface(entry: dict, forms: dict[str, str]) -> Optional[str]:
    form_uri = entry.get("canonical_form_uri")
    if form_uri:
        text = forms.get(form_uri)
        if text:
            return text.strip()
    # Fall back to rdfs:label (DBnary always carries one).
    label = entry.get("label")
    if label:
        return label.strip()
    # Last resort: first available other form.
    for form_uri in entry.get("other_form_uris", []):
        text = forms.get(form_uri)
        if text:
            return text.strip()
    return None


def _resolve_english_translation(
    entry: dict,
    senses: dict[str, dict],
    translations: dict[str, dict],
    entry_uri: Optional[str] = None,
) -> Optional[str]:
    candidates: list[str] = []
    sense_uris = set(entry.get("sense_uris", []) or ())
    # 1) Forward sense → translation links (some dumps emit dbnary:senseTranslation).
    for sense_uri in sense_uris:
        sense = senses.get(sense_uri)
        if not sense:
            continue
        for tr_uri in sense.get("translation_uris", []):
            tr = translations.get(tr_uri)
            if tr and _is_english(tr) and tr.get("written"):
                candidates.append(tr["written"].strip())
    # 2) Reverse dbnary:isTranslationOf — the source URI is either the entry URI
    #    (current DBnary dumps) or a sense URI (older dumps).
    for tr in translations.values():
        if not _is_english(tr) or not tr.get("written"):
            continue
        source = tr.get("source_sense_uri")
        if not source:
            continue
        if source == entry_uri or source in sense_uris:
            candidates.append(tr["written"].strip())
    if not candidates:
        return None
    # Deduplicate while preserving order; join up to first 3 candidates.
    seen: dict[str, None] = {}
    for c in candidates:
        if c and c not in seen:
            seen[c] = None
    return "; ".join(list(seen.keys())[:3])


def _is_english(tr: dict) -> bool:
    if (tr.get("lang") or "").lower() in ENGLISH_LANG_TAGS:
        return True
    if (tr.get("lang_uri") or "") in ENGLISH_LANG_URIS:
        return True
    return False


def _resolve_examples(entry: dict, senses: dict[str, dict]) -> list[dict]:
    out: list[dict] = []
    for sense_uri in entry.get("sense_uris", []):
        sense = senses.get(sense_uri)
        if not sense:
            continue
        for text, lang in sense.get("examples", []):
            example_fr = text if (lang in (None, "", "fr")) else None
            if example_fr:
                out.append({"example_fr": example_fr})
    return out


# ---------------------------------------------------------------------------
# Block streaming (quote-aware turtle splitter)
# ---------------------------------------------------------------------------

def _split_prefix_preamble(lines: Iterable[str]) -> tuple[str, Iterator[str]]:
    """
    Drain leading @prefix / @base declarations into a preamble string. Returns
    the preamble and an iterator over the remaining lines. The preamble is
    re-injected into every block so rdflib resolves namespace shortcuts.
    """
    prefix_lines: list[str] = []
    body_buffer: list[str] = []
    it = iter(lines)
    for line in it:
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            prefix_lines.append(line)
            continue
        if stripped.startswith("@prefix") or stripped.startswith("@base") \
                or stripped.lower().startswith("prefix ") \
                or stripped.lower().startswith("base "):
            prefix_lines.append(line)
            continue
        body_buffer.append(line)
        break

    def remaining() -> Iterator[str]:
        for buffered in body_buffer:
            yield buffered
        for upstream in it:
            yield upstream

    return "".join(prefix_lines), remaining()


def _iter_subject_blocks(lines: Iterable[str]) -> Iterator[str]:
    """
    Yield one subject's Turtle block per item. A block ends at the first `.`
    encountered outside any string literal. Handles `"..."` literals,
    `'''...'''` and `\"\"\"...\"\"\"` long-string literals, and `<...>` IRIs.
    """
    buf: list[str] = []
    in_triple_quote: Optional[str] = None      # '\"\"\"' or "'''" while open, else None
    in_string: Optional[str] = None            # '"' or "'" while open, else None
    in_iri = False
    in_line_comment = False

    for line in lines:
        i = 0
        n = len(line)
        while i < n:
            ch = line[i]

            if in_line_comment:
                if ch == "\n":
                    in_line_comment = False
                buf.append(ch)
                i += 1
                continue

            if in_triple_quote is not None:
                buf.append(ch)
                if line.startswith(in_triple_quote, i):
                    buf.append(line[i + 1:i + 3])
                    i += 3
                    in_triple_quote = None
                    continue
                if ch == "\\" and i + 1 < n:
                    buf.append(line[i + 1])
                    i += 2
                    continue
                i += 1
                continue

            if in_string is not None:
                buf.append(ch)
                if ch == "\\" and i + 1 < n:
                    buf.append(line[i + 1])
                    i += 2
                    continue
                if ch == in_string:
                    in_string = None
                i += 1
                continue

            if in_iri:
                buf.append(ch)
                if ch == ">":
                    in_iri = False
                i += 1
                continue

            if ch == "#":
                in_line_comment = True
                buf.append(ch)
                i += 1
                continue

            if line.startswith('"""', i) or line.startswith("'''", i):
                in_triple_quote = line[i:i + 3]
                buf.append(line[i:i + 3])
                i += 3
                continue

            if ch == '"' or ch == "'":
                in_string = ch
                buf.append(ch)
                i += 1
                continue

            if ch == "<":
                in_iri = True
                buf.append(ch)
                i += 1
                continue

            if ch == ".":
                buf.append(ch)
                # `.` is a statement terminator only when followed by whitespace,
                # end-of-line, or end-of-input. Otherwise it's part of an IRI
                # (already covered above) or a decimal literal that didn't open
                # a string.
                rest = line[i + 1:]
                if rest == "" or rest[0].isspace() or rest.startswith("#"):
                    block = "".join(buf).strip()
                    if block:
                        yield block + "\n"
                    buf = []
                i += 1
                continue

            buf.append(ch)
            i += 1

    tail = "".join(buf).strip()
    if tail:
        yield tail + "\n"


def _block_is_interesting(block_text: str) -> bool:
    """Cheap pre-filter: skip blocks that obviously contain nothing we care about.

    For dbnary:Translation blocks we additionally require that the block targets
    English — non-English translations would never populate `surface_en` and
    parsing them is the dominant cost (≈95% of all triples in the French dump
    are non-English translation triples), so this short-circuit roughly 10x's
    the parser throughput.
    """
    if not any(marker in block_text for marker in (
        "LexicalEntry", "LexicalSense", "Form", "Translation",
        "writtenRep", "writtenForm", "canonicalForm", "partOfSpeech",
        "definition", "senseTranslation", "rdfs:label", "isTranslationOf",
    )):
        return False
    if "dbnary:Translation" in block_text and "lexvo:eng" not in block_text:
        return False
    return True


@click.command()
@click.option("--config", default="config.yml")
@click.option("--language", default="fr")
def main(config: str, language: str) -> None:
    DBnaryIngester(language=language).run()


if __name__ == "__main__":
    main()
