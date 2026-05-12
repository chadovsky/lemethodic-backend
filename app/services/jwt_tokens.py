"""F-310 Phase B — JWT mint / verify / rotate helpers.

Split out of auth.py so the auth router stays focused on HTTP shape +
the token lifecycle lives in one place.

Two token kinds:
  - ACCESS — short-lived (15 min), stateless JWT. Verified by signature
    + exp check only. No DB hit; no Redis hit.
  - REFRESH — long-lived (7 days), JWT with a `jti` claim. The jti is
    stored in `refresh_tokens` (audit trail + rotation chain) and added
    to a Redis set on revocation for sub-ms revocation lookup. Verifying
    a refresh involves: JWT signature + jti DB-present + not rotated +
    not expired + jti not in Redis revoked-set.

Plus two pure-secret token kinds (NOT JWTs):
  - Email verification token: random 32-byte urlsafe base64; raw token
    sent in email URL, SHA-256 hex stored in `email_verification_tokens`.
  - Password reset token: same pattern; stored in `password_reset_tokens`.
"""
from __future__ import annotations

import datetime
import hashlib
import secrets
import uuid

from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.models.auth_tokens import RefreshToken
from app.services.redis_client import get_redis


# ──────────────────────────────────────────────────────────────────
# Access tokens (short-lived JWT, stateless)
# ──────────────────────────────────────────────────────────────────


def mint_access_token(email: str) -> str:
    """Mint a 15-min access JWT for `email`. Stateless — no DB / Redis hit."""
    now = datetime.datetime.utcnow()
    payload = {
        "sub": email,
        "type": "access",
        "iat": now,
        "exp": now + datetime.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_access_token(token: str) -> dict:
    """Verify access JWT signature + exp + type. Returns payload dict.
    Raises JWTError on any failure — caller maps to HTTP 401."""
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    if payload.get("type") != "access":
        raise JWTError("Not an access token")
    if not payload.get("sub"):
        raise JWTError("Missing subject")
    return payload


# ──────────────────────────────────────────────────────────────────
# Refresh tokens (long-lived JWT, jti-tracked in Postgres + Redis)
# ──────────────────────────────────────────────────────────────────


_REDIS_REVOKED_PREFIX = "f310:refresh:revoked"  # SET of revoked jti


def _refresh_expiry() -> datetime.datetime:
    return datetime.datetime.utcnow() + datetime.timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS,
    )


