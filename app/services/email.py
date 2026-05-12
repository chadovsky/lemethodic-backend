"""F-310 Phase A — async transactional email send.

Provider-pluggable via settings.EMAIL_PROVIDER. Phase A implements
"resend" only (per Chadi's 2026-05-12 sign-off: Resend default, clean
API, 3K/month free tier, env-pluggable so we can swap later).

Used by:
  - email_verification.py (Phase C) — registration verification token
  - password_reset.py (Phase C) — password-reset token

Fail-quiet contract: any send failure returns False and logs at
WARNING. Callers decide whether the user-facing operation fails or
proceeds (typically: email-verification failure does NOT block the
registration response, but DOES log loud so we can replay).
"""
from __future__ import annotations

import logging

import httpx

from app.config import settings


logger = logging.getLogger(__name__)


RESEND_API_URL = "https://api.resend.com/emails"


class EmailSendError(Exception):
    """Reserved for code paths that want fail-loud behavior. Phase A
    callers don't raise this directly — the send_email() helper catches
    everything internally. Lift the catch in callers that need it."""


async def send_email(
    *,
    to: str | list[str],
    subject: str,
    html: str,
    text: str | None = None,
    reply_to: str | None = None,
) -> bool:
    """Send a transactional email. Returns True on success, False on
    any failure (including missing config). Errors are logged but
    not raised.

    Phase A: Resend only. Adding a provider = extending this function;
    the signature stays stable so callers don't change.

    Args:
        to: single recipient address or list.
        subject: email subject line.
        html: HTML body (Resend requires either html or text).
        text: optional plain-text alternative.
        reply_to: optional Reply-To header.
    """
    provider = settings.EMAIL_PROVIDER
    if provider != "resend":
        logger.warning(
            "F-310 email: provider=%r not implemented (supported: resend)",
            provider,
        )
        return False
    if not settings.RESEND_API_KEY:
        logger.warning("F-310 email: RESEND_API_KEY unset; cannot send")
        return False

    payload: dict = {
        "from": f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM_ADDRESS}>",
        "to": [to] if isinstance(to, str) else to,
        "subject": subject,
        "html": html,
    }
    if text:
        payload["text"] = text
    if reply_to:
        payload["reply_to"] = reply_to

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                RESEND_API_URL,
                headers={
                    "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
        return True
    except Exception as e:
        logger.warning(
            "F-310 email send failed: provider=resend to=%s subject=%r err=%s",
            to, subject, e,
        )
        return False
