"""One-shot migration: add F-038 fluency column to the recordings table.

Follows the same pattern as scripts/add_dual_channel_columns.py: direct
ALTER TABLE against the SQLite DB, idempotent.

Run from project root:
    python -m scripts.add_fluency_column
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "tcf_oral.db"

NEW_COLUMNS = [
    ("fluency", "TEXT DEFAULT ''"),
]


def main() -> int:
    if not DB_PATH.exists():
        print(f"DB not found at {DB_PATH}. Skipping.")
        return 0

    conn = sqlite3.connect(str(DB_PATH))
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(recordings)")
        existing = {row[1] for row in cur.fetchall()}

        added = []
        for col, decl in NEW_COLUMNS:
            if col in existing:
                continue
            cur.execute(f"ALTER TABLE recordings ADD COLUMN {col} {decl}")
            added.append(col)

        conn.commit()
        if added:
            print(f"Added columns to recordings: {', '.join(added)}")
        else:
            print("Fluency column already present. Nothing to do.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
