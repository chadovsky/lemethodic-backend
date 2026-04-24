"""Migration v3 — adds all missing columns."""
import sqlite3, os

DB_PATH = os.environ.get("DB_PATH", "tcf_oral.db")

MIGRATIONS = [
    ("test_topics", "theme", "ALTER TABLE test_topics ADD COLUMN theme VARCHAR(100) DEFAULT 'Société'"),
    ("test_topics", "sous_theme", "ALTER TABLE test_topics ADD COLUMN sous_theme VARCHAR(200) DEFAULT ''"),
    ("recordings", "target_level", "ALTER TABLE recordings ADD COLUMN target_level VARCHAR(10) DEFAULT ''"),
    ("recordings", "native_language", "ALTER TABLE recordings ADD COLUMN native_language VARCHAR(50) DEFAULT 'english'"),
    ("feedbacks", "detected_level", "ALTER TABLE feedbacks ADD COLUMN detected_level VARCHAR(10) DEFAULT ''"),
    ("feedbacks", "level_justification", "ALTER TABLE feedbacks ADD COLUMN level_justification TEXT DEFAULT ''"),
    ("feedbacks", "layer_content_score", "ALTER TABLE feedbacks ADD COLUMN layer_content_score FLOAT DEFAULT 0"),
    ("feedbacks", "layer_discourse_score", "ALTER TABLE feedbacks ADD COLUMN layer_discourse_score FLOAT DEFAULT 0"),
    ("feedbacks", "layer_sentence_score", "ALTER TABLE feedbacks ADD COLUMN layer_sentence_score FLOAT DEFAULT 0"),
    ("feedbacks", "layer_interference_score", "ALTER TABLE feedbacks ADD COLUMN layer_interference_score FLOAT DEFAULT 0"),
    ("feedbacks", "patterns_detected", "ALTER TABLE feedbacks ADD COLUMN patterns_detected TEXT DEFAULT ''"),
    ("feedbacks", "patterns_missing", "ALTER TABLE feedbacks ADD COLUMN patterns_missing TEXT DEFAULT ''"),
    ("feedbacks", "interferences_detected", "ALTER TABLE feedbacks ADD COLUMN interferences_detected TEXT DEFAULT ''"),
    ("feedbacks", "recommendations", "ALTER TABLE feedbacks ADD COLUMN recommendations TEXT DEFAULT ''"),
    ("feedbacks", "grammar_inventory", "ALTER TABLE feedbacks ADD COLUMN grammar_inventory TEXT DEFAULT ''"),
    ("feedbacks", "vocabulary_assessment", "ALTER TABLE feedbacks ADD COLUMN vocabulary_assessment TEXT DEFAULT ''"),
    ("feedbacks", "homework_targets", "ALTER TABLE feedbacks ADD COLUMN homework_targets TEXT DEFAULT ''"),
]

def column_exists(cur, table, col):
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == col for row in cur.fetchall())

def migrate():
    print(f"Migrating {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    n = 0
    for table, col, sql in MIGRATIONS:
        if not column_exists(cur, table, col):
            print(f"  + {table}.{col}")
            cur.execute(sql)
            n += 1
        else:
            print(f"  ✓ {table}.{col}")
    conn.commit()
    conn.close()
    print(f"Done — {n} column(s) added.")

if __name__ == "__main__":
    migrate()
