"""Auth dependencies + password hashing.

F-310 Phase B (2026-05-12):
  - get_current_user now enforces email_verified_at IS NOT NULL on
    protected routes (Decision 4: hard gate on new registrations,
    grandfathered for soft-beta accounts via migration backfill).
  - get_current_user_allow_unverified added for endpoints that must
    work for unverified users (/me, /logout, /verify-email/resend).
  - JWT mint/verify lives in app/services/jwt_tokens.py (split out).
    create_access_token() kept here as a thin wrapper for backward
    compat with smoke scripts; new code imports from jwt_tokens.
"""
from passlib.context import CryptContext
from jose import JWTError
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import User
from app.services.jwt_tokens import mint_access_token, verify_access_token

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password[:72])


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain[:72], hashed)


def create_access_token(data: dict) -> str:
    """Legacy wrapper around jwt_tokens.mint_access_token.

    Kept for compat with smoke scripts that import this name (e.g.
    scripts/smoke_v016a.py). New code imports mint_access_token
    directly from app.services.jwt_tokens.

    Args:
        data: dict with at minimum {"sub": email}. Other keys are
              ignored — the new minter constructs the payload itself.
    """
    email = data.get("sub")
    if not email:
        raise ValueError("create_access_token requires data['sub'] = email")
    return mint_access_token(email)


def _resolve_token(request: Request) -> str | None:
    """Pull the access token from cookie or Authorization header. Cookie
    wins (the legacy path); Bearer is honored for smoke scripts and
    legacy mobile clients."""
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization")
        if auth and auth.startswith("Bearer "):
            token = auth[7:]
    return token


def _load_user_from_token(token: str | None, db: Session) -> User:
    """Verify the token, load the User row. Raises HTTPException(401)
    on any failure path. Does NOT enforce email_verified_at — that
    layer is the caller's job (get_current_user adds it; the
    allow_unverified variant doesn't)."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    try:
        payload = verify_access_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """Resolve the current user from the access token AND enforce that
    their email is verified (F-310 Phase B Decision 4 gate).

    Returns 401 on missing/invalid token + user-not-found.
    Returns 403 with {"code": "email_not_verified"} when the user
    exists but has email_verified_at IS NULL — soft-beta accounts
    are grandfathered as verified via migration backfill, so any
    NULL here is a post-2026-05-12 registration that hasn't clicked
    the verification email yet.

    Use get_current_user_allow_unverified() for endpoints that must
    work for unverified users (/me, /logout, /verify-email/resend).
    """
    token = _resolve_token(request)
    user = _load_user_from_token(token, db)
    if user.email_verified_at is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "email_not_verified",
                "message": "Email verification required",
            },
        )
    return user


def get_current_user_allow_unverified(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """Same as get_current_user but does NOT enforce email_verified_at.

    Use for the narrow set of endpoints that must remain reachable to
    unverified users so they can complete verification: /me (to see
    the unverified state), /logout, /verify-email/resend.

    Returns 401 on missing/invalid token + user-not-found, same as
    the verified variant. NEVER returns 403 for unverified state.
    """
    token = _resolve_token(request)
    return _load_user_from_token(token, db)


def get_current_user_optional(request: Request, db: Session = Depends(get_db)):
    """Returns user or None — for pages that work both ways.

    F-310 Phase B note: this variant also does NOT enforce
    email_verified_at. If a route needs the verified-gate, it should
    use get_current_user via Depends, not this helper. The optional
    helper is for surfaces that render differently for anonymous vs
    logged-in users (e.g. landing page personalization)."""
    try:
        return _load_user_from_token(_resolve_token(request), db)
    except HTTPException:
        return None


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
