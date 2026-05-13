"""F-321 Phase B — classify all .docx files in Chadi's tutoring archive.

Pipeline:
  1. Glob /c/Users/pc/Downloads/*.docx (excluding ~$ lock files).
  2. Collapse duplicate-suffix filenames to canonical representatives.
  3. Pre-classify by filename pattern — publisher imports skip Haiku.
  4. Read each surviving file, pre-classify by content (publisher
     attribution / ISBN). Surviving files go to Haiku.
  5. Async batched Haiku call (concurrency 8) with per-file budget cap.
  6. Write data/f321_classification.csv with one row per file.
  7. Print cost summary + verdict distribution + STOP if total cost
     trends above $1.

CSV columns:
  filename, verdict, source_type, content_type, has_tables,
  has_paragraph_glosses, suggested_topic_slug, confidence, reasoning,
  skipped_reason (empty if classified, populated if pre-skipped),
  input_tokens, output_tokens, file_size_bytes

Usage:
  python -m scripts.classify_f321_docx               # full run
  python -m scripts.classify_f321_docx --limit 10    # smoke test
  python -m scripts.classify_f321_docx --dry-run     # filenames only

Output sentinel: data/f321_classification.csv is gitignored — it's
ephemeral. The Phase C runner reads it back. Re-running is safe —
the CSV is overwritten in full.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import logging
import re
import sys
import time
from pathlib import Path
from typing import Optional

from app.config import settings
from app.services.ai_router import pick_model
from app.services.anthropic_client import call_anthropic
from app.services.f321_classifier import (
    CLASSIFIER_SYSTEM_PROMPT,
    build_classifier_user_prompt,
    collapse_duplicate_filenames,
    extract_docx_text,
    is_publisher_import_by_content,
    is_publisher_import_by_filename,
)


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


ARCHIVE_DIR = Path("/c/Users/pc/Downloads")
ALT_ARCHIVE_DIR = Path("C:/Users/pc/Downloads")  # Windows path fallback
OUTPUT_CSV = Path("data/f321_classification.csv")
# Concurrency 4: initial run at 8 hit 429s on >50% of calls. Anthropic's
# per-minute token cap throttles aggressive bursts; 4 stays comfortably
# under for Haiku 4.5.
CONCURRENCY = 4
# Retry policy: up to 5 backoff retries on 429 / ConnectError, with
# jittered exponential backoff capped at 30s.
MAX_RETRIES = 5

# Cost rates per million tokens (Anthropic Haiku 4.5 pricing locked
# 2026-05-12 per F-311 config).
HAIKU_INPUT_RATE = 0.80
HAIKU_OUTPUT_RATE = 4.00

# Hard ceiling for Phase B alone. Beyond this, stop and surface.
PHASE_B_COST_CEILING = 1.50


def _list_archive_docx() -> list[Path]:
    """Glob the archive directory for real .docx files (excluding
    Word lock files prefixed with ~$). Tries POSIX path first, falls
    back to the Windows path under Git Bash."""
    for root in (ARCHIVE_DIR, ALT_ARCHIVE_DIR):
        try:
            files = [
                p for p in root.glob("*.docx")
                if not p.name.startswith("~$")
            ]
            if files:
                return sorted(files)
        except OSError:
            continue
    return []


async def classify_one(
    path: Path,
    sem: asyncio.Semaphore,
    model: str,
) -> dict:
    """Classify a single file. Returns a dict with all CSV columns.
    Calls Haiku unless a pre-filter fires first (no API call in that
    case)."""
    row: dict = {
        "filename": path.name,
        "verdict": "",
        "source_type": "",
        "content_type": "",
        "has_tables": "",
        "has_paragraph_glosses": "",
        "suggested_topic_slug": "",
        "confidence": "",
        "reasoning": "",
        "skipped_reason": "",
        "input_tokens": 0,
        "output_tokens": 0,
        "file_size_bytes": path.stat().st_size if path.exists() else 0,
    }

    # Pre-filter 1: filename pattern.
    if is_publisher_import_by_filename(path.name):
        row["verdict"] = "SKIP"
        row["source_type"] = "third_party_publisher_DO_NOT_EXTRACT"
        row["skipped_reason"] = "filename_publisher_pattern"
        row["reasoning"] = "Pre-skip by filename pattern (publisher series)"
        return row

    # Read text (also needed for Pre-filter 2).
    text = extract_docx_text(path)
    if not text:
        row["verdict"] = "SKIP"
        row["source_type"] = ""
        row["skipped_reason"] = "empty_or_unreadable"
        row["reasoning"] = "Empty or unreadable .docx"
        return row

    # Pre-filter 2: content publisher attribution / ISBN.
    publisher_marker = is_publisher_import_by_content(text[:2000])
    if publisher_marker:
        row["verdict"] = "SKIP"
        row["source_type"] = "third_party_publisher_DO_NOT_EXTRACT"
        row["skipped_reason"] = f"content_marker:{publisher_marker}"
        row["reasoning"] = f"Pre-skip by content marker: {publisher_marker}"
        return row

    # Haiku classification with 429/ConnectError retry + jittered
    # exponential backoff.
    user_prompt = build_classifier_user_prompt(path.name, text)
    import random as _random
    import httpx as _httpx
    async with sem:
        content = None
        meta: dict = {}
        last_exc: Optional[Exception] = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                content, meta = await call_anthropic(
                    system=CLASSIFIER_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": user_prompt}],
                    model=model,
                    max_tokens=400,
                    cache_system=True,
                    return_meta=True,
                )
                last_exc = None
                break
            except _httpx.HTTPStatusError as exc:
                status_code = getattr(exc.response, "status_code", None)
                last_exc = exc
                if status_code == 429 and attempt < MAX_RETRIES:
                    backoff = min(2 ** attempt + _random.random(), 30.0)
                    await asyncio.sleep(backoff)
                    continue
                break
            except (_httpx.ConnectError, _httpx.ReadError, _httpx.TimeoutException) as exc:
                last_exc = exc
                if attempt < MAX_RETRIES:
                    backoff = min(2 ** attempt + _random.random(), 30.0)
                    await asyncio.sleep(backoff)
                    continue
                break
            except Exception as exc:
                last_exc = exc
                break
        if last_exc is not None or content is None:
            row["verdict"] = "ERROR"
            err = last_exc if last_exc is not None else Exception("no response")
            row["skipped_reason"] = f"haiku_error:{type(err).__name__}"
            row["reasoning"] = str(err)[:200]
            return row

    row["input_tokens"] = (
        meta.get("input_tokens", 0)
        + meta.get("cache_creation_input_tokens", 0)
        + meta.get("cache_read_input_tokens", 0)
    )
    row["output_tokens"] = meta.get("output_tokens", 0)

    parsed: Optional[dict] = None
    if isinstance(content, dict):
        parsed = content
    elif isinstance(content, str):
        # Strip optional code fences.
        stripped = content.strip()
        if stripped.startswith("```"):
            stripped = re.sub(r"^```(?:json)?", "", stripped).rstrip("`").strip()
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            row["verdict"] = "ERROR"
            row["skipped_reason"] = "json_parse_failure"
            row["reasoning"] = f"Raw: {content[:200]}"
            return row

    if not isinstance(parsed, dict):
        row["verdict"] = "ERROR"
        row["skipped_reason"] = "unexpected_response_shape"
        row["reasoning"] = f"Type {type(parsed).__name__}"
        return row

    row["verdict"] = str(parsed.get("verdict", "")).strip()
    row["source_type"] = str(parsed.get("source_type", "")).strip()
    row["content_type"] = str(parsed.get("content_type", "")).strip()
    row["has_tables"] = str(parsed.get("has_tables", "")).lower()
    row["has_paragraph_glosses"] = str(parsed.get("has_paragraph_glosses", "")).lower()
    row["suggested_topic_slug"] = (
        str(parsed.get("suggested_topic_slug") or "").strip() or ""
    )
    row["confidence"] = str(parsed.get("confidence", "")).strip()
    row["reasoning"] = str(parsed.get("reasoning", "")).strip()[:300]
    return row


def _existing_classification_rows() -> dict[str, dict]:
    """Load existing CSV (if any) into a dict by filename."""
    if not OUTPUT_CSV.exists():
        return {}
    with OUTPUT_CSV.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        return {row["filename"]: row for row in reader}


async def main_async(limit: Optional[int], dry_run: bool, retry_errors: bool) -> int:
    files = _list_archive_docx()
    if not files:
        logger.error(
            "No .docx files found in %s or %s — check archive path",
            ARCHIVE_DIR, ALT_ARCHIVE_DIR,
        )
        return 1

    logger.info("Found %d raw .docx files (pre-dedup)", len(files))
    canonical_names = collapse_duplicate_filenames([f.name for f in files])
    name_to_path = {f.name: f for f in files}
    files = [name_to_path[n] for n in canonical_names if n in name_to_path]
    logger.info("Post-dedup: %d files", len(files))

    if limit:
        files = files[:limit]
        logger.info("--limit=%d applied: %d files", limit, len(files))

    if dry_run:
        logger.info("--dry-run: listing files only")
        for f in files:
            logger.info("  %s", f.name)
        return 0

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    # Retry-only mode: keep all clean rows, retry only ERROR rows.
    keep_rows: list[dict] = []
    if retry_errors:
        existing = _existing_classification_rows()
        if not existing:
            logger.error("--retry-errors requires an existing CSV at %s", OUTPUT_CSV)
            return 1
        retry_names = {
            name for name, row in existing.items()
            if row.get("verdict") == "ERROR"
        }
        keep_rows = [
            row for name, row in existing.items()
            if name not in retry_names
        ]
        files = [f for f in files if f.name in retry_names]
        logger.info(
            "--retry-errors: keeping %d clean rows, retrying %d error rows",
            len(keep_rows), len(files),
        )
        if not files:
            logger.info("No ERROR rows to retry — exiting clean")
            return 0

    sem = asyncio.Semaphore(CONCURRENCY)
    model = pick_model("vocab")
    logger.info("Classifying %d files via %s (concurrency=%d)", len(files), model, CONCURRENCY)
    if not settings.ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY not set")
        return 1

    start = time.monotonic()
    rows = await asyncio.gather(*(classify_one(p, sem, model) for p in files))
    elapsed = time.monotonic() - start

    total_input_tokens = sum(r["input_tokens"] for r in rows)
    total_output_tokens = sum(r["output_tokens"] for r in rows)
    cost = (
        total_input_tokens * HAIKU_INPUT_RATE / 1_000_000
        + total_output_tokens * HAIKU_OUTPUT_RATE / 1_000_000
    )

    # Write CSV — merge keep_rows (if retry-mode) with newly classified rows
    fieldnames = [
        "filename", "verdict", "source_type", "content_type",
        "has_tables", "has_paragraph_glosses", "suggested_topic_slug",
        "confidence", "reasoning", "skipped_reason",
        "input_tokens", "output_tokens", "file_size_bytes",
    ]
    all_rows = rows + keep_rows
    all_rows.sort(key=lambda r: r.get("filename", ""))
    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_rows:
            # Normalize int columns for keep_rows (CSV reads as str)
            for k in ("input_tokens", "output_tokens", "file_size_bytes"):
                if k in row and isinstance(row[k], str) and row[k].isdigit():
                    row[k] = int(row[k])
            writer.writerow(row)

    # Summary (over the FULL merged CSV, not just this run)
    verdict_counts: dict[str, int] = {}
    source_type_counts: dict[str, int] = {}
    topic_counts: dict[str, int] = {}
    skip_reasons: dict[str, int] = {}
    for row in all_rows:
        verdict_counts[row["verdict"]] = verdict_counts.get(row["verdict"], 0) + 1
        if row["source_type"]:
            source_type_counts[row["source_type"]] = source_type_counts.get(row["source_type"], 0) + 1
        slug = row["suggested_topic_slug"]
        if slug:
            topic_counts[slug] = topic_counts.get(slug, 0) + 1
        if row["skipped_reason"]:
            skip_reasons[row["skipped_reason"]] = skip_reasons.get(row["skipped_reason"], 0) + 1

    print()
    print("=" * 60)
    print(f"Phase B classification complete in {elapsed:.1f}s")
    print(f"Files classified: {len(rows)}")
    print(f"Output: {OUTPUT_CSV}")
    print()
    print("Verdict distribution:")
    for v, n in sorted(verdict_counts.items(), key=lambda x: -x[1]):
        print(f"  {v:18s} {n:4d}")
    print()
    print("Source-type distribution:")
    for st, n in sorted(source_type_counts.items(), key=lambda x: -x[1]):
        print(f"  {st:42s} {n:4d}")
    print()
    print("Topic-slug suggestions (Phase 1 lock: faux_amis, calques_anglais, prepositions_a_de_dans_par_pour):")
    for slug, n in sorted(topic_counts.items(), key=lambda x: -x[1]):
        print(f"  {slug:42s} {n:4d}")
    print()
    if skip_reasons:
        print("Pre-skip reasons:")
        for reason, n in sorted(skip_reasons.items(), key=lambda x: -x[1]):
            print(f"  {reason:42s} {n:4d}")
        print()
    print(f"Input tokens:  {total_input_tokens:,}")
    print(f"Output tokens: {total_output_tokens:,}")
    print(f"Cost:          ${cost:.4f}")
    print(f"Ceiling:       ${PHASE_B_COST_CEILING:.2f}")
    print("=" * 60)

    if cost > PHASE_B_COST_CEILING:
        logger.error("Phase B cost ${%.4f} exceeded ceiling ${%.2f}", cost, PHASE_B_COST_CEILING)
        return 2
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--retry-errors", action="store_true",
                        help="Re-classify only ERROR rows in existing CSV")
    args = parser.parse_args()
    return asyncio.run(main_async(args.limit, args.dry_run, args.retry_errors))


if __name__ == "__main__":
    sys.exit(main())
