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
    # P-201 fully shipped 2026-05-02 (2-commit set) — moved to SHIPPED.
    # P-221 fully shipped 2026-05-02 (single commit c475bb7) — moved to SHIPPED.
    # P-104 fully shipped FE-side 2026-05-01 — moved to SHIPPED. BE-side
    # confirmed no-op (client-reported duration_seconds is metadata only;
    # no server reconciliation needed by product design).
    # P-240 fully shipped 2026-05-02 (single commit 6b8ee43, action layer
    # only) — moved to SHIPPED. Prose layer split as P-240b (Post-launch
    # P1, blocked on P-213 templates).
    # F-079 fully shipped 2026-05-03 (DNS + Vercel SSL + CORS via
    # FRONTEND_ORIGIN env) — moved to SHIPPED. No code commit; ops only.
    # P-222 fully shipped 2026-05-03 FE-side (commits 59fb2c6 + deff02b +
    # 820d788) — moved to SHIPPED. BE no-op (P-220 contract already
    # carried waitlist signals).
    # P-230 fully shipped 2026-05-03 FE-side (3-commit set ending 28bf765)
    # — moved to SHIPPED. BE no-op (P-201/P-201.x/P-240/F-080d covered
    # the full data surface).
    # ── 2026-05-04 BACKLOG restructure — soft-beta definition lock ──
    # Process gate (file FIRST so PRs going forward are governed):
    "F-225",                  # Desktop verification protocol (1440px)

    # Bug + copy hygiene (small but quality-gating):
    "F-222",                  # Sign Out bug fix
    # F-223 fully shipped 2026-05-06 (FE delete 2026-05-04 + BE delete
    # e7d0ea1) — moved to SHIPPED. 5,358 lines of dead Jinja retired.

    # Desktop responsive — every shipped surface broken on desktop:
    "F-200",                  # Landing page desktop layout
    "F-201",                  # Onboarding flow desktop layout
    "F-202",                  # /ecole + L'École intro rebuild
    "F-203",                  # /progress dashboard desktop layout
    "P-230.depth",            # /progress real content (paired with F-203)
    "F-204",                  # /cluster/[slug] desktop layout
    "F-205",                  # /speaking/* (Tâche surfaces) desktop
    "F-206",                  # Auxiliary pages desktop

    # Onboarding restructure (brand-layer pivot):
    "F-220",                  # Onboarding intro framing
    "F-221",                  # Exam-selector + brand-layer rewrite

    # F-224 fully shipped 2026-05-06 (real Claude analysis + 14 v1
    # prompts seeded prod via alembic f4d5e6c7b8a9 + commit ae785a4).
    # Moved to SHIPPED.

    # V-series — verification-found refinement (filed 2026-05-05).
    # V-009 + V-010 lead — methodology-content contradictions in shipped
    # surfaces (radar mislabels + /ecole phase structure stale). "Ship
    # before any chrome work" per spec.
    # V-005 ships before V-003/V-004 (foundation; they inherit typography).
    "V-009",                  # CouchesDiagnostic radar: 5-axis + brand labels
    "V-010",                  # /ecole phase structure (3 → 2 phases)
    "V-013",                  # Pre-launch surface completeness (a/b/c sub-tickets)
    "V-015",                  # Post-V-013 fixes + desktop redesign (a/b/c/d sub-tickets)
    "V-016",                  # Post-V-015 fixes (a urgent BE timeout, b–f FE)
    "F-300",                  # Platform repositioning + Store (7 sub-tickets a–g)
    "V-005",                  # Font system upgrade (Switzer + Fraunces)
    "V-001",                  # Hero H1 + rotating kicker sizing
    "V-002",                  # Em-dash strip across FE copy
    "V-003",                  # Hero atmospheric typographic animation
    "V-004",                  # Differentiation cards rebuild (Codersera-grade)
    "V-011",                  # FinalCTA centering + color refresh (filed 2026-05-06)

    # Visual identity at Promova-bench level:
    "F-210",                  # Icon system
    "F-211",                  # Loading states overhaul
    "F-212",                  # Micro-animations + interaction feedback
    "F-213",                  # Page transitions + motion design
    "F-214",                  # Visual depth + design system extension

    # ── Existing pre-restructure work ──
    "P-234",                  # cluster detail view (BE shipped, FE in progress)

    # Pre-launch product:
    "P-105", "P-106",         # 7-day trial + LemonSqueezy integration
    # P-260.5 deferred 2026-05-03 to month-2 launch event (post-soft-beta).

    # Pre-launch business:
    # B-102 fully shipped 2026-05-03 FE-side.
    "B-100",                  # MoR provider selection (Path A vs Path B, pending Chadi)

    # Pre-launch marketing:
    # M-100 + M-101 fully shipped 2026-05-03.
    "M-103", "M-104",         # YouTube anchor (rescoped) + Reddit (broadened)
]
POST_LAUNCH_P1 = [
    "P-107", "P-108", "P-110",
    "P-211b",
    "P-213",                  # FE-migrated: dialogue box template authoring
    "P-220.z",
    "P-231", "P-232", "P-233", # FE-migrated: speaking / per-tâche / curriculum view dashboards
    "P-235", "P-236", "P-237", # FE-migrated: ceiling marker map / mistake repo / time-adaptive UI lean
    "P-240b",                 # P-240 prose layer split — blocked on P-213
    "P-241", "P-250", "P-251",
    "P-260.5",                # 3 TCF Canada mocks — Sprint product, month-2 launch event
    "F-226",                  # FR voice audit + full-app tu-form sweep (post-soft-beta)
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
    # 2026-05-04 BACKLOG restructure:
    "B-200",                  # Book-Lab store surface (Phase 2 brand expansion)
]
# 2026-05-02 follow-up triage: P-212 superseded by P-210 + P-211.
# P-220 fully shipped (BE + FE + production verification) 2026-05-02.
# P-200 fully shipped (3-commit set, BE only — no FE consumer yet) 2026-05-02.
# P-201 fully shipped (2-commit set, BE only — FE consumer is dashboard work) 2026-05-02.
# P-221 fully shipped (single commit c475bb7, BE only — FE banner + results screen pending) 2026-05-02.
# P-104 fully shipped FE-side 2026-05-01 (commit fluentpath-frontend@48b61a1, BE no-op).
# P-240 action layer shipped 2026-05-02 (single commit 6b8ee43); prose layer
# split as P-240b (Post-launch P1, blocked on P-213).
# F-079 fully shipped 2026-05-03 (DNS + Vercel SSL + CORS via env, ops only — no code commit).
# P-222 fully shipped 2026-05-03 FE-side (commits 59fb2c6 + deff02b + 820d788, BE no-op).
# B-102 fully shipped 2026-05-03 FE-side (commit 3216d4d — /privacy + /terms + /refund).
# P-230 fully shipped 2026-05-03 FE-side (3-commit set ending 28bf765, BE no-op).
# M-101 fully shipped 2026-05-03 (landing page LeMethodic-voice copy live via M-101a).
# M-100 fully shipped 2026-05-03 (Past Preply re-engagement outreach delivered).
# F-224 fully shipped 2026-05-06 (writing surface — real Claude analysis +
# 14 v1 prompts seeded prod via alembic f4d5e6c7b8a9 + commit ae785a4).
# F-223 fully shipped 2026-05-06 (FE delete 2026-05-04 + BE delete e7d0ea1
# — Jinja templates retired without log verification per Chadi).
SHIPPED = [
    "B-102",
    "F-079", "F-110", "F-110.1", "F-110.2", "F-223", "F-224",
    "P-103", "P-104",
    "P-200", "P-201", "P-202", "P-203", "P-204",
    "P-210", "P-211", "P-212", "P-220", "P-221", "P-222",
    "P-230", "P-240",
    "M-100", "M-101",
]
# Decided not to pursue. Keep entry to preserve history.
CLOSED = ["M-105"]


# Tag value injected as **Tag:** line per ticket body.
TAG_TEXT = {
    "active_lc":  "Active — Launch Critical (before soft beta launches)",
    "p1":         "Post-launch P1 (2-4 weeks after launch)",
    "p2":         "Post-launch P2 — signal-driven (defer until real signal)",
    "deferred":   "Phase 2 / deferred indefinitely",
    "shipped":    None,   # no tag for shipped — status reflects history
    "closed":     "Closed — decided not to pursue",
}

# Section ordering in the regenerated file.
SECTIONS = [
    ("active_lc",  f"Active — Launch Critical ({len(ACTIVE_LC)} tickets, before soft beta launches)",  ACTIVE_LC),
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
    out.append("## Active Queue — Launch Critical (before soft beta launches)")
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
