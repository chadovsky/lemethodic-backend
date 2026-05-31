"""F-310 Phase C — Redis-backed dual-window rate limiter for /auth routes.
F-401 — same limiter extended to AI endpoints, keyed by user_id.

Pattern: fixed-window counter (per key × per window-start timestamp).
Two windows in series — both must pass:

  Auth endpoints (IP-keyed):
    short window: 5 attempts / 15 min  → first-line throttle
    long window:  10 attempts / 1 hour → lockout-tier (catches slow spray)

  AI endpoints (user_id-keyed, configurable per endpoint):
    short window: X / 1 min  → burst protection
    long window:  Y / 1 hour → abuse ceiling

On exceed → HTTP 429 with `Retry-After` header = remaining seconds of the
exceeded window.

Fail-open on Redis unreachable: if get_redis() / INCR raise, we log at
WARNING and allow the request. The trade-off is: never lock everyone out
when Redis is down. The DB-side credentials check (auth) or the
diagnostic quota (AI) is the next line of defense.

Usage (auth, IP-keyed):

    from app.services.rate_limit import auth_rate_limit

    @router.post("/login", dependencies=[Depends(auth_rate_limit("login"))])
    def login(...): ...

Usage (AI, user_id-keyed):

    from app.services.rate_limit import ai_rate_limit

    @router.post("/transcribe", dependencies=[Depends(ai_rate_limit(
        "transcribe", short_max=20, long_max=200,
    ))])
    async def transcribe(...): ...

The auth dependency reads the client IP from `request.client.host`.
AI dependency reads user_id via get_current_user (FastAPI caches the
dependency per-request, so no double auth check when the endpoint also
declares user: User = Depends(get_current_user)).
"""
from __future__ import annotations

import logging
import time
from typing import Callable

from fastapi import Depends, HTTPException, Request, status

from app.config import settings
from app.services.redis_client import get_redis


logger = logging.getLogger(__name__)


# Default limits per F-310 Decision 4. Override per-endpoint via factory.
_SHORT_MAX = 5
_SHORT_WINDOW = 15 * 60          # 15 min
_LONG_MAX = 10
_LONG_WINDOW = 60 * 60           # 1 hour


def _client_ip(request: Request) -> str:
    """Resolve the real client IP.

    F-310.1 (2026-05-12): in production behind DO App Platform's load
    balancer, request.client.host is the LB's IP, not the user's.
    Without this fix all users share one rate-limit bucket per LB IP,
    which breaks the moment a handful of concurrent users hit the
    rate-limited endpoints (one user triggers the limit; everyone is
    blocked).

    Trust model:
      - When ENV != "production", trust request.client.host as the real
        client (local dev: no proxy between client and uvicorn).
      - When ENV == "production", DO App Platform inserts the real
        client IP into X-Forwarded-For. The chain is
        `[client-spoofed-XFF, ..., real-client-IP-inserted-by-DO]`.
        The LAST entry is the one DO inserted, which is the trusted
        real-client IP. Earlier entries may be attacker-spoofed and
        must NOT be trusted.

    The "trust last entry" pattern is correct ONLY because DO is a
    single trusted proxy hop. If a CDN (Cloudflare etc.) sits in front
    of DO, the trust position shifts and this needs revisiting.

    `request.client` is None in some test contexts; default to a stable
    sentinel so the test path doesn't crash.
    """
    if settings.ENV.lower() == "production":
        xff = request.headers.get("x-forwarded-for")
        if xff:
            parts = [p.strip() for p in xff.split(",") if p.strip()]
            if parts:
                return parts[-1]
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


async def _check_window(
    redis,
    *,
    key: str,
    max_attempts: int,
    window_seconds: int,
) -> tuple[bool, int]:
    """INCR the counter for the current window; check against threshold.

    Returns (allowed, retry_after_seconds).
    `allowed=True` → under threshold.
    `allowed=False` → at-or-over threshold; retry_after is the seconds
    until the current window ends.
    """
    now = int(time.time())
    window_start = now - (now % window_seconds)
    full_key = f"f310:ratelimit:{key}:{window_start}"

    pipe = redis.pipeline()
    pipe.incr(full_key)
    pipe.expire(full_key, window_seconds + 60)  # +1min slack for clock skew
    count, _ = await pipe.execute()

    if count > max_attempts:
        retry_after = (window_start + window_seconds) - now
        return False, max(1, retry_after)
    return True, 0


