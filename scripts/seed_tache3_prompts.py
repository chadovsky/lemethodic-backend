"""F-051 — backfill every ``test_topics`` row with a placeholder Tâche 3
prompt + default difficulty.

The existing 84 seeded topics already phrase themselves as debate
questions (all end with "?"), so the FR prompt template just appends a
standard framing sentence that tells the candidate to defend a position
with concrete examples. EN / ES slots stay blank on purpose — the UI
falls back to the FR prompt until Chadi supplies real translations.

Placeholders everywhere. Every row written is tagged via the fact that
``tache_3_prompt_en`` and ``tache_3_prompt_es`` are empty; the seeder
prints a count of rows still needing translation so Chadi knows how far
the Day-7 copy swap has to go.

Idempotent: runs match by topic id; existing non-empty prompts are
preserved (don't stomp Chadi's manual edits on re-run).

    # CHADI: validate or replace every prompt below before Day 7.

Usage from project root:
    python -m scripts.seed_tache3_prompts
"""
from __future__ import annotations

import sys

from app.database import SessionLocal
from app.models.models import TestTopic


FR_FRAMING_SUFFIX = " Donnez votre opinion argumentée, avec des exemples concrets."

# CHADI: placeholder default; recategorize each row before Day 7.
DEFAULT_DIFFICULTY = "B1_B2"


def _fr_prompt_for(title: str) -> str:
    title = (title or "").strip()
    if not title:
        return ""
    # Titles already end with "?" — avoid doubling the punctuation.
    return f"{title}{FR_FRAMING_SUFFIX}"


def main() -> int:
    session = SessionLocal()
    try:
        rows = session.query(TestTopic).all()
        if not rows:
            print("No topics found. Run init_db / seed_topics first.")
            return 1

        filled_fr = 0
        preserved_fr = 0
        filled_difficulty = 0
        missing_en = 0
        missing_es = 0

        for topic in rows:
            # FR: placeholder fill only if empty. Preserves Chadi's hand edits.
            if not (topic.tache_3_prompt_fr or "").strip():
                topic.tache_3_prompt_fr = _fr_prompt_for(topic.title)
                filled_fr += 1
            else:
                preserved_fr += 1

            if not (topic.tache_3_difficulty or "").strip():
                topic.tache_3_difficulty = DEFAULT_DIFFICULTY
                filled_difficulty += 1

            if not (topic.tache_3_prompt_en or "").strip():
                missing_en += 1
            if not (topic.tache_3_prompt_es or "").strip():
                missing_es += 1

        session.commit()

        print(
            f"Tâche 3 placeholder seeding complete:\n"
            f"  total topics          : {len(rows)}\n"
            f"  FR prompts filled     : {filled_fr} (preserved {preserved_fr} non-empty)\n"
            f"  difficulty defaults   : {filled_difficulty} (default='{DEFAULT_DIFFICULTY}')\n"
            f"  EN prompts missing    : {missing_en}  # CHADI: translate before Day 7\n"
            f"  ES prompts missing    : {missing_es}  # CHADI: translate before Day 7"
        )
        return 0
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
