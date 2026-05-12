"""F-310 Phase B — auth hardening schema

Adds:
  - 5 new columns on `users`:
      email_verified_at      (TIMESTAMP NULL) — null = unverified.
      stripe_customer_id     (VARCHAR(255) NULL) — set when P-105 creates customer.
      stripe_subscription_id (VARCHAR(255) NULL) — set when P-106 creates subscription.
      subscription_status    (VARCHAR(20) NULL, CHECK) — trialing|active|lapsed|canceled|none.
      subscription_tier      (VARCHAR(20) NOT NULL DEFAULT 'free', CHECK) —
                              free|subscription|sprint|premium.
  - 3 new tables:
      refresh_tokens             — durable refresh-token audit trail.
      email_verification_tokens  — short-lived verify-email tokens (24h).
      password_reset_tokens      — short-lived password-reset tokens (1h).

Grandfather backfill (per Decision 4, 2026-05-12):
  Every existing user gets email_verified_at = NOW() so the soft-beta
  cohort isn't locked out. New registrations leave the column NULL
  until the verification email is clicked.

Token storage strategy:
  email_verification_tokens + password_reset_tokens store SHA-256 hex
  of the actual token (column `token_hash`), NOT the token itself.
  The token is sent in the email link; on receipt we hash + compare.
  DB leak ≠ token harvest.

  refresh_tokens stores the raw `jti` (UUIDv4) because Redis-side
  revocation membership check is by jti and the jti is also encoded
  in the refresh JWT payload — it's not a secret in the same sense
  as a reset token.

Indices:
  refresh_tokens.jti — UNIQUE (lookup on every refresh).
  refresh_tokens (user_id, expires_at) — cleanup queries.
  email_verification_tokens.token_hash — UNIQUE (lookup from email link).
  email_verification_tokens.user_id — find pending verification per user.
  password_reset_tokens.token_hash — UNIQUE.
  password_reset_tokens.user_id — find pending reset per user.

Rollback safety:
  downgrade() drops all 3 new tables, drops both CHECK constraints, and
  drops all 5 new columns on `users`. No data preservation needed —
  the F-310 surface doesn't exist pre-migration, so post-rollback the
  app reverts to the V-016a schema cleanly.

Revision ID: h6f7g8e9d0c1
Revises: g5e6f7d8c9b0
Create Date: 2026-05-12 (F-310 Phase B auth hardening schema).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "h6f7g8e9d0c1"
down_revision: Union[str, None] = "g5e6f7d8c9b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users: 5 new columns ───────────────────────────────────────
    op.add_column(
        "users",
        sa.Column("email_verified_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("subscription_status", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "subscription_tier",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'free'"),
        ),
    )
    op.create_check_constraint(
        "ck_users_subscription_status",
        "users",
        "subscription_status IS NULL OR subscription_status IN "
        "('trialing', 'active', 'lapsed', 'canceled', 'none')",
    )
    op.create_check_constraint(
        "ck_users_subscription_tier",
        "users",
        "subscription_tier IN ('free', 'subscription', 'sprint', 'premium')",
    )

    # ── Grandfather backfill: existing users verified as of migration time ──
    # Decision 4 (2026-05-12): soft-beta cohort is grandfathered so the
    # new email-verification gate doesn't lock anyone out. New registrations
    # leave the column NULL until the verification link is clicked.
    op.execute("UPDATE users SET email_verified_at = NOW() WHERE email_verified_at IS NULL")

    # ── refresh_tokens ─────────────────────────────────────────────
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("jti", sa.String(length=36), nullable=False),
        sa.Column("issued_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        # When this refresh is rotated, store the successor's jti so we
        # can detect replay (presenting an already-rotated refresh).
        sa.Column("rotated_to_jti", sa.String(length=36), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_refresh_tokens_user",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("jti", name="uq_refresh_tokens_jti"),
    )
    op.create_index(
        "ix_refresh_tokens_user_expires",
        "refresh_tokens",
        ["user_id", "expires_at"],
        unique=False,
    )

    # ── email_verification_tokens ──────────────────────────────────
    op.create_table(
        "email_verification_tokens",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        # SHA-256 hex of the raw token sent in the email. 64 chars.
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("consumed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_email_verification_tokens_user",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("token_hash", name="uq_email_verification_tokens_hash"),
    )
    op.create_index(
        "ix_email_verification_tokens_user",
        "email_verification_tokens",
        ["user_id"],
        unique=False,
    )

    # ── password_reset_tokens ──────────────────────────────────────
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("consumed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_password_reset_tokens_user",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("token_hash", name="uq_password_reset_tokens_hash"),
    )
    op.create_index(
        "ix_password_reset_tokens_user",
        "password_reset_tokens",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    # Drop tables in reverse-creation order so FK constraints unwind cleanly.
    op.drop_index("ix_password_reset_tokens_user", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")

    op.drop_index(
        "ix_email_verification_tokens_user",
        table_name="email_verification_tokens",
    )
    op.drop_table("email_verification_tokens")

    op.drop_index("ix_refresh_tokens_user_expires", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")

    # users column drops — reverse-order. CHECK constraints first.
    op.drop_constraint("ck_users_subscription_tier", "users", type_="check")
    op.drop_constraint("ck_users_subscription_status", "users", type_="check")
    op.drop_column("users", "subscription_tier")
    op.drop_column("users", "subscription_status")
    op.drop_column("users", "stripe_subscription_id")
    op.drop_column("users", "stripe_customer_id")
    op.drop_column("users", "email_verified_at")
