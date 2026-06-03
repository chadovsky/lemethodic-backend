"""F-410 / F-411 / F-417 — Phase 2 foundation tables + engagement columns

Revision ID: a0b1c2d3e4f5
Revises: f40200000001
Create Date: 2026-06-03

Changes in this migration:

  CREATE TABLE target_profiles   (F-410)
    Per-user exam-target configuration. Upsert-by-is_active at the router layer.
    Fully additive — no touch on existing tables.

  CREATE TABLE scoring_rubrics   (F-411)
    Per-(exam, level, couche_key) weight + score_mapping. Starting weights are
    seeded by scripts/seed_scoring_rubrics.py (gate #7 — Chadi approves prod
    seed separately). UNIQUE(exam, level, couche_key) enforces no duplicates.
    Fully additive.

  ALTER TABLE users              (F-417)
    7 engagement/progress columns: streak_days, longest_streak_days,
    streak_last_active_date, production_minutes_total, daily_target_minutes,
    tache_attempts, last_couche_signals.
    All nullable OR have a server_default so PG16 applies them as a
    metadata-only operation (no table rewrite).

pg_dump tiering: REQUIRED — touches `users` table.
Downgrade: safe for the CREATE tables (DROP); for the ALTER columns the
downgrade DROPs the 7 columns (existing data in those columns is lost on
downgrade, but all are engagement counters initialized to 0 — no meaningful
data loss unless the service has been running post-upgrade and recording
sessions).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "a0b1c2d3e4f5"
down_revision: Union[str, None] = "f40200000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── F-410: target_profiles ───────────────────────────────────────────────
    op.create_table(
        "target_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("exam", sa.String(length=50), nullable=False),
        sa.Column("threshold_band", sa.String(length=10), nullable=False),
        sa.Column("deadline_date", sa.Date(), nullable=True),
        sa.Column("persona_tag", sa.String(length=40), nullable=True),
        sa.Column(
            "maitre_intensity",
            sa.String(length=20),
            nullable=False,
            server_default="balanced",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=True,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=True,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "threshold_band IN ('b1', 'b2', 'c1', 'c2')",
            name="ck_target_profiles_threshold_band",
        ),
        sa.CheckConstraint(
            "maitre_intensity IN ('soft', 'balanced', 'strict')",
            name="ck_target_profiles_maitre_intensity",
        ),
        sa.CheckConstraint(
            "persona_tag IS NULL OR persona_tag IN "
            "('visa_urgent', 'academic', 'professional', 'general', 'professional_advancement')",
            name="ck_target_profiles_persona_tag",
        ),
    )
    op.create_index(op.f("ix_target_profiles_id"),      "target_profiles", ["id"],      unique=False)
    op.create_index(op.f("ix_target_profiles_user_id"), "target_profiles", ["user_id"], unique=False)

    # ── F-411: scoring_rubrics ───────────────────────────────────────────────
    op.create_table(
        "scoring_rubrics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("exam", sa.String(length=50), nullable=False),
        sa.Column("level", sa.String(length=10), nullable=False),
        sa.Column("couche_key", sa.String(length=40), nullable=False),
        sa.Column("weight", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("score_mapping", JSONB(), nullable=False),
        sa.Column("passing_threshold", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=True,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=True,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "exam", "level", "couche_key",
            name="uq_scoring_rubrics_exam_level_couche",
        ),
        sa.CheckConstraint(
            "level IN ('a1', 'a2', 'b1', 'b2', 'c1', 'c2')",
            name="ck_scoring_rubrics_level",
        ),
        sa.CheckConstraint(
            "couche_key IN "
            "('le_propos', 'le_plan', 'la_construction', 'les_pieges_anglais', 'la_musique')",
            name="ck_scoring_rubrics_couche_key",
        ),
    )
    op.create_index(op.f("ix_scoring_rubrics_id"),   "scoring_rubrics", ["id"],   unique=False)
    op.create_index(op.f("ix_scoring_rubrics_exam"), "scoring_rubrics", ["exam"], unique=False)

    # ── F-417: engagement + progress columns on users ────────────────────────
    # All non-nullable columns use server_default so PG16 applies them without
    # a table rewrite (metadata-only path — no existing row scan).
    op.add_column(
        "users",
        sa.Column("streak_days", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "users",
        sa.Column("longest_streak_days", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "users",
        sa.Column("streak_last_active_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("production_minutes_total", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "users",
        sa.Column("daily_target_minutes", sa.Integer(), nullable=False, server_default="20"),
    )
    op.add_column(
        "users",
        sa.Column("tache_attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "users",
        sa.Column("last_couche_signals", JSONB(), nullable=True),
    )


def downgrade() -> None:
    # F-417: drop engagement columns from users
    op.drop_column("users", "last_couche_signals")
    op.drop_column("users", "tache_attempts")
    op.drop_column("users", "daily_target_minutes")
    op.drop_column("users", "production_minutes_total")
    op.drop_column("users", "streak_last_active_date")
    op.drop_column("users", "longest_streak_days")
    op.drop_column("users", "streak_days")

    # F-411: drop scoring_rubrics
    op.drop_index(op.f("ix_scoring_rubrics_exam"), table_name="scoring_rubrics")
    op.drop_index(op.f("ix_scoring_rubrics_id"),   table_name="scoring_rubrics")
    op.drop_table("scoring_rubrics")

    # F-410: drop target_profiles
    op.drop_index(op.f("ix_target_profiles_user_id"), table_name="target_profiles")
    op.drop_index(op.f("ix_target_profiles_id"),      table_name="target_profiles")
    op.drop_table("target_profiles")
