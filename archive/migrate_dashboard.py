# Dead code from pre-routers async scaffold. Archived during F-077
# PostgreSQL migration to prevent accidental Alembic Base.metadata
# pollution. 5-minute insurance against accidental import.
"""
DASHBOARD INTEGRATION GUIDE
============================
Run this file ONCE to add dashboard tables to your existing SQLite DB.

    cd C:\\Users\\pc\\Downloads\\tcf-oral-tool\\tcf-oral-tool
    py migrate_dashboard.py

Then follow the integration steps below.
"""

import sqlite3
import os

DB_PATH = os.getenv("DB_PATH", "tcf_oral.db")


def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print(f"[1/4] Migrating {DB_PATH}...")

    # ── Add columns to feedbacks ──
    new_columns = [
        ("couche1_contenu", "REAL DEFAULT 0"),
        ("couche2_discours", "REAL DEFAULT 0"),
        ("couche3_phrase", "REAL DEFAULT 0"),
        ("couche4_interferences", "REAL DEFAULT 0"),
        ("detected_niveau", "TEXT DEFAULT ''"),
        ("vocab_richesse", "TEXT DEFAULT ''"),
        ("vocab_registre", "TEXT DEFAULT ''"),
        ("interference_count", "INTEGER DEFAULT 0"),
        ("moules_detected_count", "INTEGER DEFAULT 0"),
        ("moules_expected_count", "INTEGER DEFAULT 0"),
    ]

    existing = {row[1] for row in cursor.execute("PRAGMA table_info(feedbacks)").fetchall()}

    for col_name, col_def in new_columns:
        if col_name not in existing:
            cursor.execute(f"ALTER TABLE feedbacks ADD COLUMN {col_name} {col_def}")
            print(f"   + feedbacks.{col_name}")
        else:
            print(f"   ~ feedbacks.{col_name} (already exists)")

    # ── Create grammar_snapshots ──
    print("[2/4] Creating grammar_snapshots...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS grammar_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feedback_id INTEGER NOT NULL REFERENCES feedbacks(id) ON DELETE CASCADE,
            grammar_point TEXT NOT NULL,
            status TEXT NOT NULL,
            example TEXT DEFAULT '',
            correction TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_grammar_feedback
        ON grammar_snapshots(feedback_id)
    """)

    # ── Create interference_logs ──
    print("[3/4] Creating interference_logs...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interference_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feedback_id INTEGER NOT NULL REFERENCES feedbacks(id) ON DELETE CASCADE,
            interference_type TEXT NOT NULL,
            source_text TEXT DEFAULT '',
            target_text TEXT DEFAULT '',
            explanation TEXT DEFAULT '',
            couche_tag TEXT DEFAULT 'C4',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_interference_feedback
        ON interference_logs(feedback_id)
    """)

    # ── Create moule_snapshots ──
    print("[4/4] Creating moule_snapshots...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS moule_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feedback_id INTEGER NOT NULL REFERENCES feedbacks(id) ON DELETE CASCADE,
            moule_name TEXT NOT NULL,
            detected BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_moule_feedback
        ON moule_snapshots(feedback_id)
    """)

    conn.commit()
    conn.close()
    print("\nMigration complete.")
    print("Next: follow the integration steps in this file.\n")


"""
═══════════════════════════════════════════════════
INTEGRATION STEPS (after running this migration)
═══════════════════════════════════════════════════

STEP 1 — Copy files into your project
──────────────────────────────────────
Copy these files into your project root:
  dashboard_models.py    → app/models/dashboard_models.py
  feedback_parser.py     → app/services/feedback_parser.py
  dashboard_api.py       → app/routers/dashboard.py

Then update imports in each file to match your structure:
  from app.models.dashboard_models import ...
  from app.services.feedback_parser import ...


STEP 2 — Update your Feedback model (app/models/models.py)
──────────────────────────────────────────────────────────
Add these columns to class Feedback:

    # 4-couche diagnostic
    couche1_contenu = Column(Float, default=0)
    couche2_discours = Column(Float, default=0)
    couche3_phrase = Column(Float, default=0)
    couche4_interferences = Column(Float, default=0)

    # Auto-detected level
    detected_niveau = Column(String(10), default="")

    # Vocabulary
    vocab_richesse = Column(String(50), default="")
    vocab_registre = Column(String(50), default="")

    # Dashboard aggregation counts
    interference_count = Column(Integer, default=0)
    moules_detected_count = Column(Integer, default=0)
    moules_expected_count = Column(Integer, default=0)

    # Relationships to detail tables
    grammar_snapshots = relationship("GrammarSnapshot", back_populates="feedback", cascade="all, delete-orphan")
    interference_logs = relationship("InterferenceLog", back_populates="feedback", cascade="all, delete-orphan")
    moule_snapshots = relationship("MouleSnapshot", back_populates="feedback", cascade="all, delete-orphan")


STEP 3 — Update your Claude prompt (app/services/analysis.py)
─────────────────────────────────────────────────────────────
Add this to your system prompt so Claude returns structured JSON.
See the full JSON schema in feedback_parser.py (line ~40).

Key addition to your prompt:

    "Return your analysis as a valid JSON object.
     Do not include any text outside the JSON.
     Follow this exact structure: { ... }"


STEP 4 — Hook the parser into your recording flow
─────────────────────────────────────────────────
In app/routers/recordings.py, after you save the Feedback:

    from app.services.feedback_parser import parse_and_store_feedback

    # After: feedback = Feedback(recording_id=..., analysis_text=..., ...)
    # After: db.add(feedback); db.commit(); db.refresh(feedback)

    # Parse structured data for dashboard
    try:
        llm_json = json.loads(raw_response)  # or however you parse Claude's response
        parse_and_store_feedback(db, feedback_id=feedback.id, llm_json=llm_json)
    except Exception as e:
        logger.warning(f"Dashboard parse failed: {e}")
        # Non-blocking — the session still works even if parsing fails


STEP 5 — Register the dashboard router (main.py)
────────────────────────────────────────────────
    from app.routers.dashboard import router as dashboard_router
    app.include_router(dashboard_router, prefix="/api/dashboard", tags=["dashboard"])


STEP 6 — Backfill existing sessions (one-time)
──────────────────────────────────────────────
If you have existing sessions with raw_llm_response stored,
run the backfill to populate dashboard tables retroactively:

    py -c "
    from app.database import SessionLocal
    from app.services.feedback_parser import backfill_from_raw_responses
    db = SessionLocal()
    count = backfill_from_raw_responses(db)
    print(f'Backfilled {count} sessions')
    db.close()
    "

Note: This only works if raw_llm_response contains parseable JSON.
If your current Claude responses are plain text, the backfill
will skip them and only new sessions will have dashboard data.


═══════════════════════════════════════════════════
API ENDPOINTS REFERENCE
═══════════════════════════════════════════════════

All endpoints require authentication (JWT cookie).
All return JSON.

GET /api/dashboard/overview
    → KPIs: current niveau, score delta, interference trend, streak
    → Used by: KPI strip at top of dashboard

GET /api/dashboard/score-history?limit=50
    → Per-session: date, score, niveau, 4 couches, theme, interferences
    → Used by: main chart (3 views: Score, 4 Couches, Interférences)

GET /api/dashboard/grammar-progression?last_n=12
    → Per grammar point: array of statuses over last N sessions
    → Used by: grammar mastery grid

GET /api/dashboard/moules-progression?last_n=5
    → Per moule: detection frequency over last N sessions
    → Used by: moules bar chart + "prochain objectif"

GET /api/dashboard/activity-heatmap?weeks=6
    → Daily session counts + best score, 6-week grid
    → Used by: activity heatmap

GET /api/dashboard/niveau-trajectory?target=B2
    → Niveau per session + estimated weeks to target
    → Used by: niveau trajectory chart + estimation card

GET /api/dashboard/interference-breakdown?last_n=10
    → Interference types ranked by frequency
    → Used by: optional drill-down view

"""


if __name__ == "__main__":
    migrate()
