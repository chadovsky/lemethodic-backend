"""P-220 — extended onboarding-questionnaire columns

Adds 7 columns to ``users`` and 1 column to ``user_path_enrollments`` to
back the rebuilt onboarding flow per LEMETHODIC-CURRICULUM v0.2 §8.3.
The existing 5 onboarding columns on ``users`` (target_level,
exam_profile, exam_date, goal, current_level) stay unchanged.

Mapping to §8.3 questions:

  Q5  strongest_skill              users
  Q6  weakest_skill                users
  Q7  hours_per_week               users
  Q8  topics_tested_on             users (JSONB array of TCF test-theme slugs)
  Q9  native_language              users (free text)
  Q10 prior_french_exam            users
  Q11 feedback_mode_preference     users
  Q3  persona (derived)            user_path_enrollments

Q1, Q2, Q3 (date), Q4 reuse existing columns. Q12 (reminder time) is
not asked in Phase 1 (filed as P-220.y).

topics_tested_on uses the standard CIEP/TCF test theme list (NOT the
27 vocabulary themes from P-202 — those are pedagogical taxonomy, not
exam-topic taxonomy):

  vie_quotidienne, societe, education, travail,
  loisirs_voyages, sante, environnement, culture_medias

The CHECK constraint enforces both shape (must be a JSON array) and
membership (every element must be one of the 8 slugs above).

`persona` lands on UserPathEnrollment (not on User) because persona is
intrinsically per-enrollment: it's derived from the active path's exam
date, and a user who later starts a different path gets a different
persona without rewriting the previous one. P-204's UserPathEnrollment
is the natural home.

Closed-enum columns get CHECK constraints (matches P-202's
ck_clusters_tache_application convention — plain VARCHAR + CHECK rather
than PG ENUM type, so adding values later is a one-line ALTER instead
of an enum-add migration). Each CHECK is `IS NULL OR IN (...)` so
existing rows (all NULL) pass.

Revision ID: b3a55c1e0001   ← placeholder; regenerate via
                              `alembic revision --autogenerate` before
                              applying if you want a real timestamp.
Revises: a8f3e2c4b5d1
Create Date: 2026-05-02

NOTE — SQLAlchemy model classes for these columns (User and
UserPathEnrollment in app/models/models.py) are NOT yet updated. They
land in the follow-up commit alongside this migration. Until then,
`alembic revision --autogenerate` will see drift — do not autogenerate
again until the model classes are added.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = "b3a55c1e0001"
down_revision: Union[str, None] = "a8f3e2c4b5d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users — 7 new columns ────────────────────────────────────────
    # Length picks: longest slug values are speaking_under_pressure (23)
    # for weakest_skill and more_than_10 (12) for hours_per_week. Bumped
    # to 32 / 20 for headroom.
    op.add_column("users", sa.Column("strongest_skill",          sa.String(length=20),  nullable=True))
    op.add_column("users", sa.Column("weakest_skill",            sa.String(length=32),  nullable=True))
    op.add_column("users", sa.Column("hours_per_week",           sa.String(length=20),  nullable=True))
    op.add_column("users", sa.Column("topics_tested_on",         JSONB(),               nullable=True))
    op.add_column("users", sa.Column("native_language",          sa.String(length=40),  nullable=True))
    op.add_column("users", sa.Column("prior_french_exam",        sa.String(length=20),  nullable=True))
    op.add_column("users", sa.Column("feedback_mode_preference", sa.String(length=10),  nullable=True))

    # ── user_path_enrollments — 1 new column (persona) ───────────────
    op.add_column(
        "user_path_enrollments",
        sa.Column("persona", sa.String(length=20), nullable=True),
    )

    # ── CHECK constraints (NULL allowed; closed-enum domains) ────────
    # Q5 strongest_skill — 4 raw skills + "all_equally_weak" honest opt-out
    # (per docs/P-220-onboarding-questionnaire-copy.md Q5).
    op.create_check_constraint(
        "ck_users_strongest_skill",
        "users",
        "strongest_skill IS NULL "
        "OR strongest_skill IN "
        "('speaking', 'listening', 'reading', 'writing', 'all_equally_weak')",
    )
    # Q6 weakest_skill — DIFFERENT domain from Q5: 6 blocker types, not raw
    # skills (per docs/P-220-onboarding-questionnaire-copy.md Q6).
    op.create_check_constraint(
        "ck_users_weakest_skill",
        "users",
        "weakest_skill IS NULL "
        "OR weakest_skill IN ("
        "'speaking_under_pressure', 'listening_fast', 'reading_complex', "
        "'writing_essays', 'grammar_accuracy', 'vocabulary_depth'"
        ")",
    )
    # Q7 hours_per_week — slugs (FE contract), not display labels.
    op.create_check_constraint(
        "ck_users_hours_per_week",
        "users",
        "hours_per_week IS NULL "
        "OR hours_per_week IN "
        "('less_than_2', '2_to_5', '5_to_10', 'more_than_10')",
    )
    op.create_check_constraint(
        "ck_users_prior_french_exam",
        "users",
        "prior_french_exam IS NULL "
        "OR prior_french_exam IN ('never', 'recent_6mo', 'recent_12mo', 'older')",
    )
    op.create_check_constraint(
        "ck_users_feedback_mode_preference",
        "users",
        "feedback_mode_preference IS NULL "
        "OR feedback_mode_preference IN ('calm', 'method')",
    )
    # topics_tested_on: must be a JSONB array of TCF test-theme slugs.
    # `jsonb_typeof = 'array'` rejects scalars/objects; `<@` requires
    # every element to be in the allowed slug list.
    op.create_check_constraint(
        "ck_users_topics_tested_on",
        "users",
        "topics_tested_on IS NULL OR ("
        "jsonb_typeof(topics_tested_on) = 'array' "
        "AND topics_tested_on <@ "
        """'["vie_quotidienne","societe","education","travail",""" \
        """"loisirs_voyages","sante","environnement","culture_medias"]'::jsonb""" \
        ")",
    )
    op.create_check_constraint(
        "ck_user_path_enrollments_persona",
        "user_path_enrollments",
        "persona IS NULL "
        "OR persona IN ('foundation', 'acceleration', 'cram')",
    )


def downgrade() -> None:
    # Drop constraints first, then columns. CHECK constraints are
    # table-scoped so we use op.drop_constraint with type_='check'.
    op.drop_constraint("ck_user_path_enrollments_persona", "user_path_enrollments", type_="check")
    op.drop_constraint("ck_users_topics_tested_on",         "users", type_="check")
    op.drop_constraint("ck_users_feedback_mode_preference", "users", type_="check")
    op.drop_constraint("ck_users_prior_french_exam",        "users", type_="check")
    op.drop_constraint("ck_users_hours_per_week",           "users", type_="check")
    op.drop_constraint("ck_users_weakest_skill",            "users", type_="check")
    op.drop_constraint("ck_users_strongest_skill",          "users", type_="check")

    op.drop_column("user_path_enrollments", "persona")

    op.drop_column("users", "feedback_mode_preference")
    op.drop_column("users", "prior_french_exam")
    op.drop_column("users", "native_language")
    op.drop_column("users", "topics_tested_on")
    op.drop_column("users", "hours_per_week")
    op.drop_column("users", "weakest_skill")
    op.drop_column("users", "strongest_skill")
