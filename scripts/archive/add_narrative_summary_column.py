# Archived during F-077 PostgreSQL migration. Schema change is now
# part of the initial Alembic migration. Kept for historical reference.
"""F-084 — add `narrative_summary` TEXT column to feedbacks.

Stores the single-sentence diagnostic hero produced by the F-084
narrative-summary extension to the F-083 rubric prompt. Surfaces at
the API boundary as `diagnostic.narrative_summary` (top-level alongside
`diagnostic.tache_rubric`).

Idempotent. Same shape as F-083's add_tache_rubric_data_column.py.

Run from project root:
    python -m scripts.add_narrative_summary_column
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "tcf_oral.db"


def migrate(con: sqlite3.Connection) -> None:
    cur = con.cursor()
    cur.execute("PRAGMA table_info(feedbacks)")
    columns = {row[1] for row in cur.fetchall()}

    if "narrative_summary" in columns:
        print("[F-084] narrative_summary already present; nothing to do.")
        return

    cur.execute("ALTER TABLE feedbacks ADD COLUMN narrative_summary TEXT")
    con.commit()
    print("[F-084] added narrative_summary TEXT column to feedbacks.")


def main() -> None:
    print(f"[F-084] migrating {DB_PATH} ...")
    con = sqlite3.connect(DB_PATH)
    try:
        migrate(con)
    finally:
        con.close()
    print("[F-084] done.")


if __name__ == "__main__":
    main()
