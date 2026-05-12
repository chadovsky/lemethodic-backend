"""F-310 Phase B — ORM models for the 3 auth-token tables.

Schema lives in alembic migration h6f7g8e9d0c1_f310_auth_hardening.py;
this module is the SQLAlchemy mirror for query-side use.

Convention (mirror of app/models/writing.py): one file per related
table cluster. Migration is the source of truth for column shapes +
CHECK constraints + indices; this file declares what the app reads/writes.

No relationships back to User are declared — token rows are accessed
via direct `db.query(RefreshToken).filter(...)` patterns, never via
`user.refresh_tokens`. Keeps the User model from blowing up with
back_populates noise.

Tokens never expose the raw secret outside their issuing helpers
(jwt_tokens.py for refresh jti, email_verification.py / password_reset.py
for the raw URL tokens). `token_hash` columns store SHA-256 hex of the
raw secret; the secret itself only exists in the email URL.
"""
from __future__ import annotations

import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)

from app.database import Base


class RefreshToken(Base):
    """Refresh-token audit trail. Redis owns fast revocation (jti
    membership in a sorted set keyed by user_id); this table owns the
    durable history + the rotated_to_jti chain that lets us detect
    replay of an already-rotated refresh.
    """
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    jti = Column(String(36), nullable=False)
    issued_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    # Set when this refresh is rotated. Presenting a refresh whose
    # rotated_to_jti is non-null = replay attempt.
    rotated_to_jti = Column(String(36), nullable=True)
    revoked_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("jti", name="uq_refresh_tokens_jti"),
    )


class EmailVerificationToken(Base):
    """One-shot email-verification token. The raw token is generated
    at registration / resend, sent in the email URL, hashed (SHA-256
    hex) and stored here. On consumption, we hash the URL token + look
    up by token_hash + ensure consumed_at IS NULL + expires_at > NOW().
    """
    __tablename__ = "email_verification_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    consumed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_email_verification_tokens_hash"),
    )


class PasswordResetToken(Base):
    """One-shot password-reset token. Same storage pattern as
    EmailVerificationToken; lifetimes are shorter (1h vs 24h)."""
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    consumed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_password_reset_tokens_hash"),
    )
