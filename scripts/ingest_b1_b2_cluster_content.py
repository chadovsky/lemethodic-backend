"""P-211 — ingest cluster authoring content into existing B1->B2 cluster rows.

Source: docs/clusters/B1.{1,2,3}-clusters-*.md (vendored from
lemethodic-frontend/curriculum/clusters/, see docs/clusters/ headers).

For each of the 13 authored clusters (B1.1.C1 through B1.3.C13):
    cluster.lesson_markdown     <- prose between cluster header and "## Exercises"
    cluster.practice_prompt     <- {tache_application, prompt_fr, instruction_fr,
                                    duration_seconds}
    cluster.tache_application   <- parsed from practice prompt header (overrides
                                    seed default; single source of truth = the
                                    authored content)
    cluster.detection_rubric    <- DetectionRubric prose-faithful shape per the
                                    relaxed schema (P-211 commit 11a175d)

For the 9 placeholder clusters (B1.4.C14..C18, B1.5.C19..C22):
    cluster.lesson_markdown     <- "Content authoring in progress -- ..."
    cluster.practice_prompt     <- {}
    cluster.detection_rubric    <- {}
    cluster.tache_application   <- left at seed default (tache_3)

Modes:
    --dry-run   parse + validate, no DB writes (severity inference printed)
    --force     overwrite even if the cluster already has lesson_markdown set
    (no flag)   normal run; aborts if any cluster already populated unless --force

Usage:
    python -m scripts.ingest_b1_b2_cluster_content --dry-run
    python -m scripts.ingest_b1_b2_cluster_content              # local apply
    DATABASE_URL=... python -m scripts.ingest_b1_b2_cluster_content   # prod apply

The script connects to DATABASE_URL to look up the b1_to_b2 path's
level_start, which is propagated as ceiling_level on every marker (so
the same script works for future paths -- B2->C1, etc. -- without edits).
"""
from __future__ import annotations

import argparse
import dataclasses
import re
import sys
from pathlib import Path as FsPath
from typing import Optional

from app.database import SessionLocal
from app.models.models import Cluster, Path
from app.schemas.curriculum import DetectionRubric, Marker, StatusLogic


# ── Configuration ─────────────────────────────────────────────────────

DEFAULT_SOURCE_DIR = FsPath(__file__).resolve().parent.parent / "docs" / "clusters"

PATH_SLUG = "b1_to_b2"

# Maps the cluster doc's "CLUSTER N" index to the canonical 4-segment
# slug (also used as the marker_id prefix). Source: scripts/seed_b1_b2_path.py.
CLUSTER_DOC_TO_SLUG: dict[int, str] = {
    1:  "B1.1.C1",
    2:  "B1.1.C2",
    3:  "B1.1.C3",
    4:  "B1.1.C4",
    5:  "B1.2.C5",
    6:  "B1.2.C6",
    7:  "B1.2.C7",
    8:  "B1.2.C8",
    9:  "B1.2.C9",
    10: "B1.3.C10",
    11: "B1.3.C11",
    12: "B1.3.C12",
    13: "B1.3.C13",
}

PLACEHOLDER_CLUSTERS = [
    "B1.4.C14", "B1.4.C15", "B1.4.C16", "B1.4.C17", "B1.4.C18",
    "B1.5.C19", "B1.5.C20", "B1.5.C21", "B1.5.C22",
]

PLACEHOLDER_LESSON = (
    "Content authoring in progress — "
    "see LEMETHODIC-CURRICULUM v0.2 §4.2 for outline"
)

# Maps cluster doc index -> source file path.
DOC_INDEX_TO_FILENAME = {
    1: "B1.1-clusters-1-and-2.md",   2: "B1.1-clusters-1-and-2.md",
    3: "B1.1-clusters-3-and-4.md",   4: "B1.1-clusters-3-and-4.md",
    5: "B1.2-clusters-5-to-9.md",    6: "B1.2-clusters-5-to-9.md",
    7: "B1.2-clusters-5-to-9.md",    8: "B1.2-clusters-5-to-9.md",
    9: "B1.2-clusters-5-to-9.md",
    10: "B1.3-clusters-10-to-13.md", 11: "B1.3-clusters-10-to-13.md",
    12: "B1.3-clusters-10-to-13.md", 13: "B1.3-clusters-10-to-13.md",
}


