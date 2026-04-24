"""One-shot migration: add F-032 dual-channel feedback columns to the
feedbacks table.

Follows the same pattern as scripts/add_tcf_canada_columns.py: direct
ALTER TABLE against the SQLite DB, idempotent.

Run from project root:
    python -m scripts.add_dual_channel_columns
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "tcf_oral.db"

NEW_COLUMNS = [
    ("examiner_remarks", "TEXT DEFAULT '{}'"),
    ("teacher_coaching", "TEXT DEFAULT '{}'"),
    ("feedback_grid", "TEXT DEFAULT '{}'"),
]


def main() -> int:
    if not DB_PATH.exists():
        print(f"DB not found at {DB_PATH}. Skipping.")
        return 0

    conn = sqlite3.connect(str(DB_PATH))
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(feedbacks)")
        existing = {row[1] for row in cur.fetchall()}

        added = []
        for col, decl in NEW_COLUMNS:
            if col in existing:
                continue
            cur.execute(f"ALTER TABLE feedbacks ADD COLUMN {col} {decl}")
            added.append(col)

        conn.commit()
        if added:
            print(f"Added columns to feedbacks: {', '.join(added)}")
        else:
            print("All dual-channel columns already present. Nothing to do.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
