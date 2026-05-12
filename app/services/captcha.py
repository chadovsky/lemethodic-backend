"""F-310 Phase A — hCaptcha verification.

Verifies an hCaptcha response token against hcaptcha.com/siteverify.
Fail-closed: any error, missing token, or missing secret returns False.

Wired by Phase C into:
  - POST /api/auth/register
  - POST /api/auth/password-reset/request

FE side renders the widget using settings.HCAPTCHA_SITEKEY (publicly
exposed). BE side verifies with settings.HCAPTCHA_SECRET (private).
"""
from __future__ import annotations

import logging

import httpx

from app.config import settings


logger = logging.getLogger(__name__)


HCAPTCHA_VERIFY_URL = "https://hcaptcha.com/siteverify"


async def verify_hcaptcha(
    token: str | None,
    remote_ip: str | None = None,
) -> bool:
    """Verify an hCaptcha response token via hCaptcha's siteverify API.

    Returns True iff (a) the secret is configured, (b) the token is
    present, and (c) hCaptcha confirms `success: true`. Any other
    state — network error, malformed response, missing secret — returns
    False (fail-closed). Errors logged at WARNING.

    Args:
        token: the `h-captcha-response` value posted by the FE widget.
        remote_ip: optional client IP for hCaptcha's fraud heuristics.
    """
    if not token:
        return False
    if not settings.HCAPTCHA_SECRET:
        logger.warning("F-310 hCaptcha: HCAPTCHA_SECRET unset; rejecting")
        return False

    data: dict[str, str] = {
        "secret": settings.HCAPTCHA_SECRET,
        "response": token,
    }
    if remote_ip:
        data["remoteip"] = remote_ip

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(HCAPTCHA_VERIFY_URL, data=data)
            resp.raise_for_status()
            body = resp.json()
        return bool(body.get("success"))
    except Exception as e:
        logger.warning("F-310 hCaptcha: verify failed: %s", e)
        return False