# ── Parsed cluster content (intermediate) ─────────────────────────────


@dataclasses.dataclass
class ParsedCluster:
    doc_index: int
    slug: str
    title: str
    lesson_body: str
    practice_prompt: dict
    rubric_markers: list[Marker]
    rubric_status_logic: StatusLogic
    rubric_quantitative_signals: list[dict]
    # Audit data for the dry-run output
    severity_evidence: dict[str, str]   # marker_id -> matched substring (or "" if medium)
    marker_id_rewrites: list[tuple[str, str]]   # (legacy, canonical)


# ── Section extraction ────────────────────────────────────────────────


CLUSTER_HEADER_RE = re.compile(r"^# CLUSTER (\d+)\s*[—\-]\s*(.+?)\s*$", re.MULTILINE)


def split_cluster_sections(file_text: str) -> list[tuple[int, str, str]]:
    """Yield (doc_index, title, section_text) per cluster in the file.

    A section_text starts at the cluster header and runs to the next
    `# CLUSTER N` heading or end of file.
    """
    matches = list(CLUSTER_HEADER_RE.finditer(file_text))
    out: list[tuple[int, str, str]] = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(file_text)
        out.append((int(m.group(1)), m.group(2).strip(), file_text[start:end]))
    return out


def extract_lesson_body(section: str) -> str:
    """Everything from the cluster header through the line before `## Exercises`."""
    m = re.search(r"^## Exercises\b", section, re.MULTILINE)
    if not m:
        raise ValueError("missing '## Exercises' boundary")
    return section[: m.start()].rstrip() + "\n"


PROMPT_HEADER_RE = re.compile(
    r"^## Practice Prompt\s*\((.+?)\)\s*$", re.MULTILINE
)
RUBRIC_HEADER_RE = re.compile(r"^## Detection Rubric\b", re.MULTILINE)
TACHE_RE = re.compile(r"Tâche\s+(\d)", re.IGNORECASE)
DURATION_MIN_RE = re.compile(r"(\d+)\s*min\s*recording", re.IGNORECASE)
BLOCKQUOTE_LINE_RE = re.compile(r"^>\s?(.*)$")


def extract_practice_prompt(section: str) -> dict:
    """Returns {tache_application, prompt_fr, instruction_fr, duration_seconds}.

    Header form: `## Practice Prompt (Tâche 3 — Monologue argumentatif, 5 min recording)`
    Body form:
        > **« <prompt> »**
        >
        > <instruction>

        [optional commentary -- not captured]
    """
    pm = PROMPT_HEADER_RE.search(section)
    if not pm:
        raise ValueError("no '## Practice Prompt (...)' header found")
    header_inner = pm.group(1)

    tache_match = TACHE_RE.search(header_inner)
    if not tache_match:
        raise ValueError(f"could not parse Tâche number from header: {header_inner!r}")
    # Cluster 4 / 12 use "Tâche X / Tâche Y" or "Tâche X + Tâche Y" hybrid
    # forms -- we pick the FIRST listed Tâche as the canonical
    # tache_application. Hybrid intent is preserved in the lesson body.
    tache_num = tache_match.group(1)

    duration_match = DURATION_MIN_RE.search(header_inner)
    duration_seconds = int(duration_match.group(1)) * 60 if duration_match else None

    # Body: everything between the prompt header and the next "## " section.
    body_start = pm.end()
    next_section = re.search(r"^## ", section[body_start:], re.MULTILINE)
    body = section[body_start : body_start + next_section.start()] if next_section else section[body_start:]

    quote_lines: list[str] = []
    for line in body.splitlines():
        bm = BLOCKQUOTE_LINE_RE.match(line.strip())
        if bm is not None:
            quote_lines.append(bm.group(1).strip())
    if not quote_lines:
        raise ValueError("no blockquote content found under '## Practice Prompt'")

    # First non-empty quote line(s) -> prompt_fr (joined if multi-line wrapped).
    # Last non-empty quote line -> instruction_fr.
    non_empty = [q for q in quote_lines if q]
    if len(non_empty) < 2:
        # Some clusters have prompt + instruction collapsed to one line.
        prompt_fr = non_empty[0] if non_empty else ""
        instruction_fr = ""
    else:
        instruction_fr = non_empty[-1]
        prompt_lines = non_empty[:-1]
        prompt_fr = " ".join(prompt_lines)
    # Strip enclosing « » and surrounding **, since they're rendering chrome.
    prompt_fr = prompt_fr.strip("* ").strip()
    if prompt_fr.startswith("«"):
        prompt_fr = prompt_fr.lstrip("«").rstrip("»").strip()
    elif prompt_fr.startswith("« "):
        prompt_fr = prompt_fr[2:]
    prompt_fr = prompt_fr.strip("* ").strip()

    return {
        "tache_application": f"tache_{tache_num}",
        "prompt_fr": prompt_fr,
        "instruction_fr": instruction_fr,
        "duration_seconds": duration_seconds,
    }


