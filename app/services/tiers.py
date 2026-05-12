"""F-310 Phase A — opt-in subscription-tier gate via FastAPI DI.

Usage on protected routes:

    from app.services.tiers import require_tier

    @router.get("/premium-feature")
    def premium_only(user = Depends(require_tier("premium"))):
        ...

Phase A placeholder: returns "free" for ALL users until P-105 populates
User.subscription_tier. The DI shape stays stable so per-route adoption
is incremental — when P-105 lands and entitlement.py owns the resolution,
the resolver swaps to a real DB / Redis read with zero call-site changes.

Tier hierarchy (locked in B-100 + P-105 scope):
    free < subscription < sprint < premium

A user with tier=premium trivially passes require_tier("free") because
ranks are monotonic.
"""
from __future__ import annotations

from typing import Literal

from fastapi import Depends, HTTPException, status

from app.models.models import User
from app.services.auth import get_current_user


Tier = Literal["free", "subscription", "sprint", "premium"]


_TIER_RANK: dict[str, int] = {
    "free": 0,
    "subscription": 1,
    "sprint": 2,
    "premium": 3,
}


def _resolve_user_tier(user: User) -> str:
    """Resolve the effective tier for a user.

    Phase A placeholder: returns "free" for all users. P-105 will swap
    this to `getattr(user, "subscription_tier", "free")` once the
    column is populated and entitlement.has_active_access() owns the
    trial-state logic. No call-site changes when that swap happens.
    """
    return "free"


def require_tier(min_tier: Tier):
    """FastAPI DI factory. Returns a dependency that raises HTTP 403
    if the current user's effective tier is below `min_tier`.

    The dependency itself returns the User object on success so call
    sites can chain:

        user: User = Depends(require_tier("subscription"))

    instead of `Depends(get_current_user)` + an inline tier check.

    403 body shape (FE contract):
        {
          "detail": {
            "code": "tier_insufficient",
            "required": "<min_tier>",
            "current": "<user's effective tier>"
          }
        }
    """
    required_rank = _TIER_RANK[min_tier]

    def _dep(user: User = Depends(get_current_user)) -> User:
        effective = _resolve_user_tier(user)
        user_rank = _TIER_RANK.get(effective, 0)
        if user_rank < required_rank:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "tier_insufficient",
                    "required": min_tier,
                    "current": effective,
                },
            )
        return user

    return _dep
