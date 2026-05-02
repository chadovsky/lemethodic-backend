"""One-shot regenerator for BACKLOG.md.

Reads the existing BACKLOG, classifies each ticket against the
2026-05-02 triage decisions, regroups bodies under tag sections, and
prepends an "Active Queue" summary.

Designed to be re-runnable: tag classifications and section ordering
live as Python constants below. Re-running with different sets
re-produces the file from the existing ticket bodies.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "BACKLOG.md"


# ── Triage classifications (2026-05-02) ──────────────────────────

ACTIVE_LC = [
    # In stated priority order — Active Queue summary preserves this order.
    # Reordered 2026-05-02: engineering (in dependency order) → pre-launch
    # product → pre-launch business → pre-launch marketing. P-260.5 sits
    # above marketing as a hard Sprint-product blocker.
    # 2026-05-02 reconciliation: P-222, P-230, P-234 migrated from FE BACKLOG.

    # Engineering (in dependency order):
    # P-220 fully shipped 2026-05-02 — moved to SHIPPED section.
    # P-200 fully shipped 2026-05-02 (3-commit set) — moved to SHIPPED.
    "P-201",                  # diagnostic engine — level assignment + confidence
    "P-221",                  # diagnostic flow integration
    "P-104",                  # background-tab timer drift fix
    "P-240",                  # today's recommended action
    "F-079",                  # custom domain wiring
    "P-222",                  # waitlist UX for A2/B2+ paths (FE-migrated)
    "P-230",                  # overall progress dashboard rebuild (FE-migrated)
    "P-234",                  # cluster detail view (FE-migrated)

    # Pre-launch product:
    "P-105", "P-106",         # 7-day trial + Stripe integration
    "P-260.5",                # Sprint product blocker (3 TCF mocks)

    # Pre-launch business:
    "B-100", "B-102",         # Stripe account + Privacy/ToS

    # Pre-launch marketing:
    "M-100", "M-101",         # Preply outreach + landing copy
    "M-103", "M-104",         # YouTube anchor + Reddit
]
POST_LAUNCH_P1 = [
    "P-107", "P-108", "P-110",
    "P-211b",
    "P-213",                  # FE-migrated: dialogue box template authoring
    "P-220.z",
    "P-231", "P-232", "P-233", # FE-migrated: speaking / per-tâche / curriculum view dashboards
    "P-235", "P-236", "P-237", # FE-migrated: ceiling marker map / mistake repo / time-adaptive UI lean
    "P-241", "P-250", "P-251",
    "B-101", "B-104", "B-105", "B-106",
    "C-100",                  # FE-migrated: prod test-user cleanup
    "F-109",                  # FE-migrated: full-name persistence bug
    "M-101.z",                # FE-migrated: landing page hero asset
    "M-102", "M-107", "M-108",
]
POST_LAUNCH_P2 = [
    # P-103.2 promoted from Kill (clear trigger, design contract preserved).
    # M-106 promoted from Marketing pick-1 (long-tail SEO, deferred with trigger).
    # 2026-05-02 reconciliation: P-104.x, EX-100 migrated from FE BACKLOG.
    "P-102", "P-103.1", "P-103.2", "P-104.x", "P-109",
    "P-210.1", "P-211a", "P-211c",
    "P-220.x", "P-220.y",
    "EX-100",
    "M-106",
]
DEFERRED = [
    # 2026-05-02 reconciliation: P-261, P-263, P-264, P-265, P-268, P-269
    # migrated from FE BACKLOG.
    "P-260", "P-261", "P-262", "P-263", "P-264", "P-265", "P-266",
    "P-268", "P-269",
    "P-300", "P-301", "P-302", "P-303",
    "F-077.x", "F-078.x", "F-111",
    "B-103",
]
# 2026-05-02 follow-up triage: P-212 superseded by P-210 + P-211.
# P-220 fully shipped (BE + FE + production verification) 2026-05-02.
# P-200 fully shipped (3-commit set, BE only — no FE consumer yet) 2026-05-02.
SHIPPED = [
    "F-110", "F-110.1", "F-110.2", "P-103",
    "P-200", "P-202", "P-203", "P-204",
    "P-210", "P-211", "P-212", "P-220",
]
# Decided not to pursue. Keep entry to preserve history.
CLOSED = ["M-105"]


# Tag value injected as **Tag:** line per ticket body.
TAG_TEXT = {
    "active_lc":  "Active — Launch Critical (60-day target)",
    "p1":         "Post-launch P1 (2-4 weeks after launch)",
    "p2":         "Post-launch P2 — signal-driven (defer until real signal)",
    "deferred":   "Phase 2 / deferred indefinitely",
    "shipped":    None,   # no tag for shipped — status reflects history
    "closed":     "Closed — decided not to pursue",
}

# Section ordering in the regenerated file.
SECTIONS = [
    ("active_lc",  f"Active — Launch Critical ({len(ACTIVE_LC)} tickets, 60-day target)",  ACTIVE_LC),
    ("p1",         "Post-launch P1 (2-4 weeks after launch)",                              POST_LAUNCH_P1),
    ("p2",         "Post-launch P2 — signal-driven",                                       POST_LAUNCH_P2),
    ("deferred",   "Phase 2 / deferred indefinitely",                                      DEFERRED),
    ("closed",     "Closed",                                                               CLOSED),
    ("shipped",    "Shipped",                                                              SHIPPED),
]


# Hardcoded preamble. Re-render it on every regen — DO NOT extract from
# the existing file. Earlier (pre-fix) the regen extracted
# everything-before-first-ticket as preamble, which captured stale
# Active Queue summaries from prior runs and stacked them. Hardcoding
# keeps regen idempotent.
PREAMBLE = """# BACKLOG.md

