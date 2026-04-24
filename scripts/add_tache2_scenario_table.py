"""One-shot migration: create F-049 Tâche 2 scenario table + add
scenario_id to conversations.

Forward:
  1. CREATE TABLE tache2_scenarios (idempotent).
  2. ALTER TABLE conversations ADD COLUMN scenario_id (idempotent).

Reverse:
  1. DROP COLUMN conversations.scenario_id via native DROP or rebuild
     fallback (mirrors scripts/add_tache_mode_column.py).
  2. DROP TABLE tache2_scenarios. Refuses if scenarios are present
     unless ``--force`` is passed, since losing Yarden-seeded data would
     mean re-running the seed script from Chadi's source docs.

Usage from project root:
    python -m scripts.add_tache2_scenario_table               # forward
    python -m scripts.add_tache2_scenario_table --rollback    # reverse
    python -m scripts.add_tache2_scenario_table --rollback --force
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "tcf_oral.db"

DDL_SCENARIOS = """
CREATE TABLE IF NOT EXISTS tache2_scenarios (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    code                VARCHAR(64) UNIQUE NOT NULL,
    title_fr            VARCHAR(200) DEFAULT '',
    title_en            VARCHAR(200) DEFAULT '',
    title_es            VARCHAR(200) DEFAULT '',
    candidate_brief_fr  TEXT DEFAULT '',
    candidate_brief_en  TEXT DEFAULT '',
    candidate_brief_es  TEXT DEFAULT '',
    examiner_persona    TEXT DEFAULT '',
    data_targets        TEXT DEFAULT '[]',
    register            VARCHAR(20) DEFAULT 'formel',
    difficulty          VARCHAR(10) DEFAULT 'A2_B1',
    seeded_from         VARCHAR(120) DEFAULT '',
    is_active           INTEGER DEFAULT 1,
    created_at          DATETIME
)
"""
DDL_SCENARIOS_IDX_CODE = (
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_tache2_scenarios_code "
    "ON tache2_scenarios(code)"
)


def _col_names(cur, table: str) -> list[str]:
    cur.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cur.fetchall()]


def forward(conn: sqlite3.Connection) -> int:
    cur = conn.cursor()
    cur.execute(DDL_SCENARIOS)
    cur.execute(DDL_SCENARIOS_IDX_CODE)

    # Add the FK column on conversations (only if the table exists —
    # F-048 creates it). Nullable: tache_1 conversations have no
    # scenario.
    conv_cols = _col_names(cur, "conversations")
    if conv_cols and "scenario_id" not in conv_cols:
        cur.execute(
            "ALTER TABLE conversations ADD COLUMN scenario_id INTEGER "
            "REFERENCES tache2_scenarios(id)"
        )
        print("Added column conversations.scenario_id")
    elif conv_cols:
        print("conversations.scenario_id already present.")
    else:
        print("conversations table not found; run add_conversation_tables first.")
        return 1

    conn.commit()
    cur.execute("SELECT COUNT(*) FROM tache2_scenarios")
    print(f"tache2_scenarios present ({cur.fetchone()[0]} rows).")
    return 0


def rollback(conn: sqlite3.Connection, force: bool = False) -> int:
    cur = conn.cursor()

    # 1. Drop the FK column on conversations.
    conv_cols = _col_names(cur, "conversations")
    if conv_cols and "scenario_id" in conv_cols:
        try:
            cur.execute("ALTER TABLE conversations DROP COLUMN scenario_id")
            conn.commit()
            print("Dropped column conversations.scenario_id (native).")
        except sqlite3.OperationalError as exc:
            print(f"Native DROP COLUMN unavailable ({exc}); rebuilding conversations.")
            preserved = [c for c in conv_cols if c != "scenario_id"]
            col_list = ", ".join(preserved)
            cur.execute("BEGIN")
            try:
                cur.execute(
                    f"CREATE TABLE conversations_new AS SELECT {col_list} FROM conversations"
                )
                cur.execute("DROP TABLE conversations")
                cur.execute("ALTER TABLE conversations_new RENAME TO conversations")
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    # 2. Drop the scenario table.
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='tache2_scenarios'"
    )
    if not cur.fetchone():
        print("tache2_scenarios not present; nothing to drop.")
        return 0

    cur.execute("SELECT COUNT(*) FROM tache2_scenarios")
    rows = cur.fetchone()[0]
    if rows and not force:
        print(
            f"Refusing to drop tache2_scenarios — {rows} row(s) present. "
            "Re-run with --force to discard (you'll need to re-seed from Yarden docs)."
        )
        return 2

    cur.execute("DROP TABLE tache2_scenarios")
    conn.commit()
    print("Dropped tache2_scenarios.")
    return 0


def main(argv: list[str]) -> int:
    if not DB_PATH.exists():
        print(f"DB not found at {DB_PATH}. Skipping.")
        return 0

    args = argv[1:]
    do_rollback = any(a in ("--rollback", "--reverse", "--down") for a in args)
    force = "--force" in args

    conn = sqlite3.connect(str(DB_PATH))
    try:
        return rollback(conn, force=force) if do_rollback else forward(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