def auth_rate_limit(
    endpoint_key: str,
    *,
    short_max: int = _SHORT_MAX,
    short_window: int = _SHORT_WINDOW,
    long_max: int = _LONG_MAX,
    long_window: int = _LONG_WINDOW,
) -> Callable:
    """FastAPI dependency factory. Returns a dep that enforces dual-window
    rate limits on the given endpoint_key, keyed by client IP.

    On exceed → raise HTTPException(429) with Retry-After header.
    On Redis-down → fail-open with a WARNING log; the request proceeds.

    `endpoint_key` should be short + stable, e.g. "login", "register",
    "password_reset_request". Used as part of the Redis key.
    """
    async def _dep(request: Request) -> None:
        ip = _client_ip(request)
        short_key = f"{endpoint_key}:short:{ip}"
        long_key = f"{endpoint_key}:long:{ip}"

        try:
            redis = get_redis()
            short_ok, short_retry = await _check_window(
                redis,
                key=short_key,
                max_attempts=short_max,
                window_seconds=short_window,
            )
            if not short_ok:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "code": "rate_limit_exceeded",
                        "window": "short",
                        "retry_after_seconds": short_retry,
                    },
                    headers={"Retry-After": str(short_retry)},
                )
            long_ok, long_retry = await _check_window(
                redis,
                key=long_key,
                max_attempts=long_max,
                window_seconds=long_window,
            )
            if not long_ok:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "code": "rate_limit_lockout",
                        "window": "long",
                        "retry_after_seconds": long_retry,
                    },
                    headers={"Retry-After": str(long_retry)},
                )
        except HTTPException:
            # Limit-exceeded path — re-raise.
            raise
        except Exception as e:
            # Redis-down or any other infra error — fail-open.
            logger.warning(
                "F-310 rate_limit: fail-open on %s (ip=%s) due to %s",
                endpoint_key, ip, e,
            )
            return

    return _dep


# ── F-401: per-user rate limiter for AI endpoints ─────────────────────────────

def ai_rate_limit(
    endpoint_key: str,
    *,
    short_max: int,
    short_window: int = 60,       # 1 minute default
    long_max: int,
    long_window: int = 3600,      # 1 hour default
) -> Callable:
    """FastAPI dependency factory for per-user dual-window rate limits on
    AI endpoints. Keys by user_id so the ceiling is per-account, not
    per-IP (a shared IP like a corporate NAT must not block all users).

    On exceed: 429 with Retry-After = remaining seconds of the window.
    On Redis-down: fail-open (logs WARNING; request proceeds).

    Usage:

        @router.post("/transcribe", dependencies=[Depends(ai_rate_limit(
            "transcribe", short_max=20, long_max=200,
        ))])
        async def transcribe(...): ...
    """
    from app.models.models import User  # local import avoids module-load cycle
    from app.services.auth import get_current_user  # same reason

    async def _dep(user: User = Depends(get_current_user)) -> None:
        key_base = f"f401:ai:{endpoint_key}:u:{user.id}"
        try:
            redis = get_redis()
            short_ok, short_retry = await _check_window(
                redis,
                key=f"{key_base}:s",
                max_attempts=short_max,
                window_seconds=short_window,
            )
            if not short_ok:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "code": "ai_rate_limit_exceeded",
                        "window": "short",
                        "endpoint": endpoint_key,
                        "retry_after_seconds": short_retry,
                    },
                    headers={"Retry-After": str(short_retry)},
                )
            long_ok, long_retry = await _check_window(
                redis,
                key=f"{key_base}:l",
                max_attempts=long_max,
                window_seconds=long_window,
            )
            if not long_ok:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "code": "ai_rate_limit_lockout",
                        "window": "long",
                        "endpoint": endpoint_key,
                        "retry_after_seconds": long_retry,
                    },
                    headers={"Retry-After": str(long_retry)},
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(
                "F-401 ai_rate_limit: fail-open on %s (user_id=%s) due to %s",
                endpoint_key, user.id, e,
            )

    return _dep