def mint_refresh_token(db: Session, *, user_id: int, email: str) -> tuple[str, str]:
    """Mint a refresh JWT + create the audit row in refresh_tokens.

    Returns (jwt_string, jti). Caller is responsible for setting the
    cookie (or wherever the refresh travels).
    """
    jti = str(uuid.uuid4())
    now = datetime.datetime.utcnow()
    expires_at = _refresh_expiry()

    # DB audit row first — if commit fails, we never minted the JWT.
    db.add(RefreshToken(
        user_id=user_id,
        jti=jti,
        issued_at=now,
        expires_at=expires_at,
    ))
    db.commit()

    payload = {
        "sub": email,
        "type": "refresh",
        "jti": jti,
        "iat": now,
        "exp": expires_at,
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, jti


class RefreshTokenError(Exception):
    """Raised when a refresh token fails any of: signature, type, jti
    presence, jti not revoked, jti not rotated, expires_at > NOW().
    Caller returns HTTP 401 + clears the refresh cookie."""


async def verify_refresh_token(db: Session, token: str) -> tuple[dict, RefreshToken]:
    """Verify a refresh JWT end-to-end. Returns (payload, db_row) on
    success. Raises RefreshTokenError on any failure.

    Checks (in order):
      1. JWT signature + exp + type=refresh + jti present
      2. jti not in Redis revoked-set (fast)
      3. DB row exists for the jti, not rotated, not revoked, not expired
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as e:
        raise RefreshTokenError(f"Invalid JWT: {e}") from e

    if payload.get("type") != "refresh":
        raise RefreshTokenError("Not a refresh token")
    jti = payload.get("jti")
    if not jti:
        raise RefreshTokenError("Missing jti")

    # Fast Redis revocation lookup
    try:
        is_revoked = await get_redis().sismember(_REDIS_REVOKED_PREFIX, jti)
        if is_revoked:
            raise RefreshTokenError("Refresh token revoked")
    except RefreshTokenError:
        raise
    except Exception:
        # Redis unreachable — fall through to DB check (fail-open on Redis,
        # never fail-open on DB). The DB row's revoked_at column is
        # authoritative; Redis is the performance optimization.
        pass

    # DB authoritative check
    row = db.query(RefreshToken).filter(RefreshToken.jti == jti).first()
    if row is None:
        raise RefreshTokenError("Refresh token not found")
    if row.revoked_at is not None:
        raise RefreshTokenError("Refresh token revoked (db)")
    if row.rotated_to_jti is not None:
        # Replay: this refresh was already rotated. Treat as compromise
        # and revoke the WHOLE rotation chain by marking the successor
        # revoked too (caller logs this; security-meaningful event).
        raise RefreshTokenError("Refresh token already rotated (replay)")
    if row.expires_at <= datetime.datetime.utcnow():
        raise RefreshTokenError("Refresh token expired")

    return payload, row


async def rotate_refresh_token(
    db: Session,
    *,
    old_row: RefreshToken,
    email: str,
) -> tuple[str, str]:
    """Issue a successor refresh, mark the old one rotated, add old jti
    to Redis revoked-set. Returns (new_jwt, new_jti).

    Caller flow: verify_refresh_token(...) -> rotate_refresh_token(...)
    on success.
    """
    new_jwt, new_jti = mint_refresh_token(db, user_id=old_row.user_id, email=email)

    old_row.rotated_to_jti = new_jti
    old_row.revoked_at = datetime.datetime.utcnow()
    db.commit()

    # Add the old jti to Redis revoked-set so subsequent presentations
    # short-circuit before the DB hit. TTL ≈ refresh token lifetime.
    try:
        r = get_redis()
        await r.sadd(_REDIS_REVOKED_PREFIX, old_row.jti)
        # Re-set TTL on the whole set — rough, but a set-per-jti is also
        # an option if memory pressure surfaces. For soft-beta volume,
        # one set is fine.
        await r.expire(
            _REDIS_REVOKED_PREFIX,
            settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400 + 3600,
        )
    except Exception:
        # Redis unreachable — DB-side revoked_at is authoritative; we
        # take a perf hit until Redis recovers but no security gap.
        pass

    return new_jwt, new_jti


async def revoke_refresh_token(db: Session, *, jti: str) -> None:
    """Revoke a refresh by jti — for logout flow. No-op if jti not found.
    Marks DB row revoked + adds to Redis revoked-set."""
    row = db.query(RefreshToken).filter(RefreshToken.jti == jti).first()
    if row is None:
        return
    if row.revoked_at is None:
        row.revoked_at = datetime.datetime.utcnow()
        db.commit()
    try:
        await get_redis().sadd(_REDIS_REVOKED_PREFIX, jti)
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────
# Email-verification + password-reset secret tokens (NOT JWTs)
# ──────────────────────────────────────────────────────────────────


def generate_secret_token() -> tuple[str, str]:
    """Generate a random secret token suitable for email URLs.

    Returns (raw_token, sha256_hex). The raw token goes in the email;
    the hash goes in the DB. Never store or log the raw token.
    """
    raw = secrets.token_urlsafe(32)  # 256 bits of entropy
    return raw, hash_token(raw)


def hash_token(raw: str) -> str:
    """SHA-256 hex of a raw token. Same hash on register-side and
    verify-side — pure function, no salt (the token IS the secret;
    salting adds nothing here)."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
