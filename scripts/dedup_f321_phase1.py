"""F-321 Phase D — dedup + topic-split for Chadi review prep.

Reads data/f321_extraction.csv (Phase C output) and produces TWO
review-ready CSVs:

  seeds/vocab/phase1_review.csv
    Chunks in scope for Phase 1 review NOW. Filter logic:
      1. Source file's classifier-suggested topic ∈
         {faux_amis, calques_anglais, prepositions_a_de_dans_par_pour}
         → chunk inherits that topic.
      2. Source file is Les_Moules_Complete_Framework.docx → chunk
         keeps file's suggestion if in the trio, else marked "book_lab"
         for Chadi to assign during review.
      3. Chunk text matches the preposition-content heuristic → chunk
         lands in prepositions_a_de_dans_par_pour regardless of file.
         (Per F-321 Phase D refinement 2026-05-13.)

  seeds/vocab/phase2_deferred.csv
    Every other chunk from chadi_authored + book_lab files. Tagged
    with the source file's classifier topic suggestion. Stashed for a
    future Phase 2 dispatch; not in this review burden.

Dedup heuristic:
  Normalize chunk_fr (lowercase, collapse whitespace, strip outer
  punctuation, preserve accents) → SHA-style hash → keep first
  occurrence (extractor priority: table > regex > haiku; sorted by
  source_file for determinism).

Output column shape (both CSVs):
  chunk_fr, chunk_en, topic_slug, source, source_type, register,
  exam_tag, cefr_level, review_status, review_notes, source_file,
  extractor, dup_count

Usage:
  python -m scripts.dedup_f321_phase1
"""
from __future__ import annotations

import csv
import logging
import re
import sys
from collections import Counter
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


CLASSIFICATION_CSV = Path("data/f321_classification.csv")
EXTRACTION_CSV = Path("data/f321_extraction.csv")
PHASE1_OUTPUT = Path("seeds/vocab/phase1_review.csv")
PHASE2_OUTPUT = Path("seeds/vocab/phase2_deferred.csv")

PHASE1_TOPICS = {
    "faux_amis",
    "calques_anglais",
    "prepositions_a_de_dans_par_pour",
}

# Per F-321 D2 source_type lock: Book-Lab content (this file only).
BOOK_LAB_FILES = {"Les_Moules_Complete_Framework.docx"}

# Content-inference heuristic for the prepositions topic. A chunk
# qualifies if it has 2..6 word-tokens AND contains at least one of
# the 6 target prepositions as a standalone word-boundary token.
# Accepts some false positives; Chadi's review pass filters those.
PREP_TARGETS = {"à", "de", "d'", "dans", "par", "pour", "en"}
_PREP_TOKEN_RE = re.compile(r"\b(?:à|de|d'|dans|par|pour|en)\b", re.IGNORECASE)