**Last updated:** 2026-05-02 (re-baseline pass + 5-decision follow-up).
**Phase 1 Architecture Rework** — see `lemethodic-frontend/LEMETHODIC-CURRICULUM.md` v0.2.

Active and deferred work tracking. Tickets are organized by **Tag** —
the section a ticket lives in matches its `**Tag:**` line. Section
ordering: Active → P1 → P2 → Deferred → Closed → Shipped. The Active
Queue summary at the top of this file reproduces only the launch-critical
slate in priority order; bodies live below.

Re-runnable via `scripts/regen_backlog.py` — change classification
constants there and regenerate.

---
"""


# ── Parsing ──────────────────────────────────────────────────────

HEADER_RE = re.compile(
    r"^## ([A-Z][A-Z0-9-]*[0-9](?:\.[a-z0-9]+|[a-z]+)*)\s*[—-]\s*.+?\s*$",
    re.MULTILINE,
)


SECTION_HEADING_RE = re.compile(r"^# .+$", re.MULTILINE)


def parse_backlog(text: str) -> dict[str, str]:
    """Returns {ticket_id: body_block}.

    body_block includes the `## ID — Title` line through the line before
    the next ticket header. Strips any stray top-level `# Heading` lines
    that leaked into a body — those are section headings from prior
    regen runs that should not be preserved across regenerations.
    """
    matches = list(HEADER_RE.finditer(text))
    if not matches:
        return {}
    bodies: dict[str, str] = {}
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[m.start():end].rstrip()
        # Strip top-level section headings that leaked into this ticket
        # body (anything matching ^# at line start). Keeps regen idempotent.
        block = SECTION_HEADING_RE.sub("", block).strip()
        if not block.endswith("---"):
            block = block + "\n\n---"
        bodies[m.group(1)] = block + "\n\n"
    return bodies


# ── Tag injection ────────────────────────────────────────────────

STATUS_LINE_RE = re.compile(r"^\*\*Status:\*\*.*$", re.MULTILINE)
TAG_LINE_RE = re.compile(r"^\*\*Tag:\*\*.*\n", re.MULTILINE)


def inject_tag(body: str, tag_value: str | None) -> str:
    """Idempotent: strips any existing **Tag:** line, then inserts the
    new one (if any) right after the **Status:** line.

    new_tag_line carries no trailing newline; the existing body[m.end():]
    already begins with `\\n` (Status's line terminator), so a hardcoded
    trailing `\\n` in new_tag_line would double up on second-pass regen
    and break idempotency."""
    body = TAG_LINE_RE.sub("", body)
    if tag_value is None:
        return body
    new_tag_line = f"**Tag:** {tag_value}."
    m = STATUS_LINE_RE.search(body)
    if not m:
        # No Status line — append tag line right after the heading line.
        lines = body.split("\n", 1)
        rest = lines[1] if len(lines) > 1 else ""
        return lines[0] + "\n\n" + new_tag_line + "\n" + rest
    return body[:m.end()] + "\n" + new_tag_line + body[m.end():]


# ── Active Queue summary ─────────────────────────────────────────

TITLE_RE = re.compile(
    r"^## ([A-Z][A-Z0-9-]*[0-9](?:\.[a-z0-9]+|[a-z]+)*)\s*[—-]\s*(.+?)\s*$",
    re.MULTILINE,
)


def title_of(body: str) -> str:
    m = TITLE_RE.search(body)
    return m.group(2).strip() if m else "(unknown)"


def build_active_queue(bodies: dict[str, str]) -> str:
    out: list[str] = []
    out.append("## Active Queue — Launch Critical (60-day target)")
    out.append("")
    out.append("In stated priority order. Full ticket bodies live below in the "
               '"Active — Launch Critical" section.')
    out.append("")
    out.append("| # | Ticket | Title |")
    out.append("|---|---|---|")
    for i, tid in enumerate(ACTIVE_LC, start=1):
        title = title_of(bodies.get(tid, "")) if tid in bodies else "(missing)"
        out.append(f"| {i} | **{tid}** | {title} |")
    out.append("")
    out.append("---")
    out.append("")
    return "\n".join(out)


# ── Render ───────────────────────────────────────────────────────


def render(bodies: dict[str, str]) -> str:
    """Build the new file content. Preamble is hardcoded — see PREAMBLE."""
    chunks = [PREAMBLE.rstrip() + "\n\n", build_active_queue(bodies)]

    seen: set[str] = set()
    for key, heading, ids in SECTIONS:
        section_chunks = [f"# {heading}\n\n"]
        for tid in ids:
            if tid not in bodies:
                # P-220.z is the canonical case — referenced in triage but
                # not yet filed. Surface as a placeholder so the section
                # body stays honest about what's there.
                section_chunks.append(
                    f"## {tid} — (referenced in triage but not filed)\n\n"
                    f"**Status:** Not filed — scope TBD per 2026-05-02 triage.\n"
                    f"**Tag:** {TAG_TEXT[key]}.\n\n"
                    f"Placeholder — no ticket body. Resolve by either filing "
                    f"with real scope or removing from this list.\n\n---\n\n"
                )
                continue
            body = inject_tag(bodies[tid], TAG_TEXT[key])
            section_chunks.append(body)
            seen.add(tid)
        chunks.append("".join(section_chunks))

    leftover = [tid for tid in bodies if tid not in seen]
    if leftover:
        chunks.append("# Unclassified — leftovers\n\n")
        for tid in leftover:
            chunks.append(bodies[tid])

    return "".join(chunks)


def main() -> int:
    text = SRC.read_text(encoding="utf-8")
    bodies = parse_backlog(text)
    print(f"parsed {len(bodies)} tickets from BACKLOG.md")

    classified = sum(len(ids) for _, _, ids in SECTIONS)
    print(f"classifications cover {classified} ids "
          f"(some may not yet exist as bodies)")

    new_text = render(bodies)
    SRC.write_text(new_text, encoding="utf-8")
    print(f"wrote {len(new_text)} bytes to BACKLOG.md")

    # Sanity round-trip: re-parse and confirm every original ticket survives.
    bodies_after = parse_backlog(new_text)
    missing = set(bodies) - set(bodies_after)
    extra = set(bodies_after) - set(bodies)
    print(f"round-trip: {len(bodies_after)} tickets in regenerated file")
    print(f"  missing from rewrite: {sorted(missing)}")
    print(f"  added by rewrite:     {sorted(extra)}")

    # Idempotency proof: write twice, expect identical output.
    bodies_2 = parse_backlog(SRC.read_text(encoding="utf-8"))
    text_2 = render(bodies_2)
    if text_2 == new_text:
        print("idempotency: OK (second regen produced identical output)")
    else:
        print("idempotency: FAIL — second regen differs")
        return 1
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
