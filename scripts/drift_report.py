"""Two-BACKLOG drift diagnostic.

Compares this repo's BACKLOG.md against the FE repo's BACKLOG.md and
reports four categories of drift:

  1. FE-only tickets (present in lemethodic-frontend, absent here)
  2. BE-only tickets (present here, absent in lemethodic-frontend)
  3. Status conflicts (same ticket ID, different status)
  4. Title conflicts (same ticket ID, different title)

Usage:
    python -m scripts.drift_report
    python -m scripts.drift_report --fe-path C:\\path\\to\\frontend\\BACKLOG.md

Re-runnable. Used during the 2026-05-02 reconciliation pass; kept as
a permanent diagnostic so future drift checks don't require re-deriving
the parser.

Filed B-106 captures the longer-term consolidation plan; this tool is
the lightweight check-in mechanism while B-106 stays queued.

The two BACKLOG files use different heading conventions:
  BE: ``## ID — Title``     (level-2, tag-grouped sections)
  FE: ``### ID — Title``    (level-3, week-grouped Shipped sections)

The parser handles both. Recommendations are intentionally NOT computed
in code — they're judgment calls that belong in the reconciliation pass,
not in a static diagnostic.
"""
from __future__ import annotations

import argparse
import io
import re
import sys
from pathlib import Path
from typing import Pattern


HEADER_RE_BE = re.compile(
    r"^## ([A-Z][A-Z0-9-]*[0-9](?:\.[a-z0-9]+|[a-z]+)*)\s*[—-]\s*(.+?)\s*$",
    re.MULTILINE,
)
HEADER_RE_FE = re.compile(
    r"^### ([A-Z][A-Z0-9-]*[0-9](?:\.[a-z0-9]+|[a-z]+)*)\s*[—-]\s*(.+?)\s*$",
    re.MULTILINE,
)

DEFAULT_FE_PATH = r"C:\Users\pc\Downloads\fluentpath-frontend\BACKLOG.md"


def _field(body: str, name: str) -> str | None:
    m = re.search(rf"\*\*{re.escape(name)}:\*\*\s*(.+?)$", body, re.MULTILINE)
    return m.group(1).strip().rstrip(".") if m else None


def parse(path: str | Path, regex: Pattern) -> dict[str, dict]:
    """Parse a BACKLOG file. Returns {ticket_id: {title, status}}."""
    text = Path(path).read_text(encoding="utf-8")
    matches = list(regex.finditer(text))
    out: dict[str, dict] = {}
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.end():end].strip()
        out[m.group(1)] = {
            "title": m.group(2).strip(),
            "status": _field(body, "Status") or "—",
        }
    return out


def _short(s: str | None, n: int = 60) -> str:
    if not s or s == "—":
        return "—"
    s = s.replace("\n", " ").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def _normalize_status(s: str) -> str:
    """Normalize for status-equivalence comparison: drop parenthetical
    detail, lowercase, strip trailing punctuation."""
    return (s or "").split("(")[0].strip().rstrip(",.").lower()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--be-path", default="BACKLOG.md",
                    help="Path to the BE BACKLOG.md (default: BACKLOG.md)")
    ap.add_argument("--fe-path", default=DEFAULT_FE_PATH,
                    help=f"Path to the FE BACKLOG.md (default: {DEFAULT_FE_PATH})")
    args = ap.parse_args()

    BE = parse(args.be_path, HEADER_RE_BE)
    FE = parse(args.fe_path, HEADER_RE_FE)

    print(f"BE BACKLOG: {len(BE)} tickets ({args.be_path})")
    print(f"FE BACKLOG: {len(FE)} tickets ({args.fe_path})")
    print()

    fe_only = sorted(set(FE) - set(BE))
    be_only = sorted(set(BE) - set(FE))
    shared = sorted(set(BE) & set(FE))

    # ── 1. FE-only ──────────────────────────────────────────────
    print(f"# 1. FE-only tickets ({len(fe_only)})\n")
    print("| ID | Title | FE Status |")
    print("|---|---|---|")
    for tid in fe_only:
        print(f"| {tid} | {_short(FE[tid]['title'], 60)} | {_short(FE[tid]['status'], 30)} |")

    # ── 2. BE-only ──────────────────────────────────────────────
    print(f"\n# 2. BE-only tickets ({len(be_only)})\n")
    print("| ID | Title | BE Status |")
    print("|---|---|---|")
    for tid in be_only:
        print(f"| {tid} | {_short(BE[tid]['title'], 60)} | {_short(BE[tid]['status'], 30)} |")

    # ── 3. Status conflicts ─────────────────────────────────────
    status_conflicts = []
    for tid in shared:
        bes_n = _normalize_status(BE[tid]["status"])
        fes_n = _normalize_status(FE[tid]["status"])
        if bes_n == fes_n:
            continue
        if bes_n and fes_n and (bes_n.startswith(fes_n) or fes_n.startswith(bes_n)):
            continue
        status_conflicts.append(tid)
    print(f"\n# 3. Status conflicts ({len(status_conflicts)})\n")
    print("| ID | BE Status | FE Status |")
    print("|---|---|---|")
    for tid in status_conflicts:
        print(f"| {tid} | {_short(BE[tid]['status'], 35)} | {_short(FE[tid]['status'], 35)} |")

    # ── 4. Title conflicts ──────────────────────────────────────
    title_conflicts = [tid for tid in shared if BE[tid]["title"] != FE[tid]["title"]]
    print(f"\n# 4. Title conflicts ({len(title_conflicts)})\n")
    print("| ID | BE Title | FE Title |")
    print("|---|---|---|")
    for tid in title_conflicts:
        print(f"| {tid} | {_short(BE[tid]['title'], 40)} | {_short(FE[tid]['title'], 40)} |")

    # Summary
    print(f"\n# Summary")
    print(f"  total unique tickets: {len(set(BE) | set(FE))}")
    print(f"  FE-only: {len(fe_only)}")
    print(f"  BE-only: {len(be_only)}")
    print(f"  shared: {len(shared)}")
    print(f"  status conflicts: {len(status_conflicts)}")
    print(f"  title conflicts: {len(title_conflicts)}")

    return 0 if not status_conflicts else 1


if __name__ == "__main__":
    sys.exit(main())
