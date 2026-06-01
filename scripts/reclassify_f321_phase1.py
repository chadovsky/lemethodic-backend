"""F-321 CSV regen -- per-chunk reclassification from phase1_review.csv.

Recovery path (intermediate extraction.csv / classification.csv are gone):
  - Source: seeds/vocab/phase1_review.csv (1,684 rows, valid UTF-8)
  - Per-chunk Haiku classification → 5 buckets
  - Writes new phase1_review.csv + phase2_deferred.csv

Fixes applied:
  1. utf-8-sig (BOM) on output (Excel auto-detects UTF-8)
  2. Per-chunk topic via Haiku (not inherited per-file)
  3. Deterministic pre-filter + Haiku NOISE_DROP for noise rows
  4. csv.QUOTE_ALL on output (every field quoted, naive splitters safe)

Buckets:
  faux_amis / calques_anglais / prepositions_a_de_dans_par_pour → phase1_review.csv
  OTHER_IN_SCOPE_TEACHABLE → phase2_deferred.csv
  NOISE_DROP → discarded

Usage:
  python -m scripts.reclassify_f321_phase1
"""
from __future__ import annotations

import asyncio
import csv
import json
import logging
import random as _random
import re
import sys
import time
from pathlib import Path
from typing import Optional

import httpx as _httpx

from app.config import settings
from app.services.ai_router import pick_model
from app.services.anthropic_client import call_anthropic


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


SOURCE_CSV = Path("seeds/vocab/phase1_review.csv")
# Write to a staging path so we never conflict with the source file on disk.
# After validation, commit via git plumbing or rename manually.
PHASE1_OUTPUT = Path("seeds/vocab/phase1_review_new.csv")
PHASE2_OUTPUT = Path("seeds/vocab/phase2_deferred.csv")

PHASE1_TOPICS = {"faux_amis", "calques_anglais", "prepositions_a_de_dans_par_pour"}
VALID_LABELS = PHASE1_TOPICS | {"OTHER_IN_SCOPE_TEACHABLE", "NOISE_DROP"}

BATCH_SIZE = 10
CONCURRENCY = 4
MAX_RETRIES = 5
MAX_TOKENS = 512  # 10 labels avg 5T each + breathing room

# Cost ceiling for this run ($5 F-321 total; phase B+C already used ~$0.25)
COST_CEILING = 4.50
HAIKU_INPUT_RATE = 0.80
HAIKU_OUTPUT_RATE = 4.00

SYSTEM_PROMPT = """\
You are classifying French/English vocabulary and grammar pairs for a TCF Canada French prep app.

For each numbered pair, return exactly one label from this list:

faux_amis
  False cognates: a French word looks like an English word but means something different.
  Examples: "actuellement -> currently (not 'actually')", "blesser -> to hurt", "sensible -> sensitive"

calques_anglais
  Sentence or discourse patterns showing English calque: B1 English-architecture vs B2 French-architecture
  examples, discourse connectors, French argument/rhetoric structure patterns, conditionnel social code,
  clause-linking connectors.
  Examples: "B1: Je pense que... / B2: Ce qui me preoccupe c'est que...", "Bien que + subjonctif",
  "Comme / Puisque (cause first)"

prepositions_a_de_dans_par_pour
  Prepositional usage: verb + preposition, noun + preposition, a/de/dans/par/pour/en patterns.
  Examples: "fier de", "grace a", "par rapport a", "Chercher (no preposition!) -> Look for"

OTHER_IN_SCOPE_TEACHABLE
  Teachable French grammar not in the 3 main topics: verb conjugation, pronoun usage (relative /
  object / demonstrative / possessive), articles, subjonctif, participe passe pairs, vocabulary
  themes, oral production patterns.
  Examples: "Admis -> Admettre" (participe passe), "dont / lequel" (relative pronouns),
  "le notre / le tien" (possessives), "Aller -> Venir" (antonym verb pair)

NOISE_DROP
  Not teachable: exercise numbers, grammar table headers, section headings, bare category labels,
  dates, English-only text in the French field, self-referential rows (same text both sides),
  timing notes, administrative content, single-letter entries.
  Examples: "1er groupe (-ER", "AFFIRMATIVE", "February 12 2026", "Structure de chaque cours",
  "Lire", "MODULE 3.1", "Bonus", "Function 1"

Return ONLY a valid JSON array with exactly one label per pair in order. No explanation, no markdown.\
"""


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _is_deterministic_noise(chunk_fr: str, chunk_en: str) -> bool:
    """Fast deterministic pre-filter. Returns True for obvious noise."""
    fr = chunk_fr.strip()
    en = chunk_en.strip()
    if not fr:
        return True
    # Self-referential
    if fr and fr == en:
        return True
    # Very short (< 4 chars)
    if len(fr) < 4:
        return True
    # Section/exercise number prefix: "1.", "1.1 ", "MODULE"
    if re.match(r"^\s*(\d+(?:\.\d+)*[\.\)]?\s+|MODULE\s+\d)", fr, re.IGNORECASE):
        return True
    # Date patterns: "February 12 2026", "12/02/2026"
    if re.match(
        r"(?i)^(january|february|march|april|may|june|july|august|september"
        r"|october|november|december)\s+\d",
        fr,
    ):
        return True
    # Grammar formula notation (arrows/plusses, no diacritics)
    if ("+" in fr or "->" in fr or ">" in fr) and not any(
        c in fr.lower() for c in "àâäéèêëîïôöùûüÿçœæ"
    ):
        if len(fr.split()) <= 5:
            return True
    return False


