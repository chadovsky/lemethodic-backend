"""F-310 Phase C — Redis-backed dual-window rate limiter for /auth routes.

Pattern: fixed-window counter (per IP × per endpoint × per window-start
timestamp). Two windows in series — both must pass:

  short window: 5 attempts / 15 min  → first-line throttle
  long window:  10 attempts / 1 hour → lockout-tier (catches slow spray)

On exceed → HTTP 429 with `Retry-After` header = remaining seconds of the
exceeded window.

Fail-open on Redis unreachable: if get_redis() / INCR raise, we log at
WARNING and allow the request. The trade-off is: never lock everyone out
of auth when Redis is down (auth-flow availability > rate-limit
strictness). The DB-side credentials check is the next line of defense.

Usage:

    from app.services.rate_limit import auth_rate_limit

    @router.post("/login", dependencies=[Depends(auth_rate_limit("login"))])
    def login(...): ...

The dependency reads the client IP from `request.client.host`. Behind a
proxy, App Platform / Vercel populate `X-Forwarded-For`; that's not used
here — FastAPI's `request.client.host` reflects the last hop. Acceptable
for soft beta (single tier of proxying). When we add a CDN with multiple
hops, switch to a TrustedHostMiddleware + parse `X-Forwarded-For` last
entry.
"""
from __future__ import annotations

import logging
import time
from typing import Callable

from fastapi import Depends, HTTPException, Request, status

from app.services.redis_client import get_redis


logger = logging.getLogger(__name__)


# Default limits per F-310 Decision 4. Override per-endpoint via factory.
_SHORT_MAX = 5
_SHORT_WINDOW = 15 * 60          # 15 min
_LONG_MAX = 10
_LONG_WINDOW = 60 * 60           # 1 hour


def _client_ip(request: Request) -> str:
    """Best-effort client IP. Behind a single proxy this is the proxy's
    IP — App Platform terminates at the load balancer and forwards via
    X-Forwarded-For. For soft beta we accept the simpler model.

    `request.client` is None in some test contexts; default to a stable
    sentinel so the test path doesn't crash."""
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
