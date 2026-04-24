"""F-063 migration: create tache1_openings table.

Tâche 1 is a personal-interview conversation — the examiner always asks
the candidate to introduce themselves, but the opening phrasing varies so
repeat sessions don't feel canned. This table stores the pool; /start
picks a random active row.

Follows the same idempotent pattern as scripts/add_turn_supersede_columns.py:
direct sqlite3 CREATE TABLE IF NOT EXISTS, safe to re-run. Seeding the
rows themselves lives in scripts/seed_tache1_openings.py.

Note on tooling: this project does not use Alembic (migrations/ is empty
and init_db.py uses Base.metadata.create_all). Repo convention is
scripts/add_*.py per feature.

Run from project root:
    python -m scripts.add_tache1_openings
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "tcf_oral.db"

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS tache1_openings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opening_prompt_fr TEXT NOT NULL,
    opening_prompt_en TEXT DEFAULT '',
    opening_prompt_es TEXT DEFAULT '',
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

INDEX_SQL = """
CREATE INDEX IF NOT EXISTS ix_tache1_openings_active
ON tache1_openings (is_active)
"""


def main() -> int:
    if not DB_PATH.exists():
        print(f"DB not found at {DB_PATH}. Skipping.")
        return 0

    conn = sqlite3.connect(str(DB_PATH))
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tache1_openings'")
        existed = cur.fetchone() is not None

        cur.execute(CREATE_SQL)
        cur.execute(INDEX_SQL)
        conn.commit()

        if existed:
            print("Table tache1_openings already present. Nothing to do.")
        else:
            print("Created table tache1_openings + index ix_tache1_openings_active.")
        print("Run `python -m scripts.seed_tache1_openings` to populate prompts.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
