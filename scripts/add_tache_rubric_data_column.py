"""F-083 — add `tache_rubric_data` TEXT column to feedbacks.

Stores the JSON-serialized output of ``app.services.tache_rubric``: per-
recording pedagogical rubric (summary prose + Tâche-specific dimensions
+ universal sidebars + retry recommendation + next-action suggestion).

Idempotent: PRAGMA-guarded ALTER TABLE. Safe to re-run on fresh + on
already-migrated databases. Repo-convention sqlite3 direct migration
matching the F-062.3 / F-063 / F-080a pattern.

Run from the project root:
    python -m scripts.add_tache_rubric_data_column
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "tcf_oral.db"


def migrate(con: sqlite3.Connection) -> None:
    cur = con.cursor()
    cur.execute("PRAGMA table_info(feedbacks)")
    columns = {row[1] for row in cur.fetchall()}

    if "tache_rubric_data" in columns:
        print("[F-083] tache_rubric_data already present; nothing to do.")
        return

    cur.execute("ALTER TABLE feedbacks ADD COLUMN tache_rubric_data TEXT")
    con.commit()
    print("[F-083] added tache_rubric_data TEXT column to feedbacks.")


def main() -> None:
    print(f"[F-083] migrating {DB_PATH} ...")
    con = sqlite3.connect(DB_PATH)
    try:
        migrate(con)
    finally:
        con.close()
    print("[F-083] done.")


if __name__ == "__main__":
    main()
