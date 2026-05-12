"""F-310 Phase A — Stripe webhook HMAC verification.

Wraps stripe.Webhook.construct_event() so the verification + parsing
logic lives in one place. P-106 will import this when wiring real
event handling; Phase D wires the bare endpoint that uses this.

Stripe sends the signature in the `Stripe-Signature` request header.
The secret is set per-webhook in the Stripe dashboard and lives in
settings.STRIPE_WEBHOOK_SECRET. Rotation is operational (Chadi via
dashboard + env update) — not a code concern.

NEVER trust the payload after WebhookSignatureError is raised.
"""
from __future__ import annotations

import logging

import stripe

from app.config import settings


logger = logging.getLogger(__name__)


class WebhookSignatureError(Exception):
    """Raised when the Stripe-Signature header is missing, malformed,
    or doesn't validate against the configured webhook secret.

    Caller should return HTTP 400 and log the failure but MUST NOT
    log the payload (an attacker forcing 400s can use logs as a
    side channel).
    """


def verify_stripe_webhook(
    payload: bytes,
    signature_header: str | None,
) -> dict:
    """Verify a Stripe webhook payload + signature header.

    Returns the parsed event dict on success. Raises
    WebhookSignatureError on any failure — bad signature, missing
    header, no configured secret, malformed payload.

    Args:
        payload: the RAW request body bytes (must NOT be re-encoded
            JSON — Stripe signs the exact byte sequence).
        signature_header: the `Stripe-Signature` header value.
    """
    if not signature_header:
        raise WebhookSignatureError("Missing Stripe-Signature header")
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise WebhookSignatureError("Stripe webhook secret not configured")
    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=signature_header,
            secret=settings.STRIPE_WEBHOOK_SECRET,
        )
    except Exception as e:
        # stripe.Webhook.construct_event raises a few different exception
        # classes depending on stripe-python version (SignatureVerificationError,
        # ValueError, etc.). The common contract is "any exception = reject"
        # so we coerce them all to WebhookSignatureError.
        raise WebhookSignatureError(
            f"Stripe construct_event failed: {type(e).__name__}"
        ) from e
    # stripe.Event-like dict; treat as plain dict for downstream.
    return dict(event)
