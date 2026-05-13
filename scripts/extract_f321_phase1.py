"""F-321 Phase C — extraction over the classified .docx archive.

Pipeline:
  1. Read data/f321_classification.csv.
  2. For each row eligible for extraction (verdict in HIGH/PARTIAL/
     NEEDS_MANUAL AND source_type in chadi_authored/book_lab):
       a. Run table extractor (highest yield per audit).
       b. Run regex extractor over paragraphs.
       c. Combined unique chunk count → "table_regex_yield".
       d. If yield < HAIKU_THRESHOLD AND verdict != HIGH: queue for
          Haiku-assisted extraction.
  3. Three run modes:
     - --validation-mode: run Haiku-assisted on 5 sample files only,
       write data/f321_haiku_validation_sample.csv, exit. (Mandatory
       Chadi-approval gate per F-321 Phase A plan.)
     - --post-validation: run Haiku-assisted on the rest of the queue.
       Requires that validation file exists + a marker that says
       Chadi approved it.
     - --table-regex-only: run only table + regex, no Haiku calls.
  4. Write data/f321_extraction.csv (all chunks, pre-dedup).

CSV columns:
  source_file, extractor, chunk_fr, chunk_en, register_hint,
  cefr_hint, suggested_topic_slug, source_type
"""
from __future__ import annotations

import argparse
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
from app.services.f321_extractors import (
    HAIKU_EXTRACTOR_SYSTEM_PROMPT,
    build_haiku_extractor_user_prompt,
    extract_regex_from_doc,
    extract_tables_from_doc,
    parse_haiku_extractor_response,
)
from app.services.f321_classifier import extract_docx_text


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


ARCHIVE_DIR = Path("/c/Users/pc/Downloads")
ALT_ARCHIVE_DIR = Path("C:/Users/pc/Downloads")
CLASSIFICATION_CSV = Path("data/f321_classification.csv")
VALIDATION_CSV = Path("data/f321_haiku_validation_sample.csv")
VALIDATION_APPROVAL_FILE = Path("data/f321_haiku_validation_approved.txt")
EXTRACTION_CSV = Path("data/f321_extraction.csv")
CONCURRENCY = 4
MAX_RETRIES = 5
HAIKU_THRESHOLD = 5         # min chunks; below this, queue for Haiku
# Bumped from 2500 → 5000 after observing truncated-JSON failures on
# validation slice. 80 chunks * ~50 tokens/chunk = 4000-tok headroom.
HAIKU_MAX_TOKENS = 5000
VALIDATION_SAMPLE_SIZE = 5

HAIKU_INPUT_RATE = 0.80
HAIKU_OUTPUT_RATE = 4.00
# Phase C cost ceiling. Combined with Phase B's $0.20 stays under
# the F-321 $5 total.
PHASE_C_COST_CEILING = 4.50


def _resolve_archive_path(filename: str) -> Optional[Path]:
    for root in (ARCHIVE_DIR, ALT_ARCHIVE_DIR):
        candidate = root / filename
        if candidate.exists():
            return candidate
    return None


def _read_classification() -> list[dict]:
    if not CLASSIFICATION_CSV.exists():
        logger.error("Missing %s — run scripts.classify_f321_docx first", CLASSIFICATION_CSV)
        sys.exit(1)
    with CLASSIFICATION_CSV.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _eligible_rows(rows: list[dict]) -> list[dict]:
    return [
        r for r in rows
        if r.get("verdict") in ("HIGH", "PARTIAL", "NEEDS_MANUAL")
        and r.get("source_type") in ("chadi_authored", "book_lab")
    ]


