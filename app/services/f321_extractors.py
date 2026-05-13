"""F-321 — extractors for FR/EN chunk pairs from .docx tutoring files.

Three extractors, dispatched per-file based on the Phase B
classification verdict + structural signals:

  1. Table extractor (highest yield per audit, ~50% of HIGH content):
     Walks python-docx Document.tables, picks 2-column tables where
     col1 is FR-shaped (diacritics present) and col2 is EN-shaped
     (ASCII-dominant), drops header rows, emits (chunk_fr, chunk_en)
     pairs.

  2. Regex extractor (paragraph gloss patterns):
     Scans each paragraph for inline FR + EN pairings:
       - FR (EN)                  → "faire la grasse matinée (to sleep in)"
       - FR — EN  or  FR – EN     → "carte d'identité — ID card"
       - FR : EN                  → "rendez-vous : appointment"
       - **FR** EN  or  *FR* EN   → bold/italic followed by gloss

  3. Haiku-assisted extractor (catch-all for low-yield files):
     For PARTIAL / NEEDS_MANUAL files where table+regex emit <5
     chunks, send file text to Haiku with a strict JSON-array output
     prompt. Wrapped by the Phase C runner; this module exports the
     prompt + the response parser.

Output shape (all 3 extractors):
  list[ExtractedChunk] — a typed-dict with chunk_fr, chunk_en,
  register_hint, cefr_hint, extractor (provenance), source_file.

extractor field is a literal "table" | "regex" | "haiku" — preserved
through Phase D dedup so noise can be tracked back to the extractor
that produced it.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, TypedDict

from docx import Document
from docx.table import Table


class ExtractedChunk(TypedDict, total=False):
    chunk_fr: str
    chunk_en: Optional[str]
    register_hint: Optional[str]
    cefr_hint: Optional[str]
    extractor: str           # "table" | "regex" | "haiku"
    source_file: str


# ── helpers ──────────────────────────────────────────────────────


# French-specific characters used to distinguish FR text from EN.
# Caller measures the ratio of these in a string to decide column
# polarity in tables.
_FRENCH_CHARS = set("àâäéèêëîïôöùûüÿçœæÀÂÄÉÈÊËÎÏÔÖÙÛÜŸÇŒÆ")


def _fr_score(text: str) -> float:
    """Return the fraction of French-specific chars in `text`. A score
    above ~0.02 strongly suggests French; ASCII-only text scores 0."""
    if not text:
        return 0.0
    fr_count = sum(1 for c in text if c in _FRENCH_CHARS)
    return fr_count / len(text)


def _looks_french(text: str) -> bool:
    """True if `text` is likely French. Permissive — short strings
    without diacritics ("le chat") still return True if they contain
    common French function words. Caller uses this together with
    fr_score for paired-column decisions."""
    if _fr_score(text) > 0.01:
        return True
    # Function-word fallback for diacritic-less short FR strings.
    tokens = re.findall(r"\b\w+\b", text.lower())
    fr_function = {"le", "la", "les", "un", "une", "des", "du", "de",
                   "et", "ou", "mais", "où", "qui", "que", "quoi",
                   "à", "au", "aux", "dans", "par", "pour", "sur",
                   "avec", "sans", "ce", "cette", "ces", "il", "elle",
                   "je", "tu", "nous", "vous", "ils", "elles", "est",
                   "sont", "avoir", "être", "faire"}
    return any(tok in fr_function for tok in tokens)


def _is_likely_english(text: str) -> bool:
    """True if `text` is likely English. ASCII-dominant + English
    function words. Reject if French-diacritic ratio is high."""
    if not text:
        return False
    if _fr_score(text) > 0.03:
        return False
    tokens = re.findall(r"\b\w+\b", text.lower())
    en_function = {"the", "a", "an", "of", "to", "in", "on", "at",
                   "for", "with", "by", "as", "is", "are", "was",
                   "were", "be", "been", "being", "have", "has", "had",
                   "do", "does", "did", "i", "you", "he", "she", "it",
                   "we", "they", "this", "that", "these", "those",
                   "from", "but", "or", "and", "not", "no"}
    return any(tok in en_function for tok in tokens)


_INSTRUCTION_PREFIXES = (
    "exercice", "exercise", "instructions", "consigne",
    "complete", "complétez", "completez", "remplissez",
    "fill in", "fill-in", "fill the", "answer", "répondez",
    "traduisez", "translate", "trouvez", "find",
    "voir", "see", "page ", "chapter", "chapitre",
)


def _is_instruction_line(text: str) -> bool:
    """Filter out lines that are exercise instructions, not content.
    Lowercase match on common imperative prefixes."""
    if not text:
        return True
    lower = text.lower().strip()
    return any(lower.startswith(prefix) for prefix in _INSTRUCTION_PREFIXES)


def _clean(text: str) -> str:
    """Normalize whitespace + strip surrounding punctuation. Preserves
    accents and internal punctuation."""
    text = re.sub(r"\s+", " ", text).strip()
    text = text.strip(" \t\n\r-–—:•·.,;()[]\"'")
    return text


# ── table extractor ──────────────────────────────────────────────


def _is_header_row(cells: list[str]) -> bool:
    """Header-row heuristic. Common patterns: 'FR | EN', 'Français |
    Anglais', 'French | English', or cells starting with capitalized
    metadata."""
    if not cells:
        return True
    joined = " ".join(c.lower() for c in cells)
    header_markers = ("français", "francais", "anglais", "french",
                      "english", "traduction", "translation",
                      "expression", "meaning", "définition", "definition",
                      "chunk", "vocabulaire", "phrase")
    return any(m in joined for m in header_markers) and all(
        len(c) <= 30 for c in cells
    )


def extract_from_table(table: Table) -> list[ExtractedChunk]:
    """Extract FR/EN pairs from a single python-docx Table object.

    Heuristics:
      - Table must have ≥2 columns. If exactly 2: assume col0=FR,
        col1=EN (or reversed if col1 scores higher on _fr_score).
      - If >2 columns: pick the first column that looks French and
        the next column that looks English. Other columns ignored.
      - Drop header row(s) per _is_header_row.
      - Skip rows where either cell is empty, an instruction line,
        or too short to be a chunk (< 2 chars in FR, < 2 chars in EN
        when present).
    """
    rows = list(table.rows)
    if not rows:
        return []

    # Pick FR + EN column indices using the first 3 non-header rows
    # as a sample. If only 1 row exists, use it.
    sample_rows: list[list[str]] = []
    for row in rows[:6]:
        cells = [c.text.strip() for c in row.cells]
        if not _is_header_row(cells):
            sample_rows.append(cells)
        if len(sample_rows) >= 3:
            break
    if not sample_rows:
        return []

    n_cols = max(len(r) for r in sample_rows)
    if n_cols < 2:
        return []

    # Score each column: mean fr_score of its sample cells.
    col_scores: list[float] = []
    for col in range(n_cols):
        scores = [
            _fr_score(r[col]) for r in sample_rows if col < len(r)
        ]
        col_scores.append(sum(scores) / len(scores) if scores else 0.0)

    # FR column = highest fr_score. EN column = the column with
    # lowest fr_score AND containing English function words. Tie-break
    # by preferring adjacent columns.
    fr_col = max(range(n_cols), key=lambda i: col_scores[i])
    en_col_candidates = sorted(
        [i for i in range(n_cols) if i != fr_col],
        key=lambda i: col_scores[i],
    )
    en_col = en_col_candidates[0] if en_col_candidates else None

    # Confidence floor: if no column scores above ~0.005 for FR, the
    # table probably isn't an FR/EN pair table.
    if col_scores[fr_col] < 0.005 and not any(
        _looks_french(r[fr_col]) for r in sample_rows if fr_col < len(r)
    ):
        return []

    chunks: list[ExtractedChunk] = []
    for row in rows:
        cells = [c.text.strip() for c in row.cells]
        if _is_header_row(cells):
            continue
        if fr_col >= len(cells):
            continue
        fr_raw = _clean(cells[fr_col])
        if not fr_raw or len(fr_raw) < 2:
            continue
        if _is_instruction_line(fr_raw):
            continue
        en_raw: Optional[str] = None
        if en_col is not None and en_col < len(cells):
            en_raw = _clean(cells[en_col]) or None
            if en_raw and len(en_raw) < 2:
                en_raw = None
            if en_raw and _is_instruction_line(en_raw):
                en_raw = None
        chunks.append(ExtractedChunk(
            chunk_fr=fr_raw,
            chunk_en=en_raw,
            extractor="table",
        ))
    return chunks


def extract_tables_from_doc(path: Path) -> list[ExtractedChunk]:
    """Run table extraction over all tables in a .docx file. Stamps
    source_file on each chunk."""
    try:
        doc = Document(str(path))
    except Exception:
        return []
    out: list[ExtractedChunk] = []
    for table in doc.tables:
        chunks = extract_from_table(table)
        for c in chunks:
            c["source_file"] = path.name
        out.extend(chunks)
    return out


# ── regex extractor ──────────────────────────────────────────────


# Pattern A: "FR (EN)" — French text followed by English in parens.
# FR is the content before the last `(...)`. EN is the parenthesized
# tail. Anchored: must consume the whole line so we don't pull
# parenthetical asides out of prose.
_GLOSS_PARENS = re.compile(
    r"^\s*"
    r"(?P<fr>.{2,200}?)"
    r"\s*\(\s*"
    r"(?P<en>[A-Za-z][^)]{1,150})"
    r"\s*\)"
    r"\s*[.;,]?\s*$"
)

# Pattern B: "FR — EN" / "FR – EN" / "FR - EN" — em-dash, en-dash,
# or hyphen (with surrounding whitespace to disambiguate from
# hyphenated French compounds like "passe-temps").
_GLOSS_DASH = re.compile(
    r"^\s*"
    r"(?P<fr>.{2,200}?)"
    r"\s+[—–\-]\s+"
    r"(?P<en>[A-Za-z][^—–\-]{1,150})"
    r"\s*[.;,]?\s*$"
)

# Pattern C: "FR : EN" — colon with mandatory surrounding whitespace.
_GLOSS_COLON = re.compile(
    r"^\s*"
    r"(?P<fr>.{2,200}?)"
    r"\s+:\s+"
    r"(?P<en>[A-Za-z][^:]{1,150})"
    r"\s*[.;,]?\s*$"
)


# Pattern precedence: colon → dash → parens. Rationale: "boulot : work
# (informal)" should claim the colon split first, not the parens split.
# Within each line, the first matching pattern wins.
_GLOSS_PATTERNS = [_GLOSS_COLON, _GLOSS_DASH, _GLOSS_PARENS]


# Function-word sets for polarity disambiguation in gloss validation.
_FR_FUNCTION = {
    "le", "la", "les", "un", "une", "de", "du", "des",
    "et", "à", "ou", "qui", "que", "ce", "il", "elle",
    "je", "tu", "vous", "nous", "ils", "elles", "se",
    "ne", "pas", "mais", "sur", "dans", "par", "pour",
    "avec", "sans", "où", "y", "en", "son", "sa", "ses",
    "mon", "ma", "mes", "ton", "ta", "tes", "notre",
    "votre", "leur", "leurs", "cette", "ces", "cet",
    "d'", "l'", "n'", "s'", "j'", "m'", "t'", "c'",
}

_EN_FUNCTION = {
    "the", "a", "an", "of", "to", "in", "on", "at",
    "for", "with", "by", "as", "is", "are", "was",
    "were", "be", "been", "being", "have", "has",
    "had", "i", "you", "he", "she", "it", "we", "they",
    "this", "that", "these", "those", "my", "your",
    "his", "her", "our", "their", "from", "but", "or",
    "and", "not", "no", "do", "does", "did", "into",
    "onto", "out", "off", "up", "down", "over", "under",
}


def _is_valid_gloss(fr: str, en: str) -> bool:
    """Decide whether (fr, en) is a plausible French-English gloss pair.

    Rules (in order):
      1. EN side must NOT contain French-specific diacritics (fr_score
         > 0.01 would indicate polarity reversal — FR snuck onto the EN
         side, e.g. "the bakery (la boulangerie)").
      2. If FR side has clear French signal (fr_score > 0.01), accept.
      3. Both ASCII-only: tokenize each side, look up against function-
         word sets. Accept when polarity is unambiguous OR when the pair
         is a short lexical chunk (≤4 tokens each, no English-function-
         word contamination on the FR side).
    """
    if not fr or not en or len(fr) < 2 or len(en) < 2:
        return False
    if _fr_score(en) > 0.01:
        return False
    if _fr_score(fr) > 0.01:
        return True
    fr_tokens = set(re.findall(r"\b\w+\b", fr.lower()))
    en_tokens = set(re.findall(r"\b\w+\b", en.lower()))
    fr_has_fr = bool(fr_tokens & _FR_FUNCTION)
    en_has_en = bool(en_tokens & _EN_FUNCTION)
    fr_has_en = bool(fr_tokens & _EN_FUNCTION)
    en_has_fr = bool(en_tokens & _FR_FUNCTION)
    if fr_has_fr and en_has_en:
        return True
    if fr_has_en and not fr_has_fr and en_has_fr:
        return False  # Polarity reversed
    if len(fr_tokens) <= 4 and len(en_tokens) <= 4:
        # Short lexical chunk pair. Reject if FR side reads as pure
        # English with no FR markers.
        if fr_has_en and not fr_has_fr:
            return False
        return True
    return False


def extract_gloss_from_line(line: str) -> Optional[ExtractedChunk]:
    """Apply each gloss pattern in priority order. Returns the first
    match where (fr, en) passes the polarity check. None if no pattern
    matches or polarity is wrong."""
    if not line or _is_instruction_line(line):
        return None
    for pattern in _GLOSS_PATTERNS:
        m = pattern.match(line)
        if not m:
            continue
        fr_raw = _clean(m.group("fr"))
        en_raw = _clean(m.group("en"))
        if not _is_valid_gloss(fr_raw, en_raw):
            continue
        return ExtractedChunk(
            chunk_fr=fr_raw,
            chunk_en=en_raw,
            extractor="regex",
        )
    return None


def extract_regex_from_doc(path: Path) -> list[ExtractedChunk]:
    """Walk all paragraphs in the doc, apply gloss patterns to each."""
    try:
        doc = Document(str(path))
    except Exception:
        return []
    out: list[ExtractedChunk] = []
    for para in doc.paragraphs:
        chunk = extract_gloss_from_line(para.text)
        if chunk is not None:
            chunk["source_file"] = path.name
            out.append(chunk)
    return out


# ── Haiku-assisted extractor (prompt + response parser) ──────────


HAIKU_EXTRACTOR_SYSTEM_PROMPT = """You are a structured-data extractor for a French-language tutoring archive. Your input is the text of ONE .docx file written by a French tutor for anglophone students. Your output is a JSON array of {chunk_fr, chunk_en} pairs representing extractable FR/EN lexical content from the file.

