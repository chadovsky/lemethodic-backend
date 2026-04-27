# Archived during F-077 PostgreSQL migration. Schema change is now
# part of the initial Alembic migration. Kept for historical reference.
"""One-shot migration: add F-047 tache_mode column to the recordings table.

Forward: adds the column nullable, backfills all existing rows to "legacy",
and reports the row count. New rows are enforced as non-null at the router
layer (SQLite can't add NOT NULL to an existing column without a table
rebuild — the app-layer check is sufficient and keeps the migration
reversible).

Reverse: drops the column by rebuilding the table (SQLite has no native
DROP COLUMN in older versions). The rebuild copies all non-tache_mode
columns; data is preserved modulo the dropped column.

Usage from project root:
    python -m scripts.add_tache_mode_column            # forward
    python -m scripts.add_tache_mode_column --rollback # reverse
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "tcf_oral.db"

COLUMN_NAME = "tache_mode"
COLUMN_DECL = "TEXT"
BACKFILL_VALUE = "legacy"


def _col_names(cur, table: str) -> list[str]:
    cur.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cur.fetchall()]


def forward(conn: sqlite3.Connection) -> int:
    cur = conn.cursor()
    existing = _col_names(cur, "recordings")
    if COLUMN_NAME in existing:
        print(f"Column {COLUMN_NAME} already present. Skipping ALTER.")
    else:
        cur.execute(f"ALTER TABLE recordings ADD COLUMN {COLUMN_NAME} {COLUMN_DECL}")
        print(f"Added column recordings.{COLUMN_NAME}")

    # Backfill any NULL rows (covers fresh migration and partial re-runs).
    cur.execute(
        f"UPDATE recordings SET {COLUMN_NAME} = ? WHERE {COLUMN_NAME} IS NULL",
        (BACKFILL_VALUE,),
    )
    backfilled = cur.rowcount
    conn.commit()
    print(f"Backfilled {backfilled} row(s) to '{BACKFILL_VALUE}'.")
    return 0


def rollback(conn: sqlite3.Connection) -> int:
    """Drop the tache_mode column via table rebuild.

    SQLite added native DROP COLUMN in 3.35 (2021). Use it if available,
    otherwise fall back to the rebuild-copy approach.
    """
    cur = conn.cursor()
    existing = _col_names(cur, "recordings")
    if COLUMN_NAME not in existing:
        print(f"Column {COLUMN_NAME} not present. Nothing to roll back.")
        return 0

    # Try native DROP COLUMN first.
    try:
        cur.execute(f"ALTER TABLE recordings DROP COLUMN {COLUMN_NAME}")
        conn.commit()
        print(f"Dropped column recordings.{COLUMN_NAME} (native).")
        return 0
    except sqlite3.OperationalError as exc:
        print(f"Native DROP COLUMN unavailable ({exc}); falling back to rebuild.")

    # Rebuild path for older SQLite.
    preserved = [c for c in existing if c != COLUMN_NAME]
    col_list = ", ".join(preserved)
    try:
        cur.execute("BEGIN")
        cur.execute(f"CREATE TABLE recordings_new AS SELECT {col_list} FROM recordings")
        cur.execute("DROP TABLE recordings")
        cur.execute("ALTER TABLE recordings_new RENAME TO recordings")
        conn.commit()
        print(f"Dropped column recordings.{COLUMN_NAME} (rebuild). "
              f"NOTE: indexes/constraints must be recreated manually if needed.")
        return 0
    except Exception:
        conn.rollback()
        raise


def main(argv: list[str]) -> int:
    if not DB_PATH.exists():
        print(f"DB not found at {DB_PATH}. Skipping.")
        return 0

    mode = "forward"
    if len(argv) > 1 and argv[1] in ("--rollback", "--reverse", "--down"):
        mode = "rollback"

    conn = sqlite3.connect(str(DB_PATH))
    try:
        if mode == "rollback":
            return rollback(conn)
        return forward(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
