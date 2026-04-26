"""
F-087 — Seed L'École 27-lesson curriculum.

Replaces the existing 16-lesson seed with the locked 27-lesson curriculum
from the L'École Curriculum Spec Lock (April 26, 2026).

Phase 1 — Fondations (lessons 1-16): the click-producing sequence.
Phase 2 — Approfondissement (lessons 17-27): post-click polish.

Voix passive removed from sequence; demoted to module library as
voix_passive_calque (severity 3) — separate module-authoring ticket,
not part of F-087.

Migration handling:
- Wipes user_ecole_progress before reseed (per Q1.2 confirmed decision —
  0 completions, 1 quiz attempt at decision time, no real user investment).
- Updates remediation_modules.ecole_lesson_id for gerondif_confusion:
  16 → 22 (gérondif moved from Phase 1 lesson 16 in old curriculum to
  Phase 2 lesson 22 in new curriculum).
- Adds `phase` and `subline_en` columns to ecole_lessons via ALTER TABLE
  if not present.

Run from tcf-oral-tool/tcf-oral-tool/ root:
    python -m scripts.seed_ecole_curriculum
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

# ────────────────────────────────────────────────────────────────────────────
# Curriculum data — 27 lessons, locked per L'École Spec (April 26, 2026)
# ────────────────────────────────────────────────────────────────────────────

LESSONS = [
    # Phase 1 — Fondations (1-16)
    {
        "lesson_number": 1,
        "code": "articles_definis_indefinis",
        "title_fr": "Articles définis et indéfinis",
        "title_en": "Definite and indefinite articles",
        "subline_en": "Coffee can't stand alone here. It needs an article. Don't ask why.",
        "phase": 1,
    },
    {
        "lesson_number": 2,
        "code": "articles_partitifs",
        "title_fr": "Articles partitifs",
        "title_en": "Partitive articles",
        "subline_en": "English drops \"some\" from sentences. French puts it back. Every time.",
        "phase": 1,
    },
    {
        "lesson_number": 3,
        "code": "genre_nombre_nom",
        "title_fr": "Genre et nombre du nom",
        "title_en": "Gender and number of nouns",
        "subline_en": "Tables are feminine, books masculine. We didn't decide. Neither will you.",
        "phase": 1,
    },
    {
        "lesson_number": 4,
        "code": "conjugaisons_fondamentales",
        "title_fr": "Conjugaisons fondamentales",
        "title_en": "Foundational conjugations",
        "subline_en": "You don't be hungry. You have hunger. Conjugate accordingly.",
        "phase": 1,
    },
    {
        "lesson_number": 5,
        "code": "futur_simple_conditionnel",
        "title_fr": "Futur simple et conditionnel",
        "title_en": "Future and conditional",
        "subline_en": "\"Would\" hides three different tenses. Pick wrong, sound foreign.",
        "phase": 1,
    },
    {
        "lesson_number": 6,
        "code": "subjonctif_present",
        "title_fr": "Subjonctif présent",
        "title_en": "Present subjunctive",
        "subline_en": "Eight triggers do the work. The rest is just learned panic.",
        "phase": 1,
    },
    {
        "lesson_number": 7,
        "code": "prepositions_lieu_temps",
        "title_fr": "Prépositions de lieu et de temps",
        "title_en": "Prepositions of place and time",
        "subline_en": "Forget the English map. À, de, en — that's mostly it. Mostly.",
        "phase": 1,
    },
    {
        "lesson_number": 8,
        "code": "verbes_regime_prepositionnel",
        "title_fr": "Verbes à régime prépositionnel (à / de)",
        "title_en": "Verbs with prepositional complements (à / de)",
        "subline_en": "\"Wait for,\" \"look at,\" \"listen to\" — drop the prepositions and start over.",
        "phase": 1,
    },
    {
        "lesson_number": 9,
        "code": "phrase_interrogative",
        "title_fr": "La phrase interrogative",
        "title_en": "The interrogative sentence",
        "subline_en": "Three ways to ask a question. Two of them sound like 1950.",
        "phase": 1,
    },
    {
        "lesson_number": 10,
        "code": "pronoms_personnels",
        "title_fr": "Pronoms personnels (sujet, COD, COI)",
        "title_en": "Personal pronouns (subject, direct, indirect)",
        "subline_en": "English keeps pronouns at the end. We put them before the verb. Always.",
        "phase": 1,
    },
    {
        "lesson_number": 11,
        "code": "pronoms_y_en",
        "title_fr": "Pronoms y et en",
        "title_en": "The pronouns y and en",
        "subline_en": "Two pronouns English doesn't have. You'll wonder how you lived without them.",
        "phase": 1,
    },
    {
        "lesson_number": 12,
        "code": "pronoms_relatifs",
        "title_fr": "Pronoms relatifs (qui, que, dont, où)",
        "title_en": "Relative pronouns (qui, que, dont, où)",
        "subline_en": "You can't drop \"that\" here. The French don't believe in shortcuts.",
        "phase": 1,
    },
    {
        "lesson_number": 13,
        "code": "adjectifs",
        "title_fr": "Adjectifs (accord, place, sens)",
        "title_en": "Adjectives (agreement, position, meaning)",
        "subline_en": "An \"ancien ami\" is an ex-friend. An \"ami ancien\" is just old. Position is everything.",
        "phase": 1,
    },
    {
        "lesson_number": 14,
        "code": "adverbes",
        "title_fr": "Adverbes",
        "title_en": "Adverbs",
        "subline_en": "\"-ly\" becomes \"-ment.\" Until it doesn't. Of course.",
        "phase": 1,
    },
    {
        "lesson_number": 15,
        "code": "discours_indirect",
        "title_fr": "Discours indirect (présent et passé)",
        "title_en": "Reported speech (present and past)",
        "subline_en": "\"He said he was tired.\" Backshift the tense or sound like Google Translate.",
        "phase": 1,
    },
    {
        "lesson_number": 16,
        "code": "concordance_temps_hypothese",
        "title_fr": "Concordance des temps et hypothèse (si)",
        "title_en": "Tense agreement and hypothesis (si)",
        "subline_en": "Three \"if\" patterns. Mix them and the sentence dies on the page.",
        "phase": 1,
    },
    # Phase 2 — Approfondissement (17-27)
    {
        "lesson_number": 17,
        "code": "verbes_pronominaux",
        "title_fr": "Verbes pronominaux",
        "title_en": "Pronominal verbs",
        "subline_en": "\"I wash myself.\" Yes, even in the shower. Especially in the shower.",
        "phase": 2,
    },
    {
        "lesson_number": 18,
        "code": "faire_causatif",
        "title_fr": "Faire causatif",
        "title_en": "Causative faire",
        "subline_en": "When you didn't do it, you made it done. One verb. That's it.",
        "phase": 2,
    },
    {
        "lesson_number": 19,
        "code": "mise_en_relief",
        "title_fr": "Mise en relief",
        "title_en": "Emphatic constructions",
        "subline_en": "\"What I love is the silence.\" The sentence pattern that ends your A2 era.",
        "phase": 2,
    },
    {
        "lesson_number": 20,
        "code": "tournures_impersonnelles",
        "title_fr": "Tournures impersonnelles",
        "title_en": "Impersonal constructions",
        "subline_en": "When \"il\" does the work, the sentence elevates. Yours probably needs some.",
        "phase": 2,
    },
    {
        "lesson_number": 21,
        "code": "comparatifs_superlatifs",
        "title_fr": "Comparatifs et superlatifs (irréguliers)",
        "title_en": "Comparatives and superlatives (irregulars)",
        "subline_en": "\"Better\" splits into two words here. Pick the wrong one and we'll know.",
        "phase": 2,
    },
    {
        "lesson_number": 22,
        "code": "gerondif_participe_present",
        "title_fr": "Gérondif et participe présent",
        "title_en": "Gerund and present participle",
        "subline_en": "Three traps wearing the same \"-ing.\" We disarm them one by one.",
        "phase": 2,
    },
    {
        "lesson_number": 23,
        "code": "presentatifs",
        "title_fr": "Présentatifs (c'est / il est / il y a / voici)",
        "title_en": "Presentatives (c'est / il est / il y a / voici)",
        "subline_en": "\"He's a doctor\" — no article. He's just doctor. That's the whole sentence.",
        "phase": 2,
    },
    {
        "lesson_number": 24,
        "code": "connecteurs_logiques",
        "title_fr": "Connecteurs logiques",
        "title_en": "Logical connectors",
        "subline_en": "Stop saying \"alors.\" We can hear the English from here.",
        "phase": 2,
    },
    {
        "lesson_number": 25,
        "code": "marqueurs_temporels",
        "title_fr": "Marqueurs temporels",
        "title_en": "Temporal markers",
        "subline_en": "Six French words wedged into four English slots. Map them wrong, we hear it.",
        "phase": 2,
    },
    {
        "lesson_number": 26,
        "code": "registre_oral",
        "title_fr": "Registre oral (négation, particules, élisions)",
        "title_en": "Oral register (negation, particles, elisions)",
        "subline_en": "Real French drops the \"ne.\" Your textbook lied by omission.",
        "phase": 2,
    },
    {
        "lesson_number": 27,
        "code": "nominalisation",
        "title_fr": "Nominalisation",
        "title_en": "Nominalization",
        "subline_en": "Why say \"when prices rise\" when \"the rise\" will do? French is lazy. Beautifully lazy.",
        "phase": 2,
    },
]

# ────────────────────────────────────────────────────────────────────────────
# Migration + seed logic
# ────────────────────────────────────────────────────────────────────────────

DB_PATH = Path(__file__).parent.parent / "tcf_oral.db"


def ensure_schema_columns(conn: sqlite3.Connection) -> None:
    """Add `phase` and `subline_en` columns to ecole_lessons if missing.
    Idempotent — safe to run multiple times."""
    cursor = conn.execute("PRAGMA table_info(ecole_lessons)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    if "phase" not in existing_columns:
        conn.execute(
            "ALTER TABLE ecole_lessons ADD COLUMN phase INTEGER DEFAULT 1"
        )
        print("  Added column: ecole_lessons.phase")

    if "subline_en" not in existing_columns:
        conn.execute(
            "ALTER TABLE ecole_lessons ADD COLUMN subline_en TEXT DEFAULT NULL"
        )
        print("  Added column: ecole_lessons.subline_en")


def wipe_progress(conn: sqlite3.Connection) -> int:
    """Wipe user_ecole_progress per F-087 spec.
    Returns row count deleted for logging."""
    cursor = conn.execute("SELECT COUNT(*) FROM user_ecole_progress")
    count = cursor.fetchone()[0]
    conn.execute("DELETE FROM user_ecole_progress")
    return count


def reseed_lessons(conn: sqlite3.Connection) -> tuple[int, int]:
    """Wipe existing lesson rows and seed the locked 27.
    Returns (deleted, inserted) for verification logging."""
    cursor = conn.execute("SELECT COUNT(*) FROM ecole_lessons")
    deleted = cursor.fetchone()[0]
    conn.execute("DELETE FROM ecole_lessons")

    now = datetime.now(timezone.utc).isoformat()
    inserted = 0
    for lesson in LESSONS:
        # Linear prerequisite chain: 1 has none, 2 → 1, 3 → 2, etc.
        prerequisite = (
            lesson["lesson_number"] - 1 if lesson["lesson_number"] > 1 else None
        )
        conn.execute(
            """
            INSERT INTO ecole_lessons (
                lesson_number, code, title_fr, title_en, subline_en,
                phase, estimated_duration_minutes, prerequisite_lesson_number,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lesson["lesson_number"],
                lesson["code"],
                lesson["title_fr"],
                lesson["title_en"],
                lesson["subline_en"],
                lesson["phase"],
                15,  # default 15 min — refine per-lesson later
                prerequisite,
                now,
            ),
        )
        inserted += 1
    return deleted, inserted