def _normalize_for_dedup(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip().lower()
    text = text.strip(" \t\n\r-–—:•·.,;()[]\"'")
    return text


def _run_deterministic_extractors(path: Path) -> list[dict]:
    """Table + regex extractors. Dedup-within-file by normalized
    chunk_fr to avoid double-counting cell-vs-paragraph collisions."""
    chunks_table = extract_tables_from_doc(path)
    chunks_regex = extract_regex_from_doc(path)
    seen: set[str] = set()
    out: list[dict] = []
    for c in list(chunks_table) + list(chunks_regex):
        key = _normalize_for_dedup(c.get("chunk_fr") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(dict(c))
    return out


async def _run_haiku_extractor(
    path: Path,
    sem: asyncio.Semaphore,
    model: str,
    text: str,
) -> tuple[list[dict], dict]:
    """Returns (chunks, meta_with_tokens). On failure, chunks=[] and
    meta gets an `error` key."""
    user_prompt = build_haiku_extractor_user_prompt(path.name, text)
    async with sem:
        last_exc: Optional[Exception] = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                content, meta = await call_anthropic(
                    system=HAIKU_EXTRACTOR_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": user_prompt}],
                    model=model,
                    max_tokens=HAIKU_MAX_TOKENS,
                    cache_system=True,
                    return_meta=True,
                )
                last_exc = None
                break
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
            return [], {"error": str(last_exc)[:200], "input_tokens": 0, "output_tokens": 0}

    # Parse response. Accept dict (with array key) or list. On JSON
    # decode failure, attempt a lenient recovery — Haiku occasionally
    # exceeds max_tokens mid-array, leaving the response truncated
    # like `[ {...}, {...}, {...` (no closing brace). Trim back to the
    # last complete `}` and close the array.
    parsed: object
    if isinstance(content, list):
        parsed = content
    elif isinstance(content, str):
        stripped = content.strip()
        # Strip code fences (Haiku sometimes returns ```json ... ```).
        if stripped.startswith("```"):
            stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        if stripped.endswith("```"):
            stripped = stripped[:-3].rstrip()
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            # Lenient pass: find the last complete `}` in the buffer
            # and close the array. Only attempt for array-shaped output.
            if stripped.lstrip().startswith("["):
                last_close = stripped.rfind("}")
                if last_close > 0:
                    candidate = stripped[: last_close + 1] + "]"
                    try:
                        parsed = json.loads(candidate)
                    except json.JSONDecodeError:
                        return [], {
                            "error": f"json_parse_fail (lenient pass failed): "
                                     f"{content[:150]}",
                            "input_tokens": meta.get("input_tokens", 0),
                            "output_tokens": meta.get("output_tokens", 0),
                        }
                else:
                    return [], {
                        "error": f"json_parse_fail (no objects): {content[:150]}",
                        "input_tokens": meta.get("input_tokens", 0),
                        "output_tokens": meta.get("output_tokens", 0),
                    }
            else:
                return [], {
                    "error": f"json_parse_fail: {content[:150]}",
                    "input_tokens": meta.get("input_tokens", 0),
                    "output_tokens": meta.get("output_tokens", 0),
                }
    elif isinstance(content, dict):
        parsed = content
    else:
        return [], {"error": f"unexpected_type:{type(content).__name__}",
                    "input_tokens": meta.get("input_tokens", 0),
                    "output_tokens": meta.get("output_tokens", 0)}

    chunks = parse_haiku_extractor_response(parsed, path.name)
    return [dict(c) for c in chunks], {
        "input_tokens": (
            meta.get("input_tokens", 0)
            + meta.get("cache_creation_input_tokens", 0)
            + meta.get("cache_read_input_tokens", 0)
        ),
        "output_tokens": meta.get("output_tokens", 0),
    }


def _pick_validation_files(
    rows: list[dict],
    haiku_queue: list[dict],
) -> list[dict]:
    """Pick 5 files for the validation pass: prefer variety across
    verdicts and topic slugs."""
    if len(haiku_queue) <= VALIDATION_SAMPLE_SIZE:
        return haiku_queue
    by_verdict: dict[str, list[dict]] = {}
    for r in haiku_queue:
        by_verdict.setdefault(r["verdict"], []).append(r)
    picked: list[dict] = []
    # 2 PARTIAL, 2 NEEDS_MANUAL, 1 catch-all (in priority order).
    if "PARTIAL" in by_verdict:
        picked.extend(sorted(by_verdict["PARTIAL"], key=lambda r: r["filename"])[:2])
    if "NEEDS_MANUAL" in by_verdict:
        picked.extend(sorted(by_verdict["NEEDS_MANUAL"], key=lambda r: r["filename"])[:2])
    remaining = [r for r in haiku_queue if r not in picked]
    while len(picked) < VALIDATION_SAMPLE_SIZE and remaining:
        picked.append(remaining.pop(0))
    return picked[:VALIDATION_SAMPLE_SIZE]


def _write_chunks_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "source_file", "extractor", "chunk_fr", "chunk_en",
        "register_hint", "cefr_hint", "suggested_topic_slug",
        "source_type", "verdict",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


async def main_async(mode: str) -> int:
    classification = _read_classification()
    eligible = _eligible_rows(classification)
    logger.info("Eligible files: %d (HIGH=%d PARTIAL=%d NEEDS_MANUAL=%d)",
                len(eligible),
                sum(1 for r in eligible if r["verdict"] == "HIGH"),
                sum(1 for r in eligible if r["verdict"] == "PARTIAL"),
                sum(1 for r in eligible if r["verdict"] == "NEEDS_MANUAL"))

    # Step 1: deterministic extractors over all eligible files.
    per_file_meta: dict[str, dict] = {}  # filename → meta
    all_chunks: list[dict] = []
    for row in eligible:
        path = _resolve_archive_path(row["filename"])
        if path is None:
            logger.warning("Missing file on disk: %s", row["filename"])
            continue
        deterministic = _run_deterministic_extractors(path)
        for chunk in deterministic:
            chunk["suggested_topic_slug"] = row.get("suggested_topic_slug", "")
            chunk["source_type"] = row.get("source_type", "")
            chunk["verdict"] = row.get("verdict", "")
        all_chunks.extend(deterministic)
        per_file_meta[row["filename"]] = {
            "verdict": row["verdict"],
            "source_type": row["source_type"],
            "suggested_topic_slug": row.get("suggested_topic_slug", ""),
            "table_regex_yield": len(deterministic),
            "path": path,
        }
    logger.info("Table+regex pass complete. Total chunks: %d. Files with yield: %d / %d",
                len(all_chunks),
                sum(1 for m in per_file_meta.values() if m["table_regex_yield"] > 0),
                len(per_file_meta))

    # Step 2: queue for Haiku — files with low deterministic yield
    # AND verdict not HIGH (HIGH files we trust the deterministic pass for).
    haiku_queue = [
        row for row in eligible
        if row["filename"] in per_file_meta
        and per_file_meta[row["filename"]]["table_regex_yield"] < HAIKU_THRESHOLD
        and row["verdict"] != "HIGH"
    ]
    logger.info("Haiku queue (yield<%d AND not HIGH): %d files",
                HAIKU_THRESHOLD, len(haiku_queue))

    if mode == "table-regex-only":
        logger.info("--table-regex-only: writing extraction CSV without Haiku")
        _write_chunks_csv(EXTRACTION_CSV, all_chunks)
        return 0

    # Step 3: Haiku pass
    if not settings.ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY not set")
        return 1
    sem = asyncio.Semaphore(CONCURRENCY)
    model = pick_model("vocab")
    total_haiku_input_tokens = 0
    total_haiku_output_tokens = 0
    haiku_chunks: list[dict] = []
    haiku_errors: list[str] = []

    if mode == "validation":
        sample = _pick_validation_files(eligible, haiku_queue)
        logger.info("Validation sample (5 files): %s", [r["filename"] for r in sample])
        start = time.monotonic()
        results = await asyncio.gather(*(
            _run_haiku_extractor(per_file_meta[row["filename"]]["path"], sem, model,
                                 extract_docx_text(per_file_meta[row["filename"]]["path"]))
            for row in sample
        ))
        elapsed = time.monotonic() - start
        for row, (chunks, meta) in zip(sample, results):
            if "error" in meta:
                haiku_errors.append(f"{row['filename']}: {meta['error']}")
                continue
            total_haiku_input_tokens += meta.get("input_tokens", 0)
            total_haiku_output_tokens += meta.get("output_tokens", 0)
            for c in chunks:
                c["suggested_topic_slug"] = row.get("suggested_topic_slug", "")
                c["source_type"] = row.get("source_type", "")
                c["verdict"] = row.get("verdict", "")
            haiku_chunks.extend(chunks)
        _write_chunks_csv(VALIDATION_CSV, haiku_chunks)
        cost = (
            total_haiku_input_tokens * HAIKU_INPUT_RATE / 1_000_000
            + total_haiku_output_tokens * HAIKU_OUTPUT_RATE / 1_000_000
        )
        per_file_yield = {row["filename"]: 0 for row in sample}
        for c in haiku_chunks:
            per_file_yield[c["source_file"]] = per_file_yield.get(c["source_file"], 0) + 1
        print()
        print("=" * 60)
        print(f"Phase C VALIDATION pass complete in {elapsed:.1f}s")
        print(f"Output: {VALIDATION_CSV}")
        print(f"Files sampled: {len(sample)}")
        print(f"Chunks emitted: {len(haiku_chunks)}")
        print("Per-file yield:")
        for fn, yield_ in per_file_yield.items():
            print(f"  {fn:60s} {yield_:4d}")
        if haiku_errors:
            print("Errors:")
            for err in haiku_errors:
                print(f"  {err}")
        print(f"Cost (validation slice): ${cost:.4f}")
        print(f"Pending after-approval queue: {len(haiku_queue) - len(sample)} files")
        print("=" * 60)
        print()
        print("MANDATORY PAUSE — surface validation CSV to Chadi for sign-off")
        print(f"Inspect: {VALIDATION_CSV}")
        print(
            f"To approve and unlock the rest of the queue, create the marker file:"
        )
        print(f"  touch {VALIDATION_APPROVAL_FILE}")
        return 0

    if mode == "post-validation":
        if not VALIDATION_APPROVAL_FILE.exists():
            logger.error("Validation approval marker missing: %s", VALIDATION_APPROVAL_FILE)
            logger.error("Run --validation-mode first, get Chadi sign-off, then touch the file")
            return 1
        already_run_filenames: set[str] = set()
        if VALIDATION_CSV.exists():
            with VALIDATION_CSV.open("r", encoding="utf-8", newline="") as fh:
                already_run_filenames = {row["source_file"] for row in csv.DictReader(fh)}
        post_queue = [r for r in haiku_queue if r["filename"] not in already_run_filenames]
        logger.info("Post-validation Haiku run: %d files (skipping %d already in validation CSV)",
                    len(post_queue), len(already_run_filenames))
        start = time.monotonic()
        results = await asyncio.gather(*(
            _run_haiku_extractor(per_file_meta[row["filename"]]["path"], sem, model,
                                 extract_docx_text(per_file_meta[row["filename"]]["path"]))
            for row in post_queue
        ))
        elapsed = time.monotonic() - start
        for row, (chunks, meta) in zip(post_queue, results):
            if "error" in meta:
                haiku_errors.append(f"{row['filename']}: {meta['error']}")
                continue
            total_haiku_input_tokens += meta.get("input_tokens", 0)
            total_haiku_output_tokens += meta.get("output_tokens", 0)
            for c in chunks:
                c["suggested_topic_slug"] = row.get("suggested_topic_slug", "")
                c["source_type"] = row.get("source_type", "")
                c["verdict"] = row.get("verdict", "")
            haiku_chunks.extend(chunks)
        # Also include the validation-CSV chunks (re-read from disk so we
        # don't double-call Haiku on the validation set).
        if VALIDATION_CSV.exists():
            with VALIDATION_CSV.open("r", encoding="utf-8", newline="") as fh:
                haiku_chunks.extend(list(csv.DictReader(fh)))
        all_chunks.extend(haiku_chunks)
        _write_chunks_csv(EXTRACTION_CSV, all_chunks)
        cost = (
            total_haiku_input_tokens * HAIKU_INPUT_RATE / 1_000_000
            + total_haiku_output_tokens * HAIKU_OUTPUT_RATE / 1_000_000
        )
        print()
        print("=" * 60)
        print(f"Phase C POST-VALIDATION pass complete in {elapsed:.1f}s")
        print(f"Output: {EXTRACTION_CSV}")
        print(f"Total chunks (table+regex+haiku, pre-dedup): {len(all_chunks)}")
        print(f"  - table+regex: {len(all_chunks) - len(haiku_chunks)}")
        print(f"  - haiku: {len(haiku_chunks)}")
        print(f"Haiku errors: {len(haiku_errors)}")
        if haiku_errors:
            for err in haiku_errors[:20]:
                print(f"  {err}")
        print(f"Haiku cost (post-validation): ${cost:.4f}")
        print(f"Phase C ceiling: ${PHASE_C_COST_CEILING:.2f}")
        if cost > PHASE_C_COST_CEILING:
            logger.error("Phase C cost ceiling exceeded")
            return 2
        return 0

    logger.error("Unknown mode: %s", mode)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=("validation", "post-validation", "table-regex-only"),
        required=True,
    )
    args = parser.parse_args()
    return asyncio.run(main_async(args.mode))


if __name__ == "__main__":
    sys.exit(main())
