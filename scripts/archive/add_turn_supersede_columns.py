# Archived during F-077 PostgreSQL migration. Schema change is now
# part of the initial Alembic migration. Kept for historical reference.
"""F-062.3 migration: add supersede-tracking columns to conversation_turns.

Enables the Tâche 2 re-record flow. The superseded_at column flips from
NULL → timestamp when the frontend calls POST /api/conversations/{id}/turn/
{turn_number}/supersede. The /end finalize path filters those rows out of
analysis; the audio stays on disk for audit (future cleanup job deferred).

Follows the same idempotent pattern as scripts/add_onboarding_columns.py:
direct ALTER TABLE against SQLite, guarded by PRAGMA table_info so a second
run is a no-op.

Note on tooling: this project does not use Alembic (migrations/ is empty and
init_db.py uses Base.metadata.create_all). Repo convention is
scripts/add_*.py per feature; the F-062.3 ticket asked for Alembic but we
stick with repo convention here — introducing Alembic just for one column
addition is disproportionate. If Alembic lands later, these two columns are
idempotent-friendly for the baseline migration.

Run from project root:
    python -m scripts.add_turn_supersede_columns
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "tcf_oral.db"

NEW_COLUMNS = [
    # NULL = active turn; populated when frontend calls /supersede.
    ("superseded_at", "TIMESTAMP"),
    # FK pointer to the replacement turn's id. Self-referential; left as a
    # plain INTEGER here because SQLite does not enforce ADD COLUMN FKs.
    # Application code validates the target exists at write time.
    ("superseded_by_turn_id", "INTEGER"),
]


def main() -> int:
    if not DB_PATH.exists():
        print(f"DB not found at {DB_PATH}. Skipping.")
        return 0

    conn = sqlite3.connect(str(DB_PATH))
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(conversation_turns)")
        existing = {row[1] for row in cur.fetchall()}

        added = []
        for col, decl in NEW_COLUMNS:
            if col in existing:
                continue
            cur.execute(f"ALTER TABLE conversation_turns ADD COLUMN {col} {decl}")
            added.append(col)

        # Partial index — active-turn lookups by (conversation_id, speaker)
        # hit this path on every /turn and /end. Queries filter
        # superseded_at IS NULL so the partial index stays small.
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_conversation_turns_active
            ON conversation_turns (conversation_id, speaker)
            WHERE superseded_at IS NULL
            """
        )

        conn.commit()
        if added:
            print(f"Added columns to conversation_turns: {', '.join(added)}")
        else:
            print("Supersede columns already present. Nothing to do.")
        print("Partial index ix_conversation_turns_active ensured.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
