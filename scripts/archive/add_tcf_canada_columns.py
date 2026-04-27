# Archived during F-077 PostgreSQL migration. Schema change is now
# part of the initial Alembic migration. Kept for historical reference.
"""One-shot migration: add TCF Canada 5-criterion columns to the feedbacks table.

Follows the same pattern used when `argument_structure` was added: direct
ALTER TABLE against the SQLite DB. Safe to run multiple times — checks
existing columns first.

Run from project root:
    python -m scripts.add_tcf_canada_columns
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "tcf_oral.db"

NEW_COLUMNS = [
    ("criteria_breakdown", "TEXT DEFAULT ''"),
    ("cefr_level", "VARCHAR(20) DEFAULT ''"),
    ("clb_level", "INTEGER"),
    ("exam_profile", "VARCHAR(50) DEFAULT 'tcf_canada'"),
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
            print("All TCF Canada columns already present. Nothing to do.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
