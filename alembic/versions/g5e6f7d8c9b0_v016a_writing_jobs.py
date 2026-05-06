"""V-016a — async job table for writing analysis

Adds ``writing_submission_jobs`` to support the async POST→poll
pattern that fixes V-016a (writing submit timing out at ~30s on
prod because Claude analysis takes 36s+ and infrastructure cuts
the request before it returns).

Pattern (V-016a A+C hybrid, locked 2026-05-07):
  POST /api/writing/submit   → 202 with job_id (background task)
  GET  /api/writing/jobs/{id} → status + result | error

Job row carries the full lifecycle (pending → running → completed
| failed). Result is stored as serialized JSON so the GET endpoint
hands back the same shape the legacy sync POST returned, letting
the FE polling consumer render identically.

Forever retention per Q3 lock-in (small table, useful for debugging
+ history surface). File P-260c if table grows.

Composite index on (user_id, created_at) supports "newest jobs for
user X" — same shape as user_cluster_events index.

Revision ID: g5e6f7d8c9b0
Revises: f4d5e6c7b8a9
Create Date: 2026-05-07 (V-016a BE-side async job pattern + C
stopgap).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "g5e6f7d8c9b0"
down_revision: Union[str, None] = "f4d5e6c7b8a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "writing_submission_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        # Populated only when status='completed'.
        sa.Column("submission_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        # Serialized WritingSubmissionResult (same shape as the legacy
        # sync POST /submit response: id, word_count, time_taken_seconds,
        # feedback, submitted_at). FE polling consumer reads this.
        sa.Column("result_json", sa.Text(), nullable=True),
        # Sanitized failure reason. Capped at 500 chars at write-time.
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_writing_submission_jobs_user",
        ),
        sa.ForeignKeyConstraint(
            ["submission_id"], ["writing_submissions.id"],
            name="fk_writing_submission_jobs_submission",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="ck_writing_submission_jobs_status",
        ),
    )
    op.create_index(
        "ix_writing_submission_jobs_user_created",
        "writing_submission_jobs",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_writing_submission_jobs_user_created",
        table_name="writing_submission_jobs",
    )
    op.drop_table("writing_submission_jobs")