OUTPUT SCHEMA (strict — return ONLY the JSON array, no prose, no markdown fences):

[
  {
    "chunk_fr": "<French expression / word / collocation, 2..200 chars>",
    "chunk_en": "<English gloss / translation, OR null if no clean translation in the source, 2..200 chars or null>",
    "register": "formel" | "semi_formel" | "informel" | "argotique" | null,
    "cefr_level": "A1" | "A2" | "B1" | "B2" | "C1" | "C2" | null
  },
  ...
]

EXTRACTION RULES:
1. Extract lexical chunks: idioms, expressions, collocations, fixed phrases, anglicismes, faux-amis, preposition+verb pairs. NOT full sentences from exercises. NOT bare grammar rules.
2. chunk_fr MUST be French text. chunk_en is its English gloss/translation if the source provides one; otherwise null. Never invent translations.
3. Skip exercise instructions ("Complete the sentences", "Translate to French", "Voir page 12").
4. Skip programme/calendar items ("Semaine 1", "Day 3 schedule"), heading lines without content, isolated dates.
5. Skip duplicate chunks within the same file. If the same FR expression appears 3 times, return it once.
6. Apply normalization: trim whitespace, strip surrounding punctuation, preserve internal hyphens + diacritics.
7. register is your inference from context if clear (formal letter → formel, slang → argotique). null if unclear.
8. cefr_level is your inference from complexity. null if unclear.