def _normalize_for_dedup(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip().lower()
    text = text.strip(" \t\n\r-–—:•·.,;()[]\"'")
    return text


# Noise filters — drop chunks that are obviously not real lexical
# content. Applied at Phase D so Chadi's review burden isn't padded
# with exercise numbering + placeholder lines. The deterministic
# table extractor (Phase C) pulls in numbered exercise prompts +
# section headers as a side-effect; this filter catches them before
# they hit the review CSV.

# Matches "1.", "1.1 ", "2.3.4 " at start — section/exercise numbers
_EXERCISE_NUMBER_PREFIX = re.compile(r"^\s*\d+(?:\.\d+)*[\.\)]?\s+")

# Matches exercise placeholders (___ blanks, [...] markers, +)
_PLACEHOLDER_RE = re.compile(r"___+|\[\.\.\.\]|^\s*\+\s+")

# Matches "1. EN", "2. After", "1.1 Article" — numbered headings
_NUMBERED_HEADING_RE = re.compile(r"^\s*\d+\.\d*\s+[A-Z][A-Z\s]+$")

# Tokenization for length check
_WORD_RE = re.compile(r"\b\w+\b", re.UNICODE)


def _is_noise_chunk(chunk_fr: str, chunk_en: str) -> bool:
    """Return True if the chunk is obviously noise (exercise number,
    section heading, placeholder line, too short, etc.). Caller drops."""
    if not chunk_fr:
        return True
    fr = chunk_fr.strip()
    if len(fr) < 4:
        return True
    # Drop exercise numbering at start ("1.", "1.1 ", "2.")
    if _EXERCISE_NUMBER_PREFIX.match(fr):
        return True
    # Drop placeholder blanks
    if _PLACEHOLDER_RE.search(fr):
        return True
    # Drop numbered headings ("1. EN Replaces ...")
    if _NUMBERED_HEADING_RE.match(fr):
        return True
    # Drop chunks that are mostly punctuation/symbols
    tokens = _WORD_RE.findall(fr)
    if not tokens:
        return True
    # Drop if the chunk has only 1 token AND that token is shorter
    # than 4 chars (catches "+", "→", "(no", etc.)
    if len(tokens) == 1 and len(tokens[0]) < 4:
        return True
    # Drop chunks that look like grammar formula notation (capital
    # words connected by + or → arrows, no diacritics)
    if "→" in fr or " + " in fr:
        if not any(c in "àâäéèêëîïôöùûüÿçœæ" for c in fr.lower()):
            # ASCII-only formula notation
            return True
    return False


def _token_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def _chunk_matches_preposition_heuristic(chunk_fr: str) -> bool:
    """True if the chunk plausibly belongs in the prepositions topic
    by content alone. Length-gated (2..6 tokens) to avoid pulling in
    long sentences."""
    tokens = re.findall(r"\b\w+\b", chunk_fr)
    if not (2 <= len(tokens) <= 6):
        return False
    if not _PREP_TOKEN_RE.search(chunk_fr):
        return False
    return True


def _topic_for_chunk(chunk: dict, file_topic: str, source_file: str) -> tuple[str, bool]:
    """Decide the topic_slug for this chunk + whether it's in Phase 1
    scope. Returns (topic_slug, in_phase1).

    Priority order:
      1. Preposition content heuristic — overrides file topic (per
         F-321 Phase D refinement). Chunks belonging to the
         prepositions topic land there regardless of source file's
         overall classification.
      2. File classifier suggestion if in PHASE1_TOPICS.
      3. Book-Lab file gets in_phase1=True with file suggestion or
         "book_lab" placeholder.
      4. Otherwise: in_phase1=False, topic_slug = file suggestion or
         "other".
    """
    chunk_fr = chunk.get("chunk_fr", "")
    # (1) Content-inference for prepositions.
    if _chunk_matches_preposition_heuristic(chunk_fr):
        return ("prepositions_a_de_dans_par_pour", True)
    # (2) File-level topic match.
    if file_topic in PHASE1_TOPICS:
        return (file_topic, True)
    # (3) Book-Lab special.
    if source_file in BOOK_LAB_FILES:
        # Use file suggestion if useful; else mark for Chadi assignment.
        return (file_topic if file_topic else "book_lab_unassigned", True)
    # (4) Phase 2 deferral.
    return (file_topic or "other", False)


def _read_classification_topics() -> dict[str, str]:
    """Map source_file → classifier suggested_topic_slug."""
    if not CLASSIFICATION_CSV.exists():
        logger.error("Missing %s", CLASSIFICATION_CSV)
        sys.exit(1)
    with CLASSIFICATION_CSV.open("r", encoding="utf-8", newline="") as fh:
        return {row["filename"]: row.get("suggested_topic_slug", "") for row in csv.DictReader(fh)}


def main() -> int:
    if not EXTRACTION_CSV.exists():
        logger.error("Missing %s — run scripts.extract_f321_phase1 first", EXTRACTION_CSV)
        return 1

    file_topic_map = _read_classification_topics()
    with EXTRACTION_CSV.open("r", encoding="utf-8", newline="") as fh:
        raw_chunks = list(csv.DictReader(fh))
    logger.info("Loaded %d raw chunks from %s", len(raw_chunks), EXTRACTION_CSV)

    # Sort for deterministic dedup order: table > regex > haiku, then
    # source_file alphabetical. Within same extractor+file, preserve
    # original order.
    extractor_priority = {"table": 0, "regex": 1, "haiku": 2}
    raw_chunks.sort(key=lambda c: (
        extractor_priority.get(c.get("extractor", ""), 9),
        c.get("source_file", ""),
    ))

    # Noise-filter pass (before dedup so we don't dedup-key on
    # garbage). Applied per F-321 Phase D refinement to keep review
    # burden manageable.
    pre_filter_count = len(raw_chunks)
    raw_chunks = [
        c for c in raw_chunks
        if not _is_noise_chunk(c.get("chunk_fr", ""), c.get("chunk_en", ""))
    ]
    dropped = pre_filter_count - len(raw_chunks)
    logger.info(
        "Noise filter dropped %d chunks (%d → %d)",
        dropped, pre_filter_count, len(raw_chunks),
    )

    # Dedup pass: hash normalized chunk_fr, count duplicates, keep
    # the first occurrence.
    dedup_buckets: dict[str, dict] = {}
    dup_count: Counter = Counter()
    for chunk in raw_chunks:
        chunk_fr = chunk.get("chunk_fr") or ""
        key = _normalize_for_dedup(chunk_fr)
        if not key:
            continue
        dup_count[key] += 1
        if key not in dedup_buckets:
            dedup_buckets[key] = chunk
    logger.info("Post-dedup: %d unique chunks (%.1f%% reduction)",
                len(dedup_buckets),
                100.0 * (1 - len(dedup_buckets) / len(raw_chunks)) if raw_chunks else 0)

    # Split + topic assignment.
    phase1_rows: list[dict] = []
    phase2_rows: list[dict] = []
    for key, chunk in dedup_buckets.items():
        source_file = chunk.get("source_file", "")
        file_topic = file_topic_map.get(source_file, chunk.get("suggested_topic_slug", ""))
        topic_slug, in_phase1 = _topic_for_chunk(chunk, file_topic, source_file)
        row = {
            "chunk_fr": chunk.get("chunk_fr", ""),
            "chunk_en": chunk.get("chunk_en", ""),
            "topic_slug": topic_slug,
            "source": chunk.get("source_file", ""),
            "source_type": chunk.get("source_type", ""),
            "register": chunk.get("register_hint", "") or "",
            "exam_tag": "",
            "cefr_level": chunk.get("cefr_hint", "") or "",
            "review_status": "",
            "review_notes": "",
            "source_file": chunk.get("source_file", ""),
            "extractor": chunk.get("extractor", ""),
            "dup_count": dup_count[key],
        }
        if in_phase1:
            phase1_rows.append(row)
        else:
            phase2_rows.append(row)

    # Sort each output by topic_slug then chunk_fr for review-friendliness.
    phase1_rows.sort(key=lambda r: (r["topic_slug"], r["chunk_fr"].lower()))
    phase2_rows.sort(key=lambda r: (r["topic_slug"], r["chunk_fr"].lower()))

    fieldnames = [
        "chunk_fr", "chunk_en", "topic_slug", "source", "source_type",
        "register", "exam_tag", "cefr_level", "review_status",
        "review_notes", "source_file", "extractor", "dup_count",
    ]
    for path, rows in [(PHASE1_OUTPUT, phase1_rows), (PHASE2_OUTPUT, phase2_rows)]:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    # Summary
    print()
    print("=" * 60)
    print("Phase D dedup + split complete")
    print(f"Raw chunks (from Phase C): {len(raw_chunks)}")
    print(f"After dedup:               {len(dedup_buckets)}")
    print(f"  In Phase 1 review:       {len(phase1_rows)}  → {PHASE1_OUTPUT}")
    print(f"  In Phase 2 deferred:     {len(phase2_rows)}  → {PHASE2_OUTPUT}")
    print()
    print("Phase 1 review topic distribution:")
    topic_counts = Counter(r["topic_slug"] for r in phase1_rows)
    for slug, n in sorted(topic_counts.items(), key=lambda x: -x[1]):
        print(f"  {slug:42s} {n:4d}")
    print()
    print("Phase 1 extractor distribution:")
    ext_counts = Counter(r["extractor"] for r in phase1_rows)
    for ext, n in sorted(ext_counts.items(), key=lambda x: -x[1]):
        print(f"  {ext:42s} {n:4d}")
    print()
    print("Phase 1 source_type distribution:")
    src_counts = Counter(r["source_type"] for r in phase1_rows)
    for src, n in sorted(src_counts.items(), key=lambda x: -x[1]):
        print(f"  {src:42s} {n:4d}")
    print()
    print("Phase 1 dup_count distribution (how many sources had each chunk):")
    dup_dist = Counter(r["dup_count"] for r in phase1_rows)
    for n, count in sorted(dup_dist.items()):
        marker = " (unique)" if n == 1 else ""
        print(f"  dup_count={n:3d}: {count:4d} chunks{marker}")
    print()
    print(f"Phase 1 review burden estimate (12 chunks/min): "
          f"{len(phase1_rows) / 12 / 60:.1f} hours")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
