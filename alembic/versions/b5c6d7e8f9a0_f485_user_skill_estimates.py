"""F-485 - user_skill_estimates table

Revision ID: b5c6d7e8f9a0
Revises: a0b1c2d3e4f5
Create Date: 2026-06-26

Changes in this migration:

  CREATE TABLE user_skill_estimates   (F-485)
    User-global per-skill CEFR estimate store. One row per user
    (UNIQUE(user_id)). The `estimates` JSONB holds a per-skill map
    {"CO": {"level": "B1", "updated_at": iso}, ...}. Fully additive:
    no touch on existing tables.

pg_dump tiering: OPTIONAL - 100% additive (single CREATE TABLE on a new
object, zero ALTER / INSERT / UPDATE / DELETE on existing data). The
clean `downgrade -1` DROPs the new empty table and loses zero existing
data; the DO daily auto-backup is the secondary fallback.

Downgrade: DROP the new table and its indexes. Reversible.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "b5c6d7e8f9a0"
down_revision: Union[str, None] = "a0b1c2d3e4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_skill_estimates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("estimates", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
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
    )
    op.create_index(
        op.f("ix_user_skill_estimates_id"),
        "user_skill_estimates",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_skill_estimates_user_id"),
        "user_skill_estimates",
        ["user_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_user_skill_estimates_user_id"), table_name="user_skill_estimates")
    op.drop_index(op.f("ix_user_skill_estimates_id"), table_name="user_skill_estimates")
    op.drop_table("user_skill_estimates")