def update_module_lesson_links(conn: sqlite3.Connection) -> int:
    """Update remediation_modules.ecole_lesson_id for gerondif_confusion.
    Old curriculum: gérondif was lesson 16.
    New curriculum: gérondif is lesson 22.
    Returns rows updated."""
    cursor = conn.execute(
        """
        UPDATE remediation_modules
        SET ecole_lesson_id = 22, updated_at = ?
        WHERE id = 'gerondif_confusion' AND ecole_lesson_id = 16
        """,
        (datetime.now(timezone.utc).isoformat(),),
    )
    return cursor.rowcount


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found at {DB_PATH}. "
            f"Run from tcf-oral-tool/tcf-oral-tool/ root."
        )

    print(f"Connecting to {DB_PATH}")
    conn = sqlite3.connect(str(DB_PATH))

    try:
        # try/finally for cleanup per F-080d.z verification harness rule
        print("\n[1/4] Ensuring schema columns...")
        ensure_schema_columns(conn)

        print("\n[2/4] Wiping user_ecole_progress (per F-087 spec)...")
        progress_wiped = wipe_progress(conn)
        print(f"  Deleted {progress_wiped} progress rows")

        print("\n[3/4] Reseeding ecole_lessons with 27-lesson curriculum...")
        deleted, inserted = reseed_lessons(conn)
        print(f"  Deleted {deleted} old lesson rows")
        print(f"  Inserted {inserted} new lesson rows")

        print("\n[4/4] Updating remediation_modules.ecole_lesson_id...")
        updated = update_module_lesson_links(conn)
        print(f"  Updated {updated} module row(s) (gerondif_confusion: 16 -> 22)")

        conn.commit()
        print("\nSeed complete. Committed.")

        # Verification queries
        print("\n--- Verification ---")
        cursor = conn.execute(
            "SELECT COUNT(*) FROM ecole_lessons WHERE phase = 1"
        )
        phase_1_count = cursor.fetchone()[0]
        cursor = conn.execute(
            "SELECT COUNT(*) FROM ecole_lessons WHERE phase = 2"
        )
        phase_2_count = cursor.fetchone()[0]
        cursor = conn.execute(
            "SELECT COUNT(*) FROM ecole_lessons WHERE subline_en IS NULL"
        )
        null_sublines = cursor.fetchone()[0]
        cursor = conn.execute(
            "SELECT id, ecole_lesson_id FROM remediation_modules WHERE id = 'gerondif_confusion'"
        )
        gerondif_row = cursor.fetchone()

        print(f"  Phase 1 lessons: {phase_1_count} (expected: 16)")
        print(f"  Phase 2 lessons: {phase_2_count} (expected: 11)")
        print(f"  Null sublines: {null_sublines} (expected: 0)")
        print(f"  gerondif_confusion -> ecole_lesson_id: {gerondif_row[1]} (expected: 22)")

        all_green = (
            phase_1_count == 16
            and phase_2_count == 11
            and null_sublines == 0
            and gerondif_row[1] == 22
        )
        if all_green:
            print("\nAll verification checks passed.")
        else:
            print("\nFAIL: One or more verification checks failed.")
            raise SystemExit(1)

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
