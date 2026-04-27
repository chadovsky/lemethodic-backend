# Archived during F-077 PostgreSQL migration. Schema change is now
# part of the initial Alembic migration. Kept for historical reference.
"""F-080a migration: create remediation_modules + session_detected_modules.

The remediation_modules table is the named library of L1-interference
modules that Claude's analysis engine tags sessions against (F-080b).
session_detected_modules links a completed recording (the existing
`recordings` table) to the modules detected in its session, with
is_primary flagging the dominant one for the diagnostic page.

Idempotent direct-sqlite3 pattern, same as scripts/add_turn_supersede_columns.py
from F-062.3. Safe to re-run; second run is a full no-op.

CHECK constraints:
- category restricted to the F-080 spec's closed list
- severity restricted to [1, 5]

Partial indexes target the hot-path queries: active-row lookups for the
seed/admin endpoints, and join-column lookups on the detection link table.

Run from project root:
    python -m scripts.add_remediation_modules
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "tcf_oral.db"

CREATE_MODULES_SQL = """
CREATE TABLE IF NOT EXISTS remediation_modules (
    id TEXT PRIMARY KEY,
    name_fr VARCHAR(200) NOT NULL,
    name_en VARCHAR(200) NOT NULL,
    category TEXT NOT NULL CHECK(category IN (
        'vocab_calque',
        'grammar_interference',
        'discourse_structure',
        'pronunciation',
        'register_mismatch',
        'word_order',
        'verb_aspect',
        'other'
    )),
    severity INTEGER NOT NULL CHECK(severity BETWEEN 1 AND 5),
    active INTEGER NOT NULL DEFAULT 1,
    L1_interference_description_fr TEXT NOT NULL,
    L1_interference_description_en TEXT NOT NULL,
    detection_criteria TEXT NOT NULL,
    examples TEXT NOT NULL,
    content_refs TEXT NOT NULL DEFAULT '[]',
    drill_ids TEXT NOT NULL DEFAULT '[]',
    prerequisite_module_ids TEXT NOT NULL DEFAULT '[]',
    ecole_lesson_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ecole_lesson_id) REFERENCES ecole_lessons(id)
)
"""

CREATE_SESSION_DETECTED_SQL = """
CREATE TABLE IF NOT EXISTS session_detected_modules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recording_id INTEGER NOT NULL,
    module_id TEXT NOT NULL,
    is_primary INTEGER NOT NULL DEFAULT 0,
    confidence_score REAL,
    supporting_quote TEXT,
    detected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (recording_id) REFERENCES recordings(id),
    FOREIGN KEY (module_id) REFERENCES remediation_modules(id)
)
"""

INDEXES_SQL = [
    # Active-module lookups (public GET /api/modules hits this on every call).
    """
    CREATE INDEX IF NOT EXISTS idx_remediation_modules_active
    ON remediation_modules(active) WHERE active = 1
    """,
    # Category-filter lookups (GET /api/modules?category=X).
    """
    CREATE INDEX IF NOT EXISTS idx_remediation_modules_category
    ON remediation_modules(category) WHERE active = 1
    """,
    # Per-recording detection lookups (diagnostic page hydration).
    """
    CREATE INDEX IF NOT EXISTS idx_sdm_recording
    ON session_detected_modules(recording_id)
    """,
    # F-080d recurring-module queries: "how many of my sessions hit module X".
    """
    CREATE INDEX IF NOT EXISTS idx_sdm_user_module
    ON session_detected_modules(module_id)
    """,
]


def main() -> int:
    if not DB_PATH.exists():
        print(f"DB not found at {DB_PATH}. Skipping.")
        return 0

    conn = sqlite3.connect(str(DB_PATH))
    try:
        cur = conn.cursor()

        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='remediation_modules'")
        modules_existed = cur.fetchone() is not None
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='session_detected_modules'")
        sdm_existed = cur.fetchone() is not None

        cur.execute(CREATE_MODULES_SQL)
        cur.execute(CREATE_SESSION_DETECTED_SQL)
        for sql in INDEXES_SQL:
            cur.execute(sql)

        conn.commit()

        created = []
        if not modules_existed:
            created.append("remediation_modules")
        if not sdm_existed:
            created.append("session_detected_modules")
        if created:
            print(f"Created tables: {', '.join(created)}.")
        else:
            print("F-080a tables already present. Nothing to do.")
        print("Indexes ensured: idx_remediation_modules_active, idx_remediation_modules_category, idx_sdm_recording, idx_sdm_user_module.")
        print("Run `python -m scripts.seed_remediation_modules` to populate modules from seeds/modules/*.json.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
