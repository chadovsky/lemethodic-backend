"""Auth endpoints — F-310 Phase B refactor.

Surface contract (FE consumes):
  POST /api/auth/register
      Body: {email, password, full_name}
      201: {access_token, user} (legacy shape; cookies set: access_token + refresh_token)
      400: validation / duplicate / password-too-short
      NOTE Phase C will add: hCaptcha verification (h-captcha-response field),
           email-verification email send. Phase B creates the verification
           token row in the DB but does not send mail.

  POST /api/auth/login
      Body: {email, password}
      200: {access_token, user} + cookies (access_token + refresh_token)
      401: invalid credentials
      NOTE Phase D will add: /auth/* rate-limit middleware.

  POST /api/auth/refresh
      Reads refresh_token cookie; rotates + reissues both tokens.
      200: {access_token} + new cookies
      401: invalid / expired / revoked / replayed refresh

  POST /api/auth/logout
      Auth required (allow_unverified). Revokes the active refresh token.
      Clears both cookies.
      200: {"message": "Logged out"}

  GET /api/auth/me
      Auth required (allow_unverified — so unverified users can see their
      verification state). Returns serialized user.

  POST /api/auth/verify-email
      Body: {token}
      200: {"message": "Email verified"} — sets users.email_verified_at = NOW().
      400: invalid / expired / already-consumed token.

  POST /api/auth/verify-email/resend
      Auth required (allow_unverified). Generates a fresh verification token,
      consumes the previous outstanding one if any. Phase C wires email send.
      200: {"message": "Verification email sent"}
      409: {"code": "already_verified"} if already verified.

  POST /api/auth/password-reset/request
      Body: {email}
      200 always (never reveals whether email exists — anti-enumeration).
      Generates token if user exists; Phase C wires email send.

  POST /api/auth/password-reset/confirm
      Body: {token, new_password}
      200: {"message": "Password reset"} — updates users.hashed_password.
      400: invalid / expired / consumed token, or password-too-short.

Per F-310 Phase B Decision 4: email-verification is a HARD GATE on new
registrations. Existing soft-beta accounts are grandfathered as verified
via migration h6f7g8e9d0c1's `UPDATE users SET email_verified_at = NOW()`
backfill statement.
"""
from __future__ import annotations

import datetime
import hashlib

from fastapi import APIRouter, Depends, HTTPException, Response, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.models import User
from app.models.auth_tokens import (
    EmailVerificationToken,
    PasswordResetToken,
)
from app.services.auth import (
    hash_password,
    verify_password,
    get_current_user_allow_unverified,
)
from app.services.jwt_tokens import (
    generate_secret_token,
    hash_token,
    mint_access_token,
    mint_refresh_token,
    revoke_refresh_token,
    rotate_refresh_token,
    verify_refresh_token,
    RefreshTokenError,
)
from app.services.user_profile import serialize_user


router = APIRouter(prefix="/api/auth", tags=["auth"])


# ─── Request / response models ───────────────────────────────────────


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str = ""
    # Phase C wires hCaptcha verification on this field. Phase B accepts
    # the field optionally so the FE shape can be locked first. FE sends
    # the hCaptcha widget's response token here under this key.
    hcaptcha_token: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class VerifyEmailRequest(BaseModel):
    token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr
    hcaptcha_token: str | None = None


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


# ─── Cookie helpers ──────────────────────────────────────────────────


def _is_production() -> bool:
    return settings.ENV.lower() == "production"


def _set_access_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=_is_production(),
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=_is_production(),
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")


# ─── Endpoints ───────────────────────────────────────────────────────