# ── Detection rubric parsing ──────────────────────────────────────────

QUANT_HEADER_RE = re.compile(r"^### Quantitative signals\b", re.MULTILINE)
QUAL_HEADER_RE = re.compile(
    r"^### Qualitative markers\b.*$", re.MULTILINE | re.IGNORECASE
)
STATUS_HEADER_RE = re.compile(r"^### Cluster status assignment\b", re.MULTILINE)
NEXT_TOPLEVEL_RE = re.compile(r"^## ", re.MULTILINE)

MARKER_LINE_RE = re.compile(
    r"^- \*\*Marker\s+([A-Za-z0-9.]+)\s*[—\-]\s*\"([^\"]+)\":\*\*\s*(.*?)$"
)


def _slice(text: str, start: int, end: Optional[int]) -> str:
    return text[start:end] if end is not None else text[start:]


def extract_rubric_sections(section: str) -> tuple[str, str, str]:
    """Return (quantitative_text, qualitative_text, status_text). Each is
    raw markdown for its subsection. Empty string if the subsection is
    missing (some early clusters omit certain subsections)."""
    rm = RUBRIC_HEADER_RE.search(section)
    if not rm:
        raise ValueError("no '## Detection Rubric' section")
    rubric_start = rm.end()
    nextm = NEXT_TOPLEVEL_RE.search(section, rubric_start)
    rubric_end = nextm.start() if nextm else len(section)
    rubric = section[rubric_start:rubric_end]

    qm = QUANT_HEADER_RE.search(rubric)
    qlm = QUAL_HEADER_RE.search(rubric)
    sm = STATUS_HEADER_RE.search(rubric)

    quant = ""
    if qm:
        quant_start = qm.end()
        quant_end = (qlm.start() if qlm else (sm.start() if sm else len(rubric)))
        quant = rubric[quant_start:quant_end]

    qual = ""
    if qlm:
        qual_start = qlm.end()
        qual_end = sm.start() if sm else len(rubric)
        qual = rubric[qual_start:qual_end]

    status = ""
    if sm:
        status = rubric[sm.end():]

    return quant.strip(), qual.strip(), status.strip()


def parse_quantitative_table(quant_text: str) -> list[dict]:
    """Parse `| Signal | Computation | Threshold |` markdown table.

    Returns one dict per row with name/computation/threshold keys.
    """
    rows = []
    for line in quant_text.splitlines():
        line = line.strip()
        if not line.startswith("|") or not line.endswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 3:
            continue
        # Skip header row and separator row
        if cells[0].lower() in ("signal", "---", ":---", "---:"):
            continue
        if all(set(c) <= set(":-") for c in cells):
            continue
        # Strip surrounding backticks from computation cell for cleaner JSON.
        computation = cells[1].strip("` ")
        rows.append({
            "name": cells[0],
            "computation": computation,
            "threshold": cells[2],
        })
    return rows


