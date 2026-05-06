"""F-224 — writing prompts v1 pack schema

Adds 5 new canonical fields to ``writing_prompts`` to support the v1
content pack (commit-resident at ``scripts/seed_data/writing_prompts_seed.py``):

  - tache_level (INTEGER NOT NULL)  — TCF Tâche 1 / 2 / 3 partitioning
  - title_fr    (VARCHAR(120) NOT NULL) — short FR title for picker UX
  - prompt_fr   (TEXT NOT NULL)      — full FR prompt body (canonical)
  - prompt_en   (TEXT NOT NULL)      — full EN prompt body (i18n parallel)
  - topic_tag   (VARCHAR(40) NOT NULL) — short topic slug for filtering

Plus 2 CHECK constraints:
  - ck_writing_prompts_tache_level: tache_level IN (1, 2, 3)
  - ck_writing_prompts_topic_tag:   topic_tag IN (8 canonical topic slugs)

Legacy columns retained for backward-compat:
  - level, theme, prompt_text, prompt_type, time_limit_minutes
The seeder auto-populates them from the new fields at insert time
(see ``scripts/seed_writing_prompts.py`` for the topic_tag→theme +
tache_level→prompt_type mapping rules). Existing endpoints
(/api/writing/prompts, /api/writing/submit, writing_analysis.py)
keep reading the legacy columns unchanged.

Pre-condition (destructive):
  TRUNCATE writing_prompts RESTART IDENTITY CASCADE.
  - Local: clears the 18 placeholder dev prompts from
    ``scripts/seed_writing_prompts.py``'s pre-v1 era. Per the
    2026-05-06 lock-in, "retire all 18 without review" — they
    predate the LeMethodic positioning shift and 4 of them are
    off-audience C1.
  - Production: 0 rows currently, so this is a no-op there.
  - CASCADE: writing_submissions FK-references writing_prompts.id;
    both tables are empty in production, and local has no real
    submissions either. Safe.

Downgrade path: drops the CHECK constraints + the 5 new columns.
Does NOT restore the 18 retired rows (intentional — they're
per-spec retired without review).

Revision ID: f4d5e6c7b8a9
Revises: f3a4b5c6d7e8
Create Date: 2026-05-06 (F-224 v1-pack BE-side schema, in tandem
with retiring the hardcoded 18-prompt seeder content).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f4d5e6c7b8a9"
down_revision: Union[str, None] = "f3a4b5c6d7e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TOPIC_TAG_DOMAIN = (
    "('travel', 'work', 'family', 'education', 'health', "
    "'technology', 'environment', 'society')"
)


def upgrade() -> None:
    # Step 1: Wipe existing rows (no prod data; local 18 are retired
    # per F-224 v1-pack lock-in 2026-05-06).
    op.execute("TRUNCATE TABLE writing_prompts RESTART IDENTITY CASCADE")

    # Step 2: 5 new columns NOT NULL — table is empty post-truncate so
    # NOT NULL is satisfied trivially.
    op.add_column(
        "writing_prompts",
        sa.Column("tache_level", sa.Integer(), nullable=False),
    )
    op.add_column(
        "writing_prompts",
        sa.Column("title_fr", sa.String(length=120), nullable=False),
    )
    op.add_column(
        "writing_prompts",
        sa.Column("prompt_fr", sa.Text(), nullable=False),
    )
    op.add_column(
        "writing_prompts",
        sa.Column("prompt_en", sa.Text(), nullable=False),
    )
    op.add_column(
        "writing_prompts",
        sa.Column("topic_tag", sa.String(length=40), nullable=False),
    )

    # Step 3: domain CHECK constraints.
    op.create_check_constraint(
        "ck_writing_prompts_tache_level",
        "writing_prompts",
        "tache_level IN (1, 2, 3)",
    )
    op.create_check_constraint(
        "ck_writing_prompts_topic_tag",
        "writing_prompts",
        f"topic_tag IN {_TOPIC_TAG_DOMAIN}",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_writing_prompts_topic_tag",
        "writing_prompts",
        type_="check",
    )
    op.drop_constraint(
        "ck_writing_prompts_tache_level",
        "writing_prompts",
        type_="check",
    )
    op.drop_column("writing_prompts", "topic_tag")
    op.drop_column("writing_prompts", "prompt_en")
    op.drop_column("writing_prompts", "prompt_fr")
    op.drop_column("writing_prompts", "title_fr")
    op.drop_column("writing_prompts", "tache_level")
