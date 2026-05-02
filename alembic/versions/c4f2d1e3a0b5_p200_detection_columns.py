"""P-200 — detection result columns

Adds two columns to back the detection engine output:

  user_cluster_statuses.last_detection_result   VARCHAR(20) NULL
  user_cluster_events.findings_json             JSONB NULL

Lifecycle (`status`) and latest detection result are two independent
axes per the P-200 design — `status` continues to mean curriculum
progress (not_started / in_progress / absorbed / needs_revisit), while
`last_detection_result` carries the latest single-recording finding
(clean / wobble / fail / not_observed). They update independently.

CHECK constraint on `last_detection_result` matches the
ck_user_path_enrollments_persona convention from P-220: plain VARCHAR
+ CHECK rather than a PG ENUM type, so adding values later is a
one-line ALTER instead of an enum-add migration. NULL is allowed —
existing rows + clusters that haven't been detected yet stay NULL.

`findings_json` carries the LLM's detection payload, used by P-250
calibration replay, the dashboard's "why was this flagged" UX, and
debugging. Loose JSONB by design; the shape is enforced via Pydantic
at write time (lands with the detection engine in commit 2).

Expected findings_json shape (documented here for migration readers;
authoritative shape lives on `app/schemas/detection.py` from commit 2):

    {
      "fired_markers": [
        {"marker_id": "B1.1.C1.a",
         "severity":  "high",
         "evidence":  "narrative is 95s with imparfait ratio ~0.08, ..."}
      ],
      "silent_markers": ["B1.1.C1.b", "B1.1.C1.c", ...],
      "status_logic_path": "needs_revisit",   // which prose branch matched
      "rubric_score":      0.0,                // 0..1, severity-weighted
      "detection_result":  "fail",             // matches last_detection_result column
      "model":             "claude-sonnet-4-20250514",
      "input_tokens":      4523,
      "output_tokens":     187
    }

NOTE — SQLAlchemy model classes for these columns (UserClusterStatus
and UserClusterEvent in app/models/models.py) are NOT yet updated.
They land in the follow-up commit alongside the detection engine.
Until then, `alembic revision --autogenerate` will see drift — do not
autogenerate again until the model classes are added.

Revision ID: c4f2d1e3a0b5   ← placeholder; regenerate via
                              `alembic revision --autogenerate` before
                              applying if you want a real timestamp,
                              OR keep this id as-is.
Revises: b3a55c1e0001
Create Date: 2026-05-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = "c4f2d1e3a0b5"
down_revision: Union[str, None] = "b3a55c1e0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_cluster_statuses",
        sa.Column("last_detection_result", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "user_cluster_events",
        sa.Column("findings_json", JSONB(), nullable=True),
    )

    # Domain-restricting CHECK on last_detection_result. NULL passes
    # explicitly so existing rows (all NULL) don't fail.
    op.create_check_constraint(
        "ck_user_cluster_statuses_last_detection_result",
        "user_cluster_statuses",
        "last_detection_result IS NULL "
        "OR last_detection_result IN ('clean', 'wobble', 'fail', 'not_observed')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_user_cluster_statuses_last_detection_result",
        "user_cluster_statuses",
        type_="check",
    )
    op.drop_column("user_cluster_events", "findings_json")
    op.drop_column("user_cluster_statuses", "last_detection_result")
