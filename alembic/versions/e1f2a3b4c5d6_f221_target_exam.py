"""F-221 — target_exam columns on User + UserPathEnrollment

Adds `target_exam` to both `users` and `user_path_enrollments` to
support the brand-layer pivot (TCF prep → French exam prep for
English speakers across exams). The Q-exam-target onboarding
question (FE-side, F-221 cross-repo) writes the slug here.

Phase 1 routing rules (consumed by app/services/onboarding_router.py):

  - {tcf, tef, delf} → existing q1/q2-driven path resolution.
    Active path b1_to_b2 covers TCF/TEF/DELF B1/B2 since the
    format DNA is shared.
  - {dalf, fide, ap, dcl} → waitlist with reason "exam_not_active"
    and a per-exam "Coming soon" copy variant on the FE side.
  - NULL → backward-compat for legacy users who completed
    onboarding before this column landed. Resolver treats NULL
    as exam-unspecified and falls through to q1/q2-only routing.

Why two columns (User + UserPathEnrollment) instead of one:
  - User.target_exam reflects the user's stated intent (mutable —
    they may switch exams over time without re-enrolling).
  - UserPathEnrollment.target_exam is the snapshot at enrollment
    time (mirrors the existing User vs UserPathEnrollment split for
    enrolled_at_level / persona). A user who switches exams later
    gets a new enrollment row carrying the new target_exam; the
    previous enrollment retains its original.

CHECK constraint domain on both columns:
  ('tcf', 'tef', 'delf', 'dalf', 'fide', 'ap', 'dcl')
or NULL.

Revision ID: e1f2a3b4c5d6
Revises: d7e4f3c2b1a9
Create Date: 2026-05-04 (BE-as-lead-orchestrator, F-221 cross-repo
in tandem with FE plan-first prompt).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, None] = "d7e4f3c2b1a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_EXAM_DOMAIN = "('tcf', 'tef', 'delf', 'dalf', 'fide', 'ap', 'dcl')"


def upgrade() -> None:
    # users.target_exam
    op.add_column(
        "users",
        sa.Column("target_exam", sa.String(length=10), nullable=True),
    )
    op.create_check_constraint(
        "ck_users_target_exam",
        "users",
        f"target_exam IS NULL OR target_exam IN {_EXAM_DOMAIN}",
    )

    # user_path_enrollments.target_exam
    op.add_column(
        "user_path_enrollments",
        sa.Column("target_exam", sa.String(length=10), nullable=True),
    )
    op.create_check_constraint(
        "ck_user_path_enrollments_target_exam",
        "user_path_enrollments",
        f"target_exam IS NULL OR target_exam IN {_EXAM_DOMAIN}",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_user_path_enrollments_target_exam",
        "user_path_enrollments",
        type_="check",
    )
    op.drop_column("user_path_enrollments", "target_exam")

    op.drop_constraint(
        "ck_users_target_exam",
        "users",
        type_="check",
    )
    op.drop_column("users", "target_exam")