@router.post("/register", status_code=201)
def register(req: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    if len(req.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(400, "Email already registered")

    # TODO F-310 Phase C: hCaptcha verify via app.services.captcha.verify_hcaptcha
    # TODO F-310 Phase D: /auth rate-limit middleware

    user = User(
        email=req.email,
        hashed_password=hash_password(req.password),
        full_name=req.full_name,
        # email_verified_at stays NULL — Decision 4 gate. Verification
        # email send wires up in Phase C; the token row exists from
        # the helper below.
        subscription_tier="free",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create the email-verification token row. Raw token returned here is
    # what Phase C will email; Phase B keeps it server-side only (no
    # response leakage — verification flow is broken until Phase C sends
    # the email, which is the intentional sequencing).
    _, _token_hash = _create_email_verification_token(db, user.id)

    # Issue both tokens so the FE can land on the "check your email" page
    # while still being authenticated enough to call /verify-email/resend.
    access = mint_access_token(user.email)
    refresh, _ = mint_refresh_token(db, user_id=user.id, email=user.email)

    _set_access_cookie(response, access)
    _set_refresh_cookie(response, refresh)

    return {
        "access_token": access,
        "user": serialize_user(user),
    }


@router.post("/login")
def login(req: LoginRequest, response: Response, db: Session = Depends(get_db)):
    # TODO F-310 Phase D: /auth rate-limit (5 attempts / 15min / IP +
    # exponential backoff + 10-attempt lockout).
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(401, "Invalid credentials")

    access = mint_access_token(user.email)
    refresh, _ = mint_refresh_token(db, user_id=user.id, email=user.email)

    _set_access_cookie(response, access)
    _set_refresh_cookie(response, refresh)

    return {
        "access_token": access,
        "user": serialize_user(user),
    }


@router.post("/refresh")
async def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Rotate refresh token + reissue access token. Reads refresh from
    cookie. On replay (presenting an already-rotated refresh), the
    entire chain is invalid — caller redirects to login."""
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(401, "No refresh token")

    try:
        _, old_row = await verify_refresh_token(db, refresh_token)
    except RefreshTokenError as e:
        _clear_auth_cookies(response)
        raise HTTPException(401, f"Invalid refresh: {e}")

    user = db.query(User).filter(User.id == old_row.user_id).first()
    if user is None:
        _clear_auth_cookies(response)
        raise HTTPException(401, "User not found")

    new_refresh, _ = await rotate_refresh_token(db, old_row=old_row, email=user.email)
    new_access = mint_access_token(user.email)

    _set_access_cookie(response, new_access)
    _set_refresh_cookie(response, new_refresh)

    return {"access_token": new_access}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_allow_unverified),
):
    """Revoke the active refresh + clear both cookies."""
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        try:
            _, old_row = await verify_refresh_token(db, refresh_token)
            await revoke_refresh_token(db, jti=old_row.jti)
        except RefreshTokenError:
            # Already invalid — nothing to revoke. Still clear cookies.
            pass
    _clear_auth_cookies(response)
    return {"message": "Logged out"}


@router.get("/me")
def me(user: User = Depends(get_current_user_allow_unverified)):
    """Returns serialized user — INCLUDING `email_verified` boolean
    so the FE can render the verification banner for unverified users."""
    return serialize_user(user)


@router.post("/verify-email")
def verify_email(
    req: VerifyEmailRequest,
    db: Session = Depends(get_db),
):
    """Consume a verification token: verify it exists, isn't expired,
    isn't already consumed; mark user.email_verified_at = NOW()."""
    token_hash = hash_token(req.token)
    row = (
        db.query(EmailVerificationToken)
        .filter(EmailVerificationToken.token_hash == token_hash)
        .first()
    )
    if row is None:
        raise HTTPException(400, "Invalid token")
    if row.consumed_at is not None:
        raise HTTPException(400, "Token already used")
    if row.expires_at <= datetime.datetime.utcnow():
        raise HTTPException(400, "Token expired")

    user = db.query(User).filter(User.id == row.user_id).first()
    if user is None:
        # Edge case: user deleted between token issue + click.
        raise HTTPException(400, "User not found")

    now = datetime.datetime.utcnow()
    row.consumed_at = now
    if user.email_verified_at is None:
        user.email_verified_at = now
    db.commit()
    return {"message": "Email verified"}


@router.post("/verify-email/resend")
def verify_email_resend(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_allow_unverified),
):
    """Regenerate the verification token for the current user. Phase C
    wires the email send; Phase B creates the token row only."""
    if user.email_verified_at is not None:
        raise HTTPException(
            409,
            detail={"code": "already_verified", "message": "Email already verified"},
        )
    # Consume any outstanding tokens so only the freshest is valid.
    _consume_outstanding_email_tokens(db, user.id)
    _create_email_verification_token(db, user.id)
    # TODO F-310 Phase C: app.services.email.send_email(...) the link.
    return {"message": "Verification email sent"}


@router.post("/password-reset/request")
def password_reset_request(
    req: PasswordResetRequest,
    db: Session = Depends(get_db),
):
    """Generate a password-reset token for the user (if exists). Returns
    200 unconditionally to prevent email enumeration. Phase C wires the
    email send. Phase D rate-limits this endpoint."""
    # TODO F-310 Phase C: hCaptcha verify on req.hcaptcha_token
    # TODO F-310 Phase D: /auth rate-limit
    user = db.query(User).filter(User.email == req.email).first()
    if user is not None:
        _consume_outstanding_password_reset_tokens(db, user.id)
        _create_password_reset_token(db, user.id)
        # TODO F-310 Phase C: send the email
    return {"message": "If the email is registered, a reset link has been sent"}


@router.post("/password-reset/confirm")
def password_reset_confirm(
    req: PasswordResetConfirm,
    db: Session = Depends(get_db),
):
    """Consume a password-reset token + update the user's hashed_password."""
    if len(req.new_password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    token_hash = hash_token(req.token)
    row = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == token_hash)
        .first()
    )
    if row is None:
        raise HTTPException(400, "Invalid token")
    if row.consumed_at is not None:
        raise HTTPException(400, "Token already used")
    if row.expires_at <= datetime.datetime.utcnow():
        raise HTTPException(400, "Token expired")

    user = db.query(User).filter(User.id == row.user_id).first()
    if user is None:
        raise HTTPException(400, "User not found")

    user.hashed_password = hash_password(req.new_password)
    row.consumed_at = datetime.datetime.utcnow()
    db.commit()
    return {"message": "Password reset"}


# ─── Internal helpers ────────────────────────────────────────────────


_EMAIL_VERIFICATION_TTL_HOURS = 24
_PASSWORD_RESET_TTL_HOURS = 1


def _create_email_verification_token(db: Session, user_id: int) -> tuple[str, str]:
    """Generate + persist an email verification token row. Returns
    (raw_token, token_hash). Caller decides whether to use the raw
    token (Phase C: email it) or discard it (Phase B: testing only)."""
    raw, token_hash = generate_secret_token()
    expires_at = (
        datetime.datetime.utcnow()
        + datetime.timedelta(hours=_EMAIL_VERIFICATION_TTL_HOURS)
    )
    db.add(EmailVerificationToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    ))
    db.commit()
    return raw, token_hash


