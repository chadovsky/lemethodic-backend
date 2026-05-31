"""F-402 -- FK indexes on hot and unindexed FK columns

Revision ID: f40200000001
Revises: 35aa0b108050
Create Date: 2026-05-31

Audit (be-audit-2026-05-31) rated the index coverage 3/10.
Two confirmed-hot columns (recordings.user_id, feedbacks.recording_id)
were unindexed. Twelve additional FK columns were flagged for
verification and confirmed missing against pg_indexes on local dev.

All 14 indexes added in this single revision. Naming follows the
project convention: op.f('ix_<table>_<column>') throughout. Downgrade
drops all 14 in reverse order.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "f40200000001"
down_revision: Union[str, None] = "35aa0b108050"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── recordings ──────────────────────────────────────────────────
    op.create_index(op.f("ix_recordings_user_id"),  "recordings", ["user_id"],  unique=False)
    op.create_index(op.f("ix_recordings_topic_id"), "recordings", ["topic_id"], unique=False)

    # ── feedbacks ───────────────────────────────────────────────────
    op.create_index(op.f("ix_feedbacks_recording_id"), "feedbacks", ["recording_id"], unique=False)

    # ── writing_submissions ─────────────────────────────────────────
    op.create_index(op.f("ix_writing_submissions_user_id"),   "writing_submissions", ["user_id"],   unique=False)
    op.create_index(op.f("ix_writing_submissions_prompt_id"), "writing_submissions", ["prompt_id"], unique=False)

    # ── remediation_modules ─────────────────────────────────────────
    op.create_index(op.f("ix_remediation_modules_ecole_lesson_id"), "remediation_modules", ["ecole_lesson_id"], unique=False)

    # ── clusters ────────────────────────────────────────────────────
    op.create_index(op.f("ix_clusters_vocabulary_theme_id"), "clusters", ["vocabulary_theme_id"], unique=False)
    op.create_index(op.f("ix_clusters_parent_cluster_id"),  "clusters", ["parent_cluster_id"],  unique=False)

    # ── user_path_enrollments ────────────────────────────────────────
    op.create_index(op.f("ix_user_path_enrollments_current_phase_id"),   "user_path_enrollments", ["current_phase_id"],   unique=False)
    op.create_index(op.f("ix_user_path_enrollments_current_cluster_id"), "user_path_enrollments", ["current_cluster_id"], unique=False)

    # ── user_cluster_statuses ────────────────────────────────────────
    op.create_index(op.f("ix_user_cluster_statuses_last_evaluated_recording_id"), "user_cluster_statuses", ["last_evaluated_recording_id"], unique=False)

    # ── user_cluster_events ─────────────────────────────────────────
    op.create_index(op.f("ix_user_cluster_events_triggered_by_recording_id"), "user_cluster_events", ["triggered_by_recording_id"], unique=False)

    # ── user_level_assessments ───────────────────────────────────────
    op.create_index(op.f("ix_user_level_assessments_triggered_by_recording_id"), "user_level_assessments", ["triggered_by_recording_id"], unique=False)

    # ── writing_submission_jobs ──────────────────────────────────────
    op.create_index(op.f("ix_writing_submission_jobs_submission_id"), "writing_submission_jobs", ["submission_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_writing_submission_jobs_submission_id"),              table_name="writing_submission_jobs")
    op.drop_index(op.f("ix_user_level_assessments_triggered_by_recording_id"),   table_name="user_level_assessments")
    op.drop_index(op.f("ix_user_cluster_events_triggered_by_recording_id"),      table_name="user_cluster_events")
    op.drop_index(op.f("ix_user_cluster_statuses_last_evaluated_recording_id"),  table_name="user_cluster_statuses")
    op.drop_index(op.f("ix_user_path_enrollments_current_cluster_id"),           table_name="user_path_enrollments")
    op.drop_index(op.f("ix_user_path_enrollments_current_phase_id"),             table_name="user_path_enrollments")
    op.drop_index(op.f("ix_clusters_parent_cluster_id"),                         table_name="clusters")
    op.drop_index(op.f("ix_clusters_vocabulary_theme_id"),                       table_name="clusters")
    op.drop_index(op.f("ix_remediation_modules_ecole_lesson_id"),                table_name="remediation_modules")
    op.drop_index(op.f("ix_writing_submissions_prompt_id"),                      table_name="writing_submissions")
    op.drop_index(op.f("ix_writing_submissions_user_id"),                        table_name="writing_submissions")
    op.drop_index(op.f("ix_feedbacks_recording_id"),                             table_name="feedbacks")
    op.drop_index(op.f("ix_recordings_topic_id"),                                table_name="recordings")
    op.drop_index(op.f("ix_recordings_user_id"),                                 table_name="recordings")
