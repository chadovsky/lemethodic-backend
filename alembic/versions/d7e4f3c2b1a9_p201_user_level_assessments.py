"""P-201 — schema for level assessment history (append-only)

Adds user_level_assessments — append-only history of system-assigned
CEFR level per user. One row per assessment computation; latest
reflects the most recent detection signal.

Why a new table (vs columns on UserPathEnrollment):
  - Mirrors UserClusterEvent's append-only pattern from P-204 — same
    architectural shape applied to user-level history.
  - Append-only INSERT is friendlier to Postgres MVCC than
    update-on-every-recording on a hot enrollment row.
  - Preserves history for P-250 calibration + Block 8 Confidence
    Visualizer (level progression over time per curriculum doc §7).
  - Doesn't overload UserPathEnrollment with system-assigned fields
    next to user-self-reported fields — different lifecycles.

Honest level labels (below_B1 / B1_emerging / B1_solid / above_B1 /
insufficient_data) instead of raw CEFR codes — Phase 1 has 13 B1-only
authored clusters, so we can directly validate B1 but only INFER
above/below. Labels graduate to {A2, B1, B2, C1} when curriculum
content for those levels lands (P-211b).

NOTE — SQLAlchemy model class for this table (UserLevelAssessment in
app/models/models.py) is NOT yet declared. It lands in the follow-up
commit alongside the level-assignment service + endpoint. Until then,
`alembic revision --autogenerate` will see drift — do not autogenerate
again until the model class is added.

Revision ID: d7e4f3c2b1a9   ← placeholder; regenerate via
                              `alembic revision --autogenerate` before
                              applying if you want a real timestamp,
                              OR keep this id as-is.
Revises: c4f2d1e3a0b5
Create Date: 2026-05-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d7e4f3c2b1a9"
down_revision: Union[str, None] = "c4f2d1e3a0b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_level_assessments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        # The assignment.
        sa.Column("assigned_level",      sa.String(length=20), nullable=False),
        sa.Column("assigned_confidence", sa.String(length=20), nullable=False),
        # Telemetry / debug. Raw floats preserved alongside bucketed
        # confidence so P-250 calibration has the granular signal.
        sa.Column("coverage",             sa.Float(),   nullable=False),
        sa.Column("top_bucket_share",     sa.Float(),   nullable=False),
        sa.Column("confidence_score",     sa.Float(),   nullable=False),
        sa.Column("n_clusters_evaluated", sa.Integer(), nullable=False),
        sa.Column("n_clusters_clean",     sa.Integer(), nullable=False),
        sa.Column("n_clusters_wobble",    sa.Integer(), nullable=False),
        sa.Column("n_clusters_fail",      sa.Integer(), nullable=False),
        # Optional pointer to the recording that triggered this
        # re-assessment. NULL if admin/cron-triggered (no such codepath
        # in Phase 1; the column is forward-looking).
        sa.Column("triggered_by_recording_id", sa.Integer(), nullable=True),
        sa.Column("computed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_user_level_assessments_user",
        ),
        sa.ForeignKeyConstraint(
            ["triggered_by_recording_id"], ["recordings.id"],
            name="fk_user_level_assessments_recording",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "assigned_level IN ("
            "'below_B1', 'B1_emerging', 'B1_solid', 'above_B1', 'insufficient_data'"
            ")",
            name="ck_user_level_assessments_assigned_level",
        ),
        sa.CheckConstraint(
            "assigned_confidence IN ('high', 'medium', 'low')",
            name="ck_user_level_assessments_assigned_confidence",
        ),
    )
    op.create_index(
        op.f("ix_user_level_assessments_id"),
        "user_level_assessments",
        ["id"],
        unique=False,
    )
    # Composite index for the "latest assessment for user X" query.
    # Same pattern as ix_user_cluster_events_user_created (P-204) —
    # supports backward index scan + heap fetch in ~1ms.
    op.create_index(
        op.f("ix_user_level_assessments_user_computed"),
        "user_level_assessments",
        ["user_id", "computed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_user_level_assessments_user_computed"),
        table_name="user_level_assessments",
    )
    op.drop_index(
        op.f("ix_user_level_assessments_id"),
        table_name="user_level_assessments",
    )
    op.drop_table("user_level_assessments")
