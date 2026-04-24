"""F-053 — create the Le Raccourci tables: lessons, quiz questions,
per-user progress.

Forward creates all three tables + indexes; idempotent re-run.
Reverse drops them (with a safety refusal when any user progress rows
are present, matching the pattern from add_conversation_tables).

Usage from project root:
    python -m scripts.add_raccourci_tables              # forward
    python -m scripts.add_raccourci_tables --rollback   # reverse (safe if empty)
    python -m scripts.add_raccourci_tables --rollback --force
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "tcf_oral.db"

DDL_LESSONS = """
CREATE TABLE IF NOT EXISTS raccourci_lessons (
    id                           INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_number                INTEGER UNIQUE NOT NULL,
    code                         VARCHAR(64) UNIQUE NOT NULL,
    title_fr                     VARCHAR(200) DEFAULT '',
    title_en                     VARCHAR(200) DEFAULT '',
    title_es                     VARCHAR(200) DEFAULT '',
    short_description_fr         TEXT DEFAULT '',
    short_description_en         TEXT DEFAULT '',
    short_description_es         TEXT DEFAULT '',
    detailed_content_fr          TEXT DEFAULT '',
    detailed_content_en          TEXT DEFAULT '',
    detailed_content_es          TEXT,
    prerequisite_lesson_number   INTEGER,
    estimated_duration_minutes   INTEGER DEFAULT 15,
    is_active                    INTEGER DEFAULT 1,
    created_at                   DATETIME
)
"""
DDL_LESSONS_IDX_NUM = "CREATE UNIQUE INDEX IF NOT EXISTS ix_raccourci_lessons_number ON raccourci_lessons(lesson_number)"
DDL_LESSONS_IDX_CODE = "CREATE UNIQUE INDEX IF NOT EXISTS ix_raccourci_lessons_code ON raccourci_lessons(code)"

DDL_QUESTIONS = """
CREATE TABLE IF NOT EXISTS raccourci_quiz_questions (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id               INTEGER NOT NULL REFERENCES raccourci_lessons(id),
    question_number         INTEGER NOT NULL,
    question_type           VARCHAR(32) NOT NULL,
    question_fr             TEXT DEFAULT '',
    question_en             TEXT DEFAULT '',
    question_es             TEXT DEFAULT '',
    correct_answer          TEXT DEFAULT '',
    accepted_alternatives   TEXT DEFAULT '[]',
    explanation_fr          TEXT DEFAULT '',
    explanation_en          TEXT DEFAULT '',
    explanation_es          TEXT DEFAULT '',
    options                 TEXT DEFAULT '[]'
)
"""
DDL_QUESTIONS_IDX = "CREATE INDEX IF NOT EXISTS ix_raccourci_questions_lesson ON raccourci_quiz_questions(lesson_id)"

DDL_PROGRESS = """
CREATE TABLE IF NOT EXISTS user_raccourci_progress (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id           INTEGER NOT NULL REFERENCES users(id),
    lesson_id         INTEGER NOT NULL REFERENCES raccourci_lessons(id),
    status            VARCHAR(20) DEFAULT 'locked',
    quiz_attempts     INTEGER DEFAULT 0,
    quiz_best_score   INTEGER DEFAULT 0,
    completed_at      DATETIME,
    unlocked_at       DATETIME,
    updated_at        DATETIME,
    UNIQUE(user_id, lesson_id)
)
"""
DDL_PROGRESS_IDX_USER = "CREATE INDEX IF NOT EXISTS ix_user_raccourci_progress_user ON user_raccourci_progress(user_id)"
DDL_PROGRESS_IDX_LESSON = "CREATE INDEX IF NOT EXISTS ix_user_raccourci_progress_lesson ON user_raccourci_progress(lesson_id)"


def forward(conn: sqlite3.Connection) -> int:
    cur = conn.cursor()
    for stmt in (
        DDL_LESSONS, DDL_LESSONS_IDX_NUM, DDL_LESSONS_IDX_CODE,
        DDL_QUESTIONS, DDL_QUESTIONS_IDX,
        DDL_PROGRESS, DDL_PROGRESS_IDX_USER, DDL_PROGRESS_IDX_LESSON,
    ):
        cur.execute(stmt)
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM raccourci_lessons")
    lessons = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM raccourci_quiz_questions")
    qs = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM user_raccourci_progress")
    progress = cur.fetchone()[0]
    print(
        f"Tables present — lessons={lessons} questions={qs} progress={progress}."
    )
    return 0


def rollback(conn: sqlite3.Connection, force: bool = False) -> int:
    cur = conn.cursor()
    # Refuse when user progress is present unless --force.
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='user_raccourci_progress'"
    )
    if cur.fetchone():
        cur.execute("SELECT COUNT(*) FROM user_raccourci_progress")
        rows = cur.fetchone()[0]
        if rows and not force:
            print(
                f"Refusing to drop raccourci tables — {rows} progress row(s) present. "
                "Re-run with --force to discard."
            )
            return 2

    # Drop in FK order: progress -> questions -> lessons.
    cur.execute("DROP TABLE IF EXISTS user_raccourci_progress")
    cur.execute("DROP TABLE IF EXISTS raccourci_quiz_questions")
    cur.execute("DROP TABLE IF EXISTS raccourci_lessons")
    conn.commit()
    print("Dropped raccourci tables (progress, questions, lessons).")
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