def parse_status_table(status_text: str) -> dict[str, str]:
    """Parse `| Status | Conditions |` table. Returns dict of
    absorbed/partial/needs_revisit/not_started -> condition prose."""
    out: dict[str, str] = {}
    for line in status_text.splitlines():
        line = line.strip()
        if not line.startswith("|") or not line.endswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 2:
            continue
        if cells[0].lower() in ("status", "---", ":---", "---:"):
            continue
        if all(set(c) <= set(":-") for c in cells):
            continue
        # cells[0] is "**Absorbed**" / "**Needs revisit**" / etc.
        key_raw = cells[0].strip("* ").lower()
        key_norm = key_raw.replace(" ", "_")
        if key_norm in {"absorbed", "partial", "needs_revisit", "not_started"}:
            out[key_norm] = cells[1]
    return out


def parse_qualitative_markers(qual_text: str) -> list[tuple[str, str, str]]:
    """Returns list of (marker_id_as_authored, name, prose)."""
    out: list[tuple[str, str, str]] = []
    for line in qual_text.splitlines():
        m = MARKER_LINE_RE.match(line.strip())
        if m:
            out.append((m.group(1), m.group(2), m.group(3).strip()))
    return out


# ── Marker ID normalization (4-segment canonical) ─────────────────────

# Patterns that may appear in authored docs:
#   B1.1.a              3-segment, where second number is global cluster index
#   B1.1.C1.a           4-segment, canonical
#   C5.a                2-segment shorthand (within-cluster references)
# LEGACY_2SEG_RE uses a negative lookbehind so it doesn't match the C1.a
# tail of an already-canonical 4-segment marker (which is preceded by
# `\d\.` -- e.g., the "1." before "C1" in "B1.1.C1.a").
LEGACY_3SEG_RE = re.compile(r"\bB[12]\.\d+\.([a-z])\b")
LEGACY_2SEG_RE = re.compile(r"(?<!\d\.)\bC\d+\.([a-z])\b")
CANON_4SEG_RE = re.compile(r"\bB[12]\.\d+\.C\d+\.[a-z]\b")


def canonical_marker_id(letter: str, cluster_slug: str) -> str:
    return f"{cluster_slug}.{letter}"


def normalize_marker_id(authored: str, cluster_slug: str) -> tuple[str, bool]:
    """Returns (canonical_id, was_rewritten)."""
    if CANON_4SEG_RE.fullmatch(authored):
        return authored, False
    # Trailing letter is reliable across all formats.
    letter = authored.split(".")[-1]
    canonical = canonical_marker_id(letter, cluster_slug)
    return canonical, True


def rewrite_marker_refs_in_text(text: str, cluster_slug: str) -> str:
    """Replace legacy marker references (3-segment or 2-segment shorthand)
    with the 4-segment canonical form. Used for status_logic prose,
    where marker IDs appear inline."""
    def _repl_3seg(m: re.Match) -> str:
        return canonical_marker_id(m.group(1), cluster_slug)

    def _repl_2seg(m: re.Match) -> str:
        return canonical_marker_id(m.group(1), cluster_slug)

    out = LEGACY_3SEG_RE.sub(_repl_3seg, text)
    out = LEGACY_2SEG_RE.sub(_repl_2seg, out)
    return out


# ── Severity inference ────────────────────────────────────────────────


