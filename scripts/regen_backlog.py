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
    # In the user's stated priority order — preserved as the Active Queue order.
    "P-104", "P-105", "P-106",
    "P-200", "P-201",
    "P-220", "P-221", "P-240",
    "B-100", "B-102",
    "M-100", "M-101",
]
POST_LAUNCH_P1 = [
    "P-107", "P-108", "P-110",
    "P-211b",
    "P-241", "P-250", "P-251",
    "B-101", "B-104", "B-105",
    "M-102", "M-107", "M-108",
]
POST_LAUNCH_P2 = [
    "P-102", "P-103.1", "P-109",
    "P-210.1", "P-211a", "P-211c",
    "P-220.x", "P-220.y",
]
DEFERRED = [
    "P-260", "P-262", "P-266",
    "P-300", "P-301", "P-302", "P-303",
    "F-077.x", "F-078.x", "F-111",
    "B-103",
]
KILL = ["P-212", "P-103.2"]
MARKETING_PICK_ONE = ["M-103", "M-104", "M-105", "M-106"]
SHIPPED = ["F-110", "F-110.1", "F-110.2", "P-103",
           "P-202", "P-203", "P-204", "P-210", "P-211"]
# F-079 unclassified -> Pending Classification section.
PENDING = ["F-079"]


# Tag value injected as **Tag:** line per ticket body.
TAG_TEXT = {
    "active_lc":  "Active — Launch Critical (60-day target)",
    "p1":         "Post-launch P1 (2-4 weeks after launch)",
    "p2":         "Post-launch P2 — signal-driven (defer until real signal)",
    "deferred":   "Phase 2 / deferred indefinitely",
    "kill":       "Kill candidate — verification pending",
    "mkt_pick1":  "Marketing — Choose 1, close 3",
    "shipped":    None,   # no tag for shipped
    "pending":    "Pending classification",
}

# Section ordering in the regenerated file.
SECTIONS = [
    ("active_lc",  "Active — Launch Critical (12 tickets, 60-day target)",  ACTIVE_LC),
    ("p1",         "Post-launch P1 (2-4 weeks after launch)",                POST_LAUNCH_P1),
    ("p2",         "Post-launch P2 — signal-driven",                         POST_LAUNCH_P2),
    ("deferred",   "Phase 2 / deferred indefinitely",                        DEFERRED),
    ("mkt_pick1",  "Marketing — Choose 1, close 3 (verify with founder)",   MARKETING_PICK_ONE),
    ("kill",       "Kill candidates — verification pending",                 KILL),
    ("pending",    "Pending classification",                                 PENDING),
    ("shipped",    "Shipped",                                                SHIPPED),
]


# ── Parsing ──────────────────────────────────────────────────────

HEADER_RE = re.compile(
    r"^## ([A-Z][A-Z0-9-]*[0-9](?:\.[a-z0-9]+|[a-z]+)*)\s*[—-]\s*.+?\s*$",
    re.MULTILINE,
)


def parse_backlog(text: str) -> tuple[str, dict[str, str]]:
    """Returns (preamble, {ticket_id: body_block}).

    body_block includes the `## ID — Title` line through the trailing `---`
    separator (or end-of-file). Tickets keep their full original content
    so we don't lose any author intent.
    """
    matches = list(HEADER_RE.finditer(text))
    if not matches:
        return text, {}
    preamble = text[:matches[0].start()]
    bodies: dict[str, str] = {}
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[m.start():end].rstrip()
        # Normalize trailing `---` so re-rendering is idempotent.
        if not block.endswith("---"):
            block = block + "\n\n---"
        bodies[m.group(1)] = block + "\n\n"
    return preamble, bodies


# ── Tag injection ────────────────────────────────────────────────

STATUS_LINE_RE = re.compile(r"^\*\*Status:\*\*.*$", re.MULTILINE)
TAG_LINE_RE = re.compile(r"^\*\*Tag:\*\*.*\n", re.MULTILINE)


def inject_tag(body: str, tag_value: str | None) -> str:
    """Idempotent: strips any existing **Tag:** line, then inserts the
    new one (if any) right after the **Status:** line."""
    body = TAG_LINE_RE.sub("", body)
    if tag_value is None:
        return body
    new_tag_line = f"**Tag:** {tag_value}.\n"
    m = STATUS_LINE_RE.search(body)
    if not m:
        # No Status line — append tag line right after the heading line.
        lines = body.split("\n", 1)
        return lines[0] + "\n\n" + new_tag_line + (lines[1] if len(lines) > 1 else "")
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


def render(preamble: str, bodies: dict[str, str]) -> str:
    """Build the new file content."""
    # Update the preamble: bump 'Last updated' if present, otherwise leave alone.
    new_preamble = re.sub(
        r"\*\*Last updated:\*\*\s+[\d-]+\.",
        "**Last updated:** 2026-05-02 (re-baseline pass).",
        preamble,
    )
    # Append a one-line note about the re-baseline.
    if "**Last updated:**" in new_preamble and "re-baseline" not in new_preamble:
        new_preamble += (
            "\nThis file was re-organized 2026-05-02 by tag (Active — Launch "
            "Critical, Post-launch P1, Post-launch P2, Deferred, Shipped). "
            "Re-runnable via `scripts/regen_backlog.py`.\n\n"
        )

    chunks = [new_preamble.rstrip() + "\n\n", build_active_queue(bodies)]

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
    preamble, bodies = parse_backlog(text)
    print(f"parsed {len(bodies)} tickets from BACKLOG.md")

    classified = sum(len(ids) for _, _, ids in SECTIONS)
    print(f"classifications cover {classified} ids "
          f"(some may not yet exist as bodies)")

    new_text = render(preamble, bodies)
    SRC.write_text(new_text, encoding="utf-8")
    print(f"wrote {len(new_text)} bytes to BACKLOG.md")

    # Sanity round-trip: re-parse and confirm every original ticket survives.
    _, bodies_after = parse_backlog(new_text)
    missing = set(bodies) - set(bodies_after)
    extra = set(bodies_after) - set(bodies)
    print(f"round-trip: {len(bodies_after)} tickets in regenerated file")
    print(f"  missing from rewrite: {sorted(missing)}")
    print(f"  added by rewrite:     {sorted(extra)}")
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
