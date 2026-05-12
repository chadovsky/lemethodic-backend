"""F-311 Phase D — per-user-per-day diagnostic-session quota.

Distinct from F-310's auth rate limiter (which is per-IP-per-window).
This one is per-user-per-UTC-day, tier-aware.

Tier quotas (Decision 4):
  free          → 5  diagnostic sessions/day
  subscription  → 30
  sprint        → 60
  premium       → unlimited (Redis bypassed)

Quota scope (Q2c confirmed 2026-05-12): the 3 analysis endpoints that
trigger sonnet-tier work:
  POST /api/recordings/upload      (Tâche 3 + finalization for T1/T2 audio)
  POST /api/conversations/end       (Tâche 1/2 analysis trigger)
  POST /api/writing/submit          (writing analysis)

NOT counted (intentional): examiner conversation turns, argument
assistant, transcript suggestions. Those are mid-session interactions
or warm-path utilities.

Redis key: f311:diag:{user_id}:{YYYY-MM-DD-UTC} with 25h TTL.
On Redis-down: fail-open (logs WARNING, allows the call) — same
availability-over-strictness tradeoff as F-310.
"""
from __future__ import annotations

import datetime
import logging

from fastapi import Depends, HTTPException, status

from app.config import settings
from app.models.models import User
from app.services.auth import get_current_user
from app.services.redis_client import get_redis


logger = logging.getLogger(__name__)


def _tier_quota(tier: str) -> int | None:
    """Return the daily quota for a tier. None = unlimited (premium).

    Defensive: unknown tier falls through to free quota. F-310's tier
    DI placeholder always returns "free" today; P-105 populates real
    values later.
    """
    if tier == "premium":
        return None
    if tier == "sprint":
        return settings.DIAGNOSTIC_RATE_LIMIT_SPRINT
    if tier == "subscription":
        return settings.DIAGNOSTIC_RATE_LIMIT_SUBSCRIPTION
    return settings.DIAGNOSTIC_RATE_LIMIT_FREE


def _today_utc() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%d")


async def check_diagnostic_quota(user_id: int, tier: str) -> tuple[bool, int, int | None]:
    """Increment + check the user's daily diagnostic counter.

    Returns (allowed, current_count, quota_limit).
    - allowed=True: under quota; the increment is counted toward today.
    - allowed=False: over quota; current_count reflects post-increment.
    - quota_limit=None: premium tier — Redis check skipped entirely.

    Fail-open on Redis errors (returns allowed=True with warning).
    """
    quota = _tier_quota(tier)
    if quota is None:
        # Premium — unlimited. No Redis hit.
        return True, 0, None

    key = f"f311:diag:{user_id}:{_today_utc()}"
    try:
        r = get_redis()
        pipe = r.pipeline()
        pipe.incr(key)
        pipe.expire(key, 25 * 60 * 60)  # 25h slack for clock skew + UTC drift
        count, _ = await pipe.execute()
        count_int = int(count) if count is not None else 0
        return (count_int <= quota), count_int, quota
    except Exception as e:
        logger.warning(
            "F-311 diagnostic_rate_limit: fail-open user_id=%s tier=%s err=%s",
            user_id, tier, e,
        )
        return True, 0, quota


async def diagnostic_quota_required(
    user: User = Depends(get_current_user),
) -> User:
    """FastAPI async dependency: increments + checks the daily
    diagnostic quota for the current user. Raises 429 on exhaustion
    with structured detail + Retry-After header (seconds until UTC
    midnight).

    Returns the User on success so call sites can chain:

        @router.post("/upload")
        async def upload(
            ...,
            user: User = Depends(diagnostic_quota_required),
        ):
            ...

    Wraps F-310's get_current_user — email-verified user is required
    AND daily-quota-checked in a single dependency. Premium tier
    short-circuits the Redis hit entirely.
    """
    tier = getattr(user, "subscription_tier", "free") or "free"
    allowed, count, quota = await check_diagnostic_quota(user.id, tier)
    if not allowed:
        # Compute seconds until UTC midnight for Retry-After.
        now = datetime.datetime.utcnow()
        tomorrow = (now + datetime.timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0,
        )
        retry_after = int((tomorrow - now).total_seconds())
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "diagnostic_quota_exceeded",
                "tier": tier,
                "limit": quota,
                "current": count,
                "retry_after_seconds": retry_after,
            },
            headers={"Retry-After": str(retry_after)},
        )
    return user