OUTPUT BOUNDS:
- Maximum 80 chunks per file. If the file has more, return the 80 highest-quality (clearest gloss, most idiomatic).
- If the file has zero extractable chunks (a programme, a calendar, pure exercise instructions), return [].

Return the JSON array NOW. No prose. No markdown. No commentary."""


def build_haiku_extractor_user_prompt(filename: str, text: str) -> str:
    """Construct the per-file user prompt. Text is truncated at 8000
    chars (Haiku context budget for Phase 1)."""
    truncated = text[:8000]
    if len(text) > 8000:
        truncated += f"\n\n[... truncated; full length was {len(text)} chars]"
    return (
        f"Filename: {filename}\n\n"
        f"Text:\n```\n{truncated}\n```\n\n"
        "Extract the JSON array of {chunk_fr, chunk_en, register, cefr_level} now."
    )


def parse_haiku_extractor_response(
    response: object, source_file: str
) -> list[ExtractedChunk]:
    """Parse the Haiku response into ExtractedChunk records.
    Accepts a list (the expected shape) or a dict containing a list
    under a common key. Silently drops malformed entries."""
    if isinstance(response, dict):
        for key in ("chunks", "result", "results", "data"):
            if isinstance(response.get(key), list):
                response = response[key]
                break
        else:
            return []
    if not isinstance(response, list):
        return []
    out: list[ExtractedChunk] = []
    for item in response:
        if not isinstance(item, dict):
            continue
        chunk_fr = (item.get("chunk_fr") or "").strip()
        if not chunk_fr or len(chunk_fr) < 2 or len(chunk_fr) > 200:
            continue
        chunk_en_raw = item.get("chunk_en")
        chunk_en: Optional[str] = None
        if isinstance(chunk_en_raw, str):
            chunk_en_stripped = chunk_en_raw.strip()
            if 2 <= len(chunk_en_stripped) <= 200:
                chunk_en = chunk_en_stripped
        register = item.get("register")
        if register not in (None, "formel", "semi_formel", "informel", "argotique"):
            register = None
        cefr = item.get("cefr_level")
        if cefr not in (None, "A1", "A2", "B1", "B2", "C1", "C2"):
            cefr = None
        out.append(ExtractedChunk(
            chunk_fr=chunk_fr,
            chunk_en=chunk_en,
            register_hint=register,
            cefr_hint=cefr,
            extractor="haiku",
            source_file=source_file,
        ))
    return out
