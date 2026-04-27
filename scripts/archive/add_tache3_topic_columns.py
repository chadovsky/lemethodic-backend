# Archived during F-077 PostgreSQL migration. Schema change is now
# part of the initial Alembic migration. Kept for historical reference.
"""F-051 — add Tâche 3 prompt + difficulty columns to test_topics.

Forward: four idempotent ALTER TABLE statements. No data touched.
Reverse: drops the four columns. Uses native DROP COLUMN where the
SQLite version supports it (3.35+); rebuilds the table otherwise.

Usage from project root:
    python -m scripts.add_tache3_topic_columns             # forward
    python -m scripts.add_tache3_topic_columns --rollback  # reverse
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "tcf_oral.db"

NEW_COLUMNS: list[tuple[str, str]] = [
    ("tache_3_prompt_fr", "TEXT DEFAULT ''"),
    ("tache_3_prompt_en", "TEXT DEFAULT ''"),
    ("tache_3_prompt_es", "TEXT DEFAULT ''"),
    ("tache_3_difficulty", "VARCHAR(10) DEFAULT 'B1_B2'"),
]


def _col_names(cur, table: str) -> list[str]:
    cur.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cur.fetchall()]


def forward(conn: sqlite3.Connection) -> int:
    cur = conn.cursor()
    existing = _col_names(cur, "test_topics")
    if not existing:
        print("test_topics table not found; run init_db.py first.")
        return 1
    added = []
    for col, decl in NEW_COLUMNS:
        if col in existing:
            continue
        cur.execute(f"ALTER TABLE test_topics ADD COLUMN {col} {decl}")
        added.append(col)
    conn.commit()
    if added:
        print(f"Added columns to test_topics: {', '.join(added)}")
    else:
        print("All Tâche 3 columns already present.")
    cur.execute("SELECT COUNT(*) FROM test_topics")
    print(f"test_topics rows: {cur.fetchone()[0]}")
    return 0


def rollback(conn: sqlite3.Connection) -> int:
    cur = conn.cursor()
    existing = _col_names(cur, "test_topics")
    to_drop = [c for c, _ in NEW_COLUMNS if c in existing]
    if not to_drop:
        print("No Tâche 3 columns present; nothing to roll back.")
        return 0

    # Try native DROP COLUMN (SQLite 3.35+). If it fails, rebuild the
    # table preserving only the non-target columns.
    native_ok = True
    for col in to_drop:
        try:
            cur.execute(f"ALTER TABLE test_topics DROP COLUMN {col}")
        except sqlite3.OperationalError as exc:
            print(f"Native DROP COLUMN unavailable ({exc}); rebuilding.")
            native_ok = False
            break
    if native_ok:
        conn.commit()
        print(f"Dropped columns: {', '.join(to_drop)}")
        return 0

    # Rebuild path.
    preserved = [c for c in existing if c not in to_drop]
    col_list = ", ".join(preserved)
    try:
        cur.execute("BEGIN")
        cur.execute(f"CREATE TABLE test_topics_new AS SELECT {col_list} FROM test_topics")
        cur.execute("DROP TABLE test_topics")
        cur.execute("ALTER TABLE test_topics_new RENAME TO test_topics")
        conn.commit()
        print(f"Dropped columns (rebuild): {', '.join(to_drop)}. "
              f"NOTE: indexes must be recreated manually if any existed.")
        return 0
    except Exception:
        conn.rollback()
        raise


def main(argv: list[str]) -> int:
    if not DB_PATH.exists():
        print(f"DB not found at {DB_PATH}. Skipping.")
        return 0
    do_rollback = any(a in ("--rollback", "--reverse", "--down") for a in argv[1:])
    conn = sqlite3.connect(str(DB_PATH))
    try:
        return rollback(conn) if do_rollback else forward(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
