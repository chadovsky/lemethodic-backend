"""F-221 v3 — add users.specific_intended_exam

Additive single-column migration. Captures the free-text exam name that
"another_exam" users fill in at q0 of the onboarding questionnaire (e.g.
DALF C1, FIDE, AP French, DCL). Stored for roadmap prioritization: when
enough users name a specific exam, a new exam-specific path can be built
and the enrolled user base migrated.

Column is VARCHAR(120) NULL:
  - NULL for all existing users (supported exams, legacy rows).
  - Non-empty string for "another_exam" users going forward
    (enforced by the Pydantic validator in OnboardingSubmitRequest,
    not by a DB NOT NULL — so legacy rows and direct DB inserts are
    never blocked).

No data loss on downgrade: column drops cleanly. No FK dependencies.

Rollback safety: pure additive (one ADD COLUMN). ``alembic downgrade -1``
is the emergency restore path; pg_dump from Chadi's pre-push step is
the secondary backup.

Revision ID: 35aa0b108050
Revises: i7g8h9i0j1k2
Create Date: 2026-05-25 (F-221 v3 — another_exam funnel restoration).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "35aa0b108050"
down_revision: Union[str, None] = "i7g8h9i0j1k2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("specific_intended_exam", sa.String(length=120), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "specific_intended_exam")