def infer_severity(
    marker_id_canonical: str, status_logic: dict[str, str]
) -> tuple[str, str]:
    """Returns (severity, evidence_substring).

    Heuristic:
      "high"   = marker_id is explicitly named in status_logic.needs_revisit
                 (because being named there means it's a single-fire OR
                 small-pair-fire trigger for needs_revisit).
      "medium" = otherwise (only triggers needs_revisit as part of the
                 generic "2+ markers firing" clause).

    Returns the matched substring as evidence for dry-run audit.
    """
    nr = status_logic.get("needs_revisit", "")
    if not nr or marker_id_canonical not in nr:
        return "medium", ""
    # Find a ~80-char window around the marker mention, for the audit log.
    idx = nr.index(marker_id_canonical)
    start = max(0, idx - 30)
    end = min(len(nr), idx + len(marker_id_canonical) + 50)
    return "high", nr[start:end].strip()


# ── Main parse flow ───────────────────────────────────────────────────


def parse_cluster_section(
    doc_index: int, title: str, section: str
) -> ParsedCluster:
    slug = CLUSTER_DOC_TO_SLUG[doc_index]

    lesson_body = extract_lesson_body(section)
    practice_prompt = extract_practice_prompt(section)
    quant_text, qual_text, status_text = extract_rubric_sections(section)

    quantitative_signals = parse_quantitative_table(quant_text)
    status_raw = parse_status_table(status_text)

    # Normalize marker references inside the status_logic prose first,
    # so severity inference reads canonical IDs.
    status_normalized = {
        k: rewrite_marker_refs_in_text(v, slug) for k, v in status_raw.items()
    }
    # StatusLogic Pydantic schema only knows absorbed/partial/needs_revisit.
    status_logic = StatusLogic(
        absorbed=status_normalized.get("absorbed", ""),
        partial=status_normalized.get("partial", ""),
        needs_revisit=status_normalized.get("needs_revisit", ""),
    )

    # Build markers with normalized IDs and inferred severity.
    parsed_markers = parse_qualitative_markers(qual_text)
    markers: list[Marker] = []
    severity_evidence: dict[str, str] = {}
    rewrites: list[tuple[str, str]] = []
    for authored_id, name, prose in parsed_markers:
        canonical, rewrote = normalize_marker_id(authored_id, slug)
        if rewrote:
            rewrites.append((authored_id, canonical))
        severity, evidence = infer_severity(canonical, status_normalized)
        severity_evidence[canonical] = evidence
        markers.append(Marker(
            marker_id=canonical,
            name=name,
            firing_condition=None,
            firing_condition_prose=prose,
            severity=severity,
            ceiling_level="B1",   # patched in build_payload() once we know level_start
        ))

    return ParsedCluster(
        doc_index=doc_index,
        slug=slug,
        title=title,
        lesson_body=lesson_body,
        practice_prompt=practice_prompt,
        rubric_markers=markers,
        rubric_status_logic=status_logic,
        rubric_quantitative_signals=quantitative_signals,
        severity_evidence=severity_evidence,
        marker_id_rewrites=rewrites,
    )


def parse_all(source_dir: FsPath) -> list[ParsedCluster]:
    """Parse every authored cluster (1..13). Aborts on the first error."""
    files_seen: dict[str, str] = {}
    for filename in set(DOC_INDEX_TO_FILENAME.values()):
        path = source_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"missing cluster doc: {path}")
        files_seen[filename] = path.read_text(encoding="utf-8")

    parsed_by_index: dict[int, ParsedCluster] = {}
    for doc_index, filename in DOC_INDEX_TO_FILENAME.items():
        sections = split_cluster_sections(files_seen[filename])
        for idx, title, section in sections:
            if idx == doc_index:
                try:
                    parsed_by_index[doc_index] = parse_cluster_section(idx, title, section)
                except Exception as e:
                    raise ValueError(
                        f"failed to parse Cluster {doc_index} ({filename}): {e}"
                    ) from e
                break
        if doc_index not in parsed_by_index:
            raise ValueError(f"Cluster {doc_index} not found in {filename}")
    return [parsed_by_index[i] for i in sorted(parsed_by_index)]


# ── Output / DB ───────────────────────────────────────────────────────


