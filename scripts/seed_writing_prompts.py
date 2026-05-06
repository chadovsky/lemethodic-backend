"""F-224 — seed writing prompts for the /writing track.

v2 (2026-05-06): retired the 18-prompt hardcoded content per Chadi's
"retire all 18 without review" lock-in. Imports the v1 pack from
`scripts/seed_data/writing_prompts_seed.py` (14 prompts authored fresh
to TCF Canada Tâche 1/2/3 specs, FR/EN parallel rendering).

Re-runnable. Idempotent: matches existing rows by `(tache_level, title_fr)`
and skips duplicates.

Run locally after `alembic upgrade head`:

    docker-compose up -d
    alembic upgrade head
    python -m scripts.seed_writing_prompts

Production seeding: Chadi runs the same command against the prod DB
(same pattern as `seed_b1_b2_path.py` + `ingest_b1_b2_cluster_content.py`).

History:
  - v1 (pre-rebrand): root-level `seed_writing_prompts.py`, ASCII-stripped
    French. Removed 2026-05-04 (commit 3ac274c).
  - v1.5 (2026-05-04): relocated to `scripts/seed_writing_prompts.py`,
    18 hardcoded prompts (7 B1 + 7 B2 + 4 C1), accents normalized.
  - v2 (this file, 2026-05-06): imports `WRITING_PROMPTS_SEED` from
    `scripts/seed_data/writing_prompts_seed.py`. The 18 hardcoded
    prompts are retired wholesale per F-224 v1-pack lock-in. Migration
    `f4d5e6c7b8a9` TRUNCATEs the table before adding the new columns.
"""
from __future__ import annotations

import sys

from sqlalchemy import text

from app.database import SessionLocal
# Import models.User first so SQLAlchemy can resolve WritingSubmission's
# user relationship at mapper-configuration time. Side-effect import; the
# `User` symbol itself is unused here but the module load registers User
# in the declarative base.
from app.models.models import User as _User  # noqa: F401
from app.models.writing import WritingPrompt
from scripts.seed_data.writing_prompts_seed import WRITING_PROMPTS_SEED


# ── Auto-backfill mappings for legacy columns ──────────────────────


# topic_tag (canonical, lowercase EN slug) → theme (legacy column,
# FR-capitalized human label). Existing endpoints + any FE consumer
# of `theme` keeps reading the FR label unchanged.
_TOPIC_TO_THEME: dict[str, str] = {
    "travel":      "Voyages",
    "work":        "Travail",
    "family":      "Famille",
    "education":   "Éducation",
    "health":      "Santé",
    "technology":  "Technologie",
    "environment": "Environnement",
    "society":     "Société",
}

# tache_level (1/2/3) → prompt_type (legacy column, classifier slug).
# Mapping rule:
#   Tâche 1 = personal message  → "formal_letter"
#   Tâche 2 = account/article   → "essay"
#   Tâche 3 = argumentative w/ 2 documents → "argumentative"
_TACHE_TO_TYPE: dict[int, str] = {
    1: "formal_letter",
    2: "essay",
    3: "argumentative",
}


# ── Seed loader ────────────────────────────────────────────────────


def seed_from_data(prompts: list[dict]) -> tuple[int, int]:
    """Insert WritingPrompt rows from v1-pack dicts. Returns (added, skipped).

    Idempotent: skips when (tache_level, title_fr) tuple already exists.
    """
    db = SessionLocal()
    try:
        added = 0
        skipped = 0
        for p in prompts:
            existing = (
                db.query(WritingPrompt)
                .filter_by(
                    tache_level=p["tache_level"],
                    title_fr=p["title_fr"],
                )
                .first()
            )
            if existing is not None:
                skipped += 1
                continue
            db.add(WritingPrompt(
                # Canonical v1 pack fields:
                tache_level = p["tache_level"],
                title_fr    = p["title_fr"],
                prompt_fr   = p["prompt_fr"],
                prompt_en   = p["prompt_en"],
                topic_tag   = p["topic_tag"],
                min_words   = p["min_words"],
                max_words   = p["max_words"],

                # Legacy backfill (auto-derived):
                level              = p["target_level"],
                theme              = _TOPIC_TO_THEME[p["topic_tag"]],
                prompt_text        = p["prompt_fr"],
                prompt_type        = _TACHE_TO_TYPE[p["tache_level"]],
                time_limit_minutes = p["time_limit_min"],
                is_active          = 1,
            ))
            added += 1
        db.commit()
        return added, skipped
    finally:
        db.close()


# ── Verification print ─────────────────────────────────────────────


def print_verification() -> None:
    """Run the verification query and print counts.

    Equivalent to:
      SELECT COUNT(*), tache_level, level
      FROM writing_prompts
      GROUP BY tache_level, level
      ORDER BY tache_level, level;

    Expected output for v1 pack:
      (1, B1) → 6
      (2, B1) → 4
      (2, B2) → 1
      (3, B2) → 3
      Total: 14
    """
    db = SessionLocal()
    try:
        rows = db.execute(text(
            "SELECT COUNT(*), tache_level, level "
            "FROM writing_prompts "
            "GROUP BY tache_level, level "
            "ORDER BY tache_level, level"
        )).all()
        total = db.query(WritingPrompt).count()

        print()
        print(f"writing_prompts row distribution (total: {total}):")
        for count, tache, lvl in rows:
            print(f"  ({tache}, {lvl}) → {count}")
    finally:
        db.close()


# ── Entrypoint ─────────────────────────────────────────────────────


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    added, skipped = seed_from_data(WRITING_PROMPTS_SEED)
    print(f"writing prompts: +{added} added, {skipped} unchanged.")
    print_verification()
    return 0


if __name__ == "__main__":
    sys.exit(main())
