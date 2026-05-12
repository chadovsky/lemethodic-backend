"""Shared user → dict serializer.

Both /api/auth/me and /api/users/me return the same payload shape. Keeping one
builder avoids drift between the two endpoints when new profile fields land.
"""
from app.models.models import User


def serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "is_admin": bool(user.is_admin),
        # Onboarding fields — null for users who haven't completed the flow.
        "target_level": user.target_level,
        "exam_profile": user.exam_profile,
        "exam_date": user.exam_date.isoformat() if user.exam_date else None,
        "goal": user.goal,
        "current_level": user.current_level,
        # Exposed as `interface_language` at the API boundary even though the
        # column is still called ui_language in the DB.
        "interface_language": user.ui_language,
        # F-310 Phase B — auth-hardening surface for FE.
        # `email_verified` is a bool the FE uses to render the verify-email
        # banner; the raw timestamp is internal-only.
        "email_verified": user.email_verified_at is not None,
        # Subscription tier + status drive the paywall + tier-aware UI.
        # `subscription_tier` is NOT NULL (default 'free'); `subscription_status`
        # is NULL until P-105 creates a Stripe subscription.
        "subscription_tier": getattr(user, "subscription_tier", "free") or "free",
        "subscription_status": getattr(user, "subscription_status", None),
    }