def _build_batch_prompt(batch: list[dict]) -> str:
    lines: list[str] = []
    for i, row in enumerate(batch, 1):
        fr = row["chunk_fr"].replace("\n", " ").strip()
        en = row["chunk_en"].replace("\n", " ").strip()
        lines.append(f"{i}. FR: {fr}")
        if en:
            lines.append(f"   EN: {en}")
    return "\n".join(lines)


async def _classify_batch(
    batch: list[dict],
    sem: asyncio.Semaphore,
    model: str,
) -> list[str]:
    """Classify a batch of rows. Returns one label per row (same order).
    Falls back to OTHER_IN_SCOPE_TEACHABLE on repeated failure."""
    user_prompt = _build_batch_prompt(batch)
    last_exc: Optional[Exception] = None

    for attempt in range(MAX_RETRIES + 1):
        async with sem:
            try:
                content, meta = await call_anthropic(
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": user_prompt}],
                    model=model,
                    max_tokens=MAX_TOKENS,
                    cache_system=True,
                    return_meta=True,
                )
                last_exc = None
            except _httpx.HTTPStatusError as exc:
                last_exc = exc
                if getattr(exc.response, "status_code", None) == 429 and attempt < MAX_RETRIES:
                    await asyncio.sleep(min(2 ** attempt + _random.random(), 30.0))
                    continue
                break
            except (_httpx.ConnectError, _httpx.ReadError, _httpx.TimeoutException) as exc:
                last_exc = exc
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(min(2 ** attempt + _random.random(), 30.0))
                    continue
                break
            except Exception as exc:
                last_exc = exc
                break

        if last_exc is not None:
            break

        # Parse response
        raw = content if isinstance(content, str) else json.dumps(content)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw).strip()

        try:
            labels = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("JSON parse fail on attempt %d: %s", attempt, raw[:120])
            await asyncio.sleep(0.5)
            continue

        if not isinstance(labels, list) or len(labels) != len(batch):
            logger.warning(
                "Label count mismatch: got %d, expected %d (attempt %d)",
                len(labels) if isinstance(labels, list) else -1,
                len(batch),
                attempt,
            )
            await asyncio.sleep(0.5)
            continue

        # Normalise labels (Haiku occasionally adds spaces or wrong case)
        normalised: list[str] = []
        for lbl in labels:
            lbl_clean = str(lbl).strip().lower()
            # Fuzzy match
            if lbl_clean in {v.lower() for v in VALID_LABELS}:
                # Return the canonical casing
                for v in VALID_LABELS:
                    if v.lower() == lbl_clean:
                        normalised.append(v)
                        break
            else:
                logger.warning("Unknown label %r; defaulting to OTHER_IN_SCOPE_TEACHABLE", lbl)
                normalised.append("OTHER_IN_SCOPE_TEACHABLE")

        return normalised, meta

    logger.error(
        "Batch failed after %d attempts (%s). Defaulting all to OTHER_IN_SCOPE_TEACHABLE.",
        MAX_RETRIES + 1,
        last_exc,
    )
    return ["OTHER_IN_SCOPE_TEACHABLE"] * len(batch), {"input_tokens": 0, "output_tokens": 0}


