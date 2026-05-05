"""F-221 v2 — realign target_exam to FE-locked 5-slug domain

Supersedes the initial F-221 migration (e1f2a3b4c5d6) which shipped a
7-slug domain ('tcf', 'tef', 'delf', 'dalf', 'fide', 'ap', 'dcl').
The FE plan-first round (locked 2026-05-05, FE commit 21a7edc) settled
on a 5-slug domain matching the strategic exam_profile semantics:

  'tcf_canada', 'tef_canada', 'delf_b1_b2', 'another_exam', 'not_sure'

Migration shape:
  - DROP the old 7-slug CHECK constraints on both tables.
  - ALTER COLUMN target_exam TYPE varchar(20). Old varchar(10) was
    too narrow — 'another_exam' is 12 chars, headroom for future
    slugs taken at 20.
  - ADD the new 5-slug CHECK constraints.
  - CREATE INDEX on both target_exam columns (per F-221 spec —
    enables future "filter by target_exam" queries on the writing
    surface and dashboard cohort splits).
  - BACKFILL: production test users (id IN 5, 6, 7) → 'tcf_canada'.
    No-op when run against a fresh local DB without those rows.

Field naming decision:
  Stayed with `target_exam` (not exam_profile). The legacy
  exam_profile column on `users` (varchar(50), populated by the
  deprecated /api/users/onboarding endpoint) remains dormant — no
  new writes via /onboarding/submit. Kept for backward-compat read
  paths only; eventual cleanup folds into F-226 voice-audit sweep.

Q-prefix decision:
  API field renamed from `target_exam` → `q0_target_exam` on
  OnboardingSubmitRequest. Matches FE 21a7edc + the q-prefixed
  convention for ordered onboarding questions (q0 lands first
  in the flow). DB column stays `target_exam` — semantic-clean,
  no q-numbering at storage layer.

F-224 relevance (note for future seeder evolution):
  When writing prompts gain a target_exam tag for cohort-aware
  filtering on the writing surface, the index added here on
  user_path_enrollments.target_exam is what the join hits.

Revision ID: f3a4b5c6d7e8
Revises: e1f2a3b4c5d6
Create Date: 2026-05-05 (BE-side F-221 v2 to match FE-locked contract).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f3a4b5c6d7e8"
down_revision: Union[str, None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_NEW_DOMAIN = (
    "('tcf_canada', 'tef_canada', 'delf_b1_b2', 'another_exam', 'not_sure')"
)


def upgrade() -> None:
    # ── users.target_exam ─────────────────────────────────────────
    op.drop_constraint("ck_users_target_exam", "users", type_="check")
    op.alter_column(
        "users",
        "target_exam",
        existing_type=sa.String(length=10),
        type_=sa.String(length=20),
        existing_nullable=True,
    )
    op.create_check_constraint(
        "ck_users_target_exam",
        "users",
        f"target_exam IS NULL OR target_exam IN {_NEW_DOMAIN}",
    )
    op.create_index(
        "ix_users_target_exam",
        "users",
        ["target_exam"],
        unique=False,
    )

    # ── user_path_enrollments.target_exam ─────────────────────────
    op.drop_constraint(
        "ck_user_path_enrollments_target_exam",
        "user_path_enrollments",
        type_="check",
    )
    op.alter_column(
        "user_path_enrollments",
        "target_exam",
        existing_type=sa.String(length=10),
        type_=sa.String(length=20),
        existing_nullable=True,
    )
    op.create_check_constraint(
        "ck_user_path_enrollments_target_exam",
        "user_path_enrollments",
        f"target_exam IS NULL OR target_exam IN {_NEW_DOMAIN}",
    )
    op.create_index(
        "ix_user_path_enrollments_target_exam",
        "user_path_enrollments",
        ["target_exam"],
        unique=False,
    )

    # ── Backfill production test users (id IN 5, 6, 7) ────────────
    # No-op locally on a fresh DB without those rows. Runs once
    # against production via the App Platform deploy hook.
    op.execute(
        "UPDATE users SET target_exam = 'tcf_canada' "
        "WHERE id IN (5, 6, 7) AND target_exam IS NULL"
    )
    # Mirror the backfill on UserPathEnrollment for any active
    # enrollment those test users have. Same id-list filter via the
    # user_id FK.
    op.execute(
        "UPDATE user_path_enrollments SET target_exam = 'tcf_canada' "
        "WHERE user_id IN (5, 6, 7) "
        "AND target_exam IS NULL "
        "AND is_active = true"
    )


def downgrade() -> None:
    # Revert to the v1 7-slug domain. Note: any rows backfilled to
    # 'tcf_canada' or with new-domain values that aren't in the v1
    # domain will fail the v1 CHECK constraint when re-applied.
    # Downgrade is intended for emergency rollback during the same
    # day's deploy; production data accumulating new-domain values
    # makes downgrade increasingly unsafe over time.
    op.drop_index(
        "ix_user_path_enrollments_target_exam",
        table_name="user_path_enrollments",
    )
    op.drop_constraint(
        "ck_user_path_enrollments_target_exam",
        "user_path_enrollments",
        type_="check",
    )
    op.alter_column(
        "user_path_enrollments",
        "target_exam",
        existing_type=sa.String(length=20),
        type_=sa.String(length=10),
        existing_nullable=True,
    )
    op.create_check_constraint(
        "ck_user_path_enrollments_target_exam",
        "user_path_enrollments",
        "target_exam IS NULL "
        "OR target_exam IN ('tcf', 'tef', 'delf', 'dalf', 'fide', 'ap', 'dcl')",
    )

    op.drop_index("ix_users_target_exam", table_name="users")
    op.drop_constraint("ck_users_target_exam", "users", type_="check")
    op.alter_column(
        "users",
        "target_exam",
        existing_type=sa.String(length=20),
        type_=sa.String(length=10),
        existing_nullable=True,
    )
    op.create_check_constraint(
        "ck_users_target_exam",
        "users",
        "target_exam IS NULL "
        "OR target_exam IN ('tcf', 'tef', 'delf', 'dalf', 'fide', 'ap', 'dcl')",
    )
