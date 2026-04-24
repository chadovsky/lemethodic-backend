"""One-shot migration: create F-048 conversation tables.

Forward: creates ``conversations`` and ``conversation_turns`` tables with
their indexes. Idempotent — re-runs are safe.

Reverse: drops both tables. Since conversations are the ONLY users of
these tables (no other FK points at them), the drop is clean. If any
conversations exist when rollback runs, the script aborts unless
``--force`` is passed — this is Chadi's safety net against accidental
loss of in-flight data.

Usage from project root:
    python -m scripts.add_conversation_tables              # forward
    python -m scripts.add_conversation_tables --rollback   # reverse (safe if empty)
    python -m scripts.add_conversation_tables --rollback --force  # drops with data
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "tcf_oral.db"


DDL_CONVERSATIONS = """
CREATE TABLE IF NOT EXISTS conversations (
    id            VARCHAR(36) PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(id),
    tache_mode    VARCHAR(20) NOT NULL,
    topic_id      INTEGER REFERENCES test_topics(id),
    target_level  VARCHAR(10) DEFAULT 'B2',
    ui_language   VARCHAR(5) DEFAULT 'en',
    exam_profile  VARCHAR(50) DEFAULT 'tcf_canada',
    status        VARCHAR(20) DEFAULT 'in_progress',
    recording_id  INTEGER REFERENCES recordings(id),
    started_at    DATETIME,
    completed_at  DATETIME
)
"""

DDL_CONVERSATIONS_IDX_USER = (
    "CREATE INDEX IF NOT EXISTS ix_conversations_user_id ON conversations(user_id)"
)
DDL_CONVERSATIONS_IDX_STATUS = (
    "CREATE INDEX IF NOT EXISTS ix_conversations_status ON conversations(status)"
)

DDL_TURNS = """
CREATE TABLE IF NOT EXISTS conversation_turns (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id VARCHAR(36) NOT NULL REFERENCES conversations(id),
    turn_number     INTEGER NOT NULL,
    speaker         VARCHAR(20) NOT NULL,
    text            TEXT DEFAULT '',
    audio_url       VARCHAR(500),
    stt_confidence  REAL,
    word_count      INTEGER DEFAULT 0,
    fluency         TEXT DEFAULT '',
    created_at      DATETIME
)
"""

DDL_TURNS_IDX_CONV = (
    "CREATE INDEX IF NOT EXISTS ix_conversation_turns_conversation_id "
    "ON conversation_turns(conversation_id)"
)


def forward(conn: sqlite3.Connection) -> int:
    cur = conn.cursor()
    for stmt in (
        DDL_CONVERSATIONS,
        DDL_CONVERSATIONS_IDX_USER,
        DDL_CONVERSATIONS_IDX_STATUS,
        DDL_TURNS,
        DDL_TURNS_IDX_CONV,
    ):
        cur.execute(stmt)
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM conversations")
    conv_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM conversation_turns")
    turn_count = cur.fetchone()[0]
    print(
        f"Tables present: conversations ({conv_count} rows), "
        f"conversation_turns ({turn_count} rows)."
    )
    return 0


def rollback(conn: sqlite3.Connection, force: bool = False) -> int:
    cur = conn.cursor()

    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name IN "
        "('conversations','conversation_turns')"
    )
    existing = {row[0] for row in cur.fetchall()}
    if not existing:
        print("No conversation tables to drop. Nothing to roll back.")
        return 0

    if "conversations" in existing:
        cur.execute("SELECT COUNT(*) FROM conversations")
        rows = cur.fetchone()[0]
        if rows and not force:
            print(
                f"Refusing to drop conversations — {rows} row(s) present. "
                "Re-run with --force if you really want to discard them."
            )
            return 2

    # Drop child first so the FK reference is gone before the parent.
    cur.execute("DROP TABLE IF EXISTS conversation_turns")
    cur.execute("DROP TABLE IF EXISTS conversations")
    conn.commit()
    print("Dropped conversation_turns + conversations.")
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