def build_rubric_payload(p: ParsedCluster, ceiling_level: str) -> dict:
    """Convert parsed cluster -> JSON-able rubric payload, validated."""
    markers_with_level = [
        m.model_copy(update={"ceiling_level": ceiling_level})
        for m in p.rubric_markers
    ]
    rubric = DetectionRubric(
        markers=markers_with_level,
        status_logic=p.rubric_status_logic,
        quantitative_signals=p.rubric_quantitative_signals or None,
    )
    # mode="json" so JSONB-compatible types (no Decimals etc.) come out.
    return rubric.model_dump(mode="json", exclude_none=True)


def print_dry_run(parsed: list[ParsedCluster], ceiling_level: str) -> None:
    print(f"\n=== DRY RUN — ceiling_level={ceiling_level} (from Path.level_start) ===\n")
    for p in parsed:
        rewrite_count = len(p.marker_id_rewrites)
        rewrite_note = (
            f" (rewrote {rewrite_count} marker_id{'s' if rewrite_count != 1 else ''})"
            if rewrite_count else ""
        )
        print(
            f"[{p.slug}] {p.title} "
            f"(tache_{p.practice_prompt['tache_application'].split('_')[1]}, "
            f"{len(p.rubric_markers)} markers){rewrite_note}"
        )
        print(
            f"  lesson_body: {len(p.lesson_body)} chars / "
            f"{p.lesson_body.count(chr(10))} lines"
        )
        print(
            f"  practice_prompt: tache={p.practice_prompt['tache_application']}, "
            f"duration={p.practice_prompt['duration_seconds']}s, "
            f"prompt_fr={len(p.practice_prompt['prompt_fr'])} chars"
        )
        print(f"  quantitative_signals: {len(p.rubric_quantitative_signals)} rows")
        print(f"  markers (severity inference):")
        for m in p.rubric_markers:
            badge = "HIGH  " if m.severity == "high" else "medium"
            evidence = p.severity_evidence.get(m.marker_id, "")
            note = f' (matched: "...{evidence}...")' if evidence else " (not in needs_revisit)"
            print(f"    {m.marker_id:<14} [{badge}] {m.name}{note}")


def print_summary(
    parsed: list[ParsedCluster], placeholder_count: int, dry_run: bool
) -> None:
    total_markers = sum(len(p.rubric_markers) for p in parsed)
    high = sum(1 for p in parsed for m in p.rubric_markers if m.severity == "high")
    medium = total_markers - high
    rewrite_total = sum(len(p.marker_id_rewrites) for p in parsed)
    rewrite_clusters = [p.slug for p in parsed if p.marker_id_rewrites]
    tache_dist: dict[str, int] = {}
    for p in parsed:
        tache_dist[p.practice_prompt["tache_application"]] = (
            tache_dist.get(p.practice_prompt["tache_application"], 0) + 1
        )

    print()
    print("=" * 72)
    print("INGEST SUMMARY")
    print("=" * 72)
    print(f"Authored clusters parsed: {len(parsed)}/13")
    print(f"  Total markers: {total_markers} ({high} high / {medium} medium)")
    print(
        "  Tâche distribution: "
        + ", ".join(f"{k} x{v}" for k, v in sorted(tache_dist.items()))
    )
    print(f"Placeholder clusters: {placeholder_count}/9")
    if rewrite_total:
        print()
        print(
            f"⚠️  MARKER_ID REWRITE SUMMARY: {rewrite_total} markers in "
            f"{len(rewrite_clusters)} cluster(s) rewritten from legacy format "
            "to canonical 4-segment."
        )
        print("    SOURCE DOCS SHOULD BE NORMALIZED.")
        print(f"    Affected clusters: {', '.join(rewrite_clusters)}.")
    print()
    if dry_run:
        print(">>> DRY RUN — no DB changes applied <<<")
    else:
        print(">>> Applied to DB <<<")


