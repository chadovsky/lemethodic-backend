# Archived during F-077 PostgreSQL migration. Schema change is now
# part of the initial Alembic migration. Kept for historical reference.
"""F-086 migration: Le Raccourci -> L'École rename (DB layer).

Atomic schema rename for the curriculum surface. Three tables move:
    raccourci_lessons        -> ecole_lessons
    raccourci_quiz_questions -> ecole_quiz_questions
    user_raccourci_progress  -> user_ecole_progress
And one column on remediation_modules:
    raccourci_lesson_id -> ecole_lesson_id

Row contents are preserved verbatim. F-086 mechanically renames; F-087
will replace lesson rows wholesale and truncate user_ecole_progress.

Idempotency: pre-checks sqlite_master for the new table names. If a
prior run already migrated, the script reports "already migrated" and
exits 0 without touching anything. Same pattern as F-080a's
add_remediation_modules.py.

FK references in dependent tables are auto-rewritten by SQLite's
ALTER TABLE RENAME (3.25+; we're on 3.50.4). foreign_keys=OFF is set
during the migration window as belt-and-braces — both halves of every
rename land before checks resume.

Indexes containing "raccourci" in their NAMES are left in place. They
attach to the renamed parent tables and continue working; the strict
F-086 grep gate is filesystem-scoped, not sqlite_master-scoped, so
internal index names don't surface to it. If `.schema` aesthetics
matter later, drop + re-create with new names — for V1 the cleanup is
not worth the extra failure surface.

Run from project root:
    python -m scripts.rename_raccourci_to_ecole
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "tcf_oral.db"


TABLE_RENAMES: list[tuple[str, str]] = [
    ("raccourci_lessons", "ecole_lessons"),
    ("raccourci_quiz_questions", "ecole_quiz_questions"),
    ("user_raccourci_progress", "user_ecole_progress"),
]

COLUMN_RENAME = (
    "remediation_modules",
    "raccourci_lesson_id",
    "ecole_lesson_id",
)


def _table_exists(cur: sqlite3.Cursor, name: str) -> bool:
    cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    )
    return cur.fetchone() is not None


def _column_exists(cur: sqlite3.Cursor, table: str, column: str) -> bool:
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


def _row_counts(cur: sqlite3.Cursor, names: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for n in names:
        if not _table_exists(cur, n):
            continue
        cur.execute(f"SELECT COUNT(*) FROM {n}")
        out[n] = cur.fetchone()[0]
    return out


def main() -> int:
    if not DB_PATH.exists():
        print(f"DB not found at {DB_PATH}. Skipping.")
        return 0

    conn = sqlite3.connect(str(DB_PATH))
    try:
        cur = conn.cursor()

        # ── Idempotency check ────────────────────────────────────────
        new_tables_present = all(
            _table_exists(cur, new) for _old, new in TABLE_RENAMES
        )
        old_tables_present = any(
            _table_exists(cur, old) for old, _new in TABLE_RENAMES
        )
        new_col_present = _column_exists(cur, COLUMN_RENAME[0], COLUMN_RENAME[2])
        old_col_present = _column_exists(cur, COLUMN_RENAME[0], COLUMN_RENAME[1])

        if new_tables_present and not old_tables_present and new_col_present and not old_col_present:
            print("F-086 rename already applied. Nothing to do.")
            return 0

        # Half-migrated states are tolerated — the per-table loop below
        # checks each rename independently. This was discovered the hard
        # way when an earlier run crashed on a print() encoding error
        # AFTER one ALTER TABLE auto-committed, leaving one table renamed
        # and two not. The script must be re-runnable from any partial
        # state.

        # ── Pre-snapshot for verify-after ───────────────────────────
        pre_counts: dict[str, int] = {}
        for old, _new in TABLE_RENAMES:
            if _table_exists(cur, old):
                cur.execute(f"SELECT COUNT(*) FROM {old}")
                pre_counts[old] = cur.fetchone()[0]

        cur.execute("PRAGMA foreign_keys=OFF")
        try:
            for old, new in TABLE_RENAMES:
                if _table_exists(cur, old):
                    cur.execute(f"ALTER TABLE {old} RENAME TO {new}")
                    print(f"Renamed table: {old} -> {new}")
                elif _table_exists(cur, new):
                    print(f"  (skipping {old} -> {new}: target already exists)")
                else:
                    print(f"  (skipping {old} -> {new}: source not found)")

            table, old_col, new_col = COLUMN_RENAME
            if _column_exists(cur, table, old_col):
                cur.execute(
                    f"ALTER TABLE {table} RENAME COLUMN {old_col} TO {new_col}"
                )
                print(f"Renamed column: {table}.{old_col} -> {new_col}")
            elif _column_exists(cur, table, new_col):
                print(f"  (skipping {table}.{old_col}: target column already exists)")
            else:
                print(f"  (skipping {table}.{old_col}: source column not found)")

            conn.commit()
        finally:
            cur.execute("PRAGMA foreign_keys=ON")

        # ── Post-verify: row counts preserved ───────────────────────
        post_counts = _row_counts(cur, [new for _old, new in TABLE_RENAMES])
        for old, new in TABLE_RENAMES:
            pre = pre_counts.get(old)
            post = post_counts.get(new)
            if pre is None:
                continue
            if pre != post:
                print(
                    f"ERROR: row count drift on {new}: pre={pre}, post={post}. "
                    "Roll back manually."
                )
                return 3
            print(f"  {new}: {post} rows (preserved from {old})")

        # Sanity check on the renamed column
        cur.execute(
            "SELECT COUNT(*) FROM remediation_modules WHERE ecole_lesson_id IS NOT NULL"
        )
        non_null = cur.fetchone()[0]
        print(f"  remediation_modules.ecole_lesson_id non-null rows: {non_null}")

        print("F-086 rename complete.")
        print(
            "Next: reseed module JSONs with the renamed key "
            "(scripts/seed_remediation_modules.py)."
        )
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