def _consume_outstanding_email_tokens(db: Session, user_id: int) -> None:
    """Mark all non-consumed, non-expired verification tokens for this
    user as consumed. Used on resend to keep only the freshest valid."""
    now = datetime.datetime.utcnow()
    (
        db.query(EmailVerificationToken)
        .filter(
            EmailVerificationToken.user_id == user_id,
            EmailVerificationToken.consumed_at.is_(None),
            EmailVerificationToken.expires_at > now,
        )
        .update({EmailVerificationToken.consumed_at: now}, synchronize_session=False)
    )
    db.commit()


def _create_password_reset_token(db: Session, user_id: int) -> tuple[str, str]:
    raw, token_hash = generate_secret_token()
    expires_at = (
        datetime.datetime.utcnow()
        + datetime.timedelta(hours=_PASSWORD_RESET_TTL_HOURS)
    )
    db.add(PasswordResetToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    ))
    db.commit()
    return raw, token_hash


def _consume_outstanding_password_reset_tokens(db: Session, user_id: int) -> None:
    now = datetime.datetime.utcnow()
    (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.user_id == user_id,
            PasswordResetToken.consumed_at.is_(None),
            PasswordResetToken.expires_at > now,
        )
        .update({PasswordResetToken.consumed_at: now}, synchronize_session=False)
    )
    db.commit()
