# Archived during F-077 PostgreSQL migration. Schema change is now
# part of the initial Alembic migration. Kept for historical reference.
"""F-060 migration: add onboarding persistence columns to the users table.

Follows the same pattern as scripts/add_fluency_column.py: direct ALTER TABLE
against the SQLite DB, idempotent via PRAGMA table_info.

The existing ui_language column is intentionally reused for the frontend's
`interface_language` onboarding field — no second column is added.

Run from project root:
    python -m scripts.add_onboarding_columns
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "tcf_oral.db"

NEW_COLUMNS = [
    ("target_level", "VARCHAR(10)"),
    ("exam_profile", "VARCHAR(50)"),
    ("exam_date", "DATE"),
    ("goal", "VARCHAR(100)"),
    ("current_level", "VARCHAR(20)"),
]


def main() -> int:
    if not DB_PATH.exists():
        print(f"DB not found at {DB_PATH}. Skipping.")
        return 0

    conn = sqlite3.connect(str(DB_PATH))
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(users)")
        existing = {row[1] for row in cur.fetchall()}

        added = []
        for col, decl in NEW_COLUMNS:
            if col in existing:
                continue
            cur.execute(f"ALTER TABLE users ADD COLUMN {col} {decl}")
            added.append(col)

        conn.commit()
        if added:
            print(f"Added columns to users: {', '.join(added)}")
        else:
            print("Onboarding columns already present. Nothing to do.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
