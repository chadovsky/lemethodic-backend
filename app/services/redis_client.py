"""F-310 Phase A — async Redis singleton.

Shared across the app for:
  - F-310 rate-limit counters on /auth endpoints
  - F-310 refresh-token revocation set (jti membership check)
  - F-311 (downstream) per-user diagnostic-rate counters keyed by tier

Lazy-init on first use; the module-level singleton stays alive for the
process lifetime. FastAPI lifespan can hook startup/shutdown later if
we need stricter pool lifecycle.
"""
from __future__ import annotations

import logging

import redis.asyncio as redis_async

from app.config import settings


logger = logging.getLogger(__name__)


_client: redis_async.Redis | None = None


def get_redis() -> redis_async.Redis:
    """Return the module-level async Redis client. Lazy-initialized.

    Callers MUST NOT close this client — it is shared across the app.
    """
    global _client
    if _client is None:
        _client = redis_async.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
        logger.info("F-310 redis: client initialized url=%s", settings.REDIS_URL)
    return _client


async def healthcheck() -> bool:
    """Ping Redis. Returns True iff reachable.

    Wired into the /health endpoint by Phase B (currently unused).
    Never raises — Redis-unreachable returns False so the caller can
    decide whether to fail open or fail closed.
    """
    try:
        return await get_redis().ping()
    except Exception as e:
        logger.warning("F-310 redis: healthcheck failed: %s", e)
        return False