async def main() -> int:
    if not SOURCE_CSV.exists():
        logger.error("Source not found: %s", SOURCE_CSV)
        return 1
    if not settings.ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY not set")
        return 1

    # Load source rows
    with SOURCE_CSV.open("r", encoding="utf-8", newline="") as fh:
        source_rows = list(csv.DictReader(fh))
    logger.info("Loaded %d rows from %s", len(source_rows), SOURCE_CSV)

    # Deterministic pre-filter
    pre_noise: list[dict] = []
    to_classify: list[dict] = []
    for row in source_rows:
        if _is_deterministic_noise(row.get("chunk_fr", ""), row.get("chunk_en", "")):
            pre_noise.append(row)
        else:
            to_classify.append(row)
    logger.info(
        "Pre-filter: %d deterministic NOISE_DROP, %d queued for Haiku",
        len(pre_noise), len(to_classify),
    )

    # Build batches
    batches: list[list[dict]] = [
        to_classify[i : i + BATCH_SIZE]
        for i in range(0, len(to_classify), BATCH_SIZE)
    ]
    logger.info("Batches: %d (size %d)", len(batches), BATCH_SIZE)

    model = pick_model("vocab")
    logger.info("Model: %s", model)

    sem = asyncio.Semaphore(CONCURRENCY)
    total_input_tokens = 0
    total_output_tokens = 0
    classified: list[tuple[dict, str]] = []  # (row, label)

    start = time.monotonic()
    for batch_idx, batch in enumerate(batches):
        result = await _classify_batch(batch, sem, model)
        labels, meta = result
        total_input_tokens += meta.get("input_tokens", 0) + meta.get("cache_creation_input_tokens", 0) + meta.get("cache_read_input_tokens", 0)
        total_output_tokens += meta.get("output_tokens", 0)
        for row, label in zip(batch, labels):
            classified.append((row, label))
        if (batch_idx + 1) % 20 == 0:
            cost_so_far = (
                total_input_tokens * HAIKU_INPUT_RATE / 1_000_000
                + total_output_tokens * HAIKU_OUTPUT_RATE / 1_000_000
            )
            logger.info(
                "Progress: %d/%d batches, cost so far $%.4f",
                batch_idx + 1, len(batches), cost_so_far,
            )
            if cost_so_far > COST_CEILING:
                logger.error("Cost ceiling $%.2f exceeded; aborting", COST_CEILING)
                return 2
    elapsed = time.monotonic() - start

    cost = (
        total_input_tokens * HAIKU_INPUT_RATE / 1_000_000
        + total_output_tokens * HAIKU_OUTPUT_RATE / 1_000_000
    )

    # Bucket the results
    fieldnames = [
        "chunk_fr", "chunk_en", "topic_slug", "source", "source_type",
        "register", "exam_tag", "cefr_level", "review_status",
        "review_notes", "source_file", "extractor", "dup_count",
    ]

    phase1_rows: list[dict] = []
    phase2_rows: list[dict] = []
    noise_count = len(pre_noise)

    for row, label in classified:
        if label == "NOISE_DROP":
            noise_count += 1
            continue
        out_row = {k: row.get(k, "") for k in fieldnames}
        if label in PHASE1_TOPICS:
            out_row["topic_slug"] = label
            phase1_rows.append(out_row)
        else:  # OTHER_IN_SCOPE_TEACHABLE
            out_row["topic_slug"] = label
            phase2_rows.append(out_row)

    # Sort by topic_slug then chunk_fr
    phase1_rows.sort(key=lambda r: (r["topic_slug"], r["chunk_fr"].lower()))
    phase2_rows.sort(key=lambda r: (r["topic_slug"], r["chunk_fr"].lower()))

    # Write outputs. Both paths are fresh (not the source file) so no lock conflict.
    # utf-8-sig (BOM) + QUOTE_ALL fix defects 1 and 4.
    for dest, rows in [(PHASE1_OUTPUT, phase1_rows), (PHASE2_OUTPUT, phase2_rows)]:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(
                fh, fieldnames=fieldnames, quoting=csv.QUOTE_ALL
            )
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    # Summary
    from collections import Counter
    p1_topics = Counter(r["topic_slug"] for r in phase1_rows)
    p2_topics = Counter(r["topic_slug"] for r in phase2_rows)

    print()
    print("=" * 60)
    print("F-321 reclassification complete")
    print(f"  Elapsed: {elapsed:.1f}s")
    print(f"  Model: {model}")
    print(f"  Input tokens:  {total_input_tokens:,}")
    print(f"  Output tokens: {total_output_tokens:,}")
    print(f"  Cost: ${cost:.4f}  (ceiling ${COST_CEILING:.2f})")
    print()
    print(f"Raw in:           {len(source_rows)}")
    print(f"  Pre-filter noise: {len(pre_noise)}")
    print(f"  Sent to Haiku:    {len(to_classify)} ({len(batches)} batches)")
    print(f"  NOISE_DROP total: {noise_count}")
    print(f"  phase1 rows:      {len(phase1_rows)}")
    print(f"  phase2 rows:      {len(phase2_rows)}")
    print()
    print("phase1 topic distribution:")
    for slug, n in sorted(p1_topics.items(), key=lambda x: -x[1]):
        print(f"  {slug:42s} {n:4d}")
    print()
    print("phase2 topic distribution:")
    for slug, n in sorted(p2_topics.items(), key=lambda x: -x[1]):
        print(f"  {slug:42s} {n:4d}")
    print()
    print(f"Output: {PHASE1_OUTPUT}")
    print(f"Output: {PHASE2_OUTPUT}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