def apply_to_db(
    parsed: list[ParsedCluster], ceiling_level: str, force: bool
) -> int:
    """Apply parsed content + placeholder updates inside ONE transaction."""
    db = SessionLocal()
    try:
        # Pre-flight: every cluster slug must exist (P-210 seed must have run).
        all_target_slugs = [p.slug for p in parsed] + PLACEHOLDER_CLUSTERS
        existing = {
            c.slug: c
            for c in db.query(Cluster).filter(Cluster.slug.in_(all_target_slugs)).all()
        }
        missing = [s for s in all_target_slugs if s not in existing]
        if missing:
            raise RuntimeError(
                f"missing cluster rows in DB (run scripts.seed_b1_b2_path first): "
                f"{missing}"
            )

        # Idempotency: refuse to overwrite already-populated lesson_markdown
        # unless --force.
        if not force:
            already_populated = [
                s for s in all_target_slugs
                if existing[s].lesson_markdown not in ("", None)
            ]
            if already_populated:
                raise RuntimeError(
                    "some clusters already have content "
                    f"({len(already_populated)} of {len(all_target_slugs)}). "
                    "Re-run with --force to overwrite. Affected slugs: "
                    f"{', '.join(already_populated[:5])}"
                    f"{'...' if len(already_populated) > 5 else ''}"
                )

        # Apply authored cluster updates.
        for p in parsed:
            cluster = existing[p.slug]
            cluster.lesson_markdown = p.lesson_body
            cluster.practice_prompt = p.practice_prompt
            cluster.tache_application = p.practice_prompt["tache_application"]
            cluster.detection_rubric = build_rubric_payload(p, ceiling_level)

        # Apply placeholder cluster updates.
        for slug in PLACEHOLDER_CLUSTERS:
            cluster = existing[slug]
            cluster.lesson_markdown = PLACEHOLDER_LESSON
            cluster.practice_prompt = {}
            cluster.detection_rubric = {}
            # Leave cluster.tache_application at the seed default (tache_3).

        db.commit()
        return len(all_target_slugs)
    finally:
        db.close()


def lookup_ceiling_level() -> str:
    db = SessionLocal()
    try:
        path = db.query(Path).filter_by(slug=PATH_SLUG).first()
        if path is None:
            raise RuntimeError(
                f"path slug '{PATH_SLUG}' not found in DB; "
                "run scripts.seed_b1_b2_path first"
            )
        return path.level_start
    finally:
        db.close()


def main() -> int:
    # Force UTF-8 stdout so the warning glyph + accented French titles
    # render on Windows consoles (default cp1252 chokes on them).
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument(
        "--source-dir",
        type=FsPath,
        default=DEFAULT_SOURCE_DIR,
        help=f"directory containing the 4 cluster docs (default: {DEFAULT_SOURCE_DIR})",
    )
    ap.add_argument("--dry-run", action="store_true",
                    help="parse + validate, no DB writes")
    ap.add_argument("--force", action="store_true",
                    help="overwrite already-populated clusters")
    args = ap.parse_args()

    print(f"[ingest_p211] source dir: {args.source_dir}")
    print(f"[ingest_p211] mode: {'DRY-RUN' if args.dry_run else 'APPLY'}"
          f"{' (force overwrite)' if args.force else ''}")

    parsed = parse_all(args.source_dir)
    print(f"[ingest_p211] parsed {len(parsed)}/13 authored clusters")

    ceiling_level = lookup_ceiling_level()
    print(f"[ingest_p211] ceiling_level (from Path.{PATH_SLUG}.level_start) = {ceiling_level}")

    # Validate every cluster's rubric payload (catches schema breaks before DB writes).
    for p in parsed:
        try:
            build_rubric_payload(p, ceiling_level)
        except Exception as e:
            print(f"[ingest_p211] FAIL: {p.slug} rubric validation: {e}")
            return 1

    print_dry_run(parsed, ceiling_level)
    print_summary(parsed, len(PLACEHOLDER_CLUSTERS), dry_run=args.dry_run)

    if args.dry_run:
        return 0

    n = apply_to_db(parsed, ceiling_level, force=args.force)
    print(f"[ingest_p211] applied to {n} clusters in 1 transaction")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
