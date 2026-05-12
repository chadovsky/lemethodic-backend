"""F-310 Phase D — Stripe webhook endpoint shell.

POST /api/stripe/webhook

Reads raw body bytes (NOT FastAPI-parsed JSON — Stripe signs the exact
byte sequence; re-encoding breaks signature verification). Pulls the
`Stripe-Signature` header. Calls webhooks.verify_stripe_webhook() —
returns parsed event dict or raises WebhookSignatureError.

On success: log the event type + id, return 200. **No DB writes. No
entitlement changes. No side effects.** P-106 (Stripe SDK integration)
owns real event handling + an audit table for replay if needed.

This shell exists now (pre-P-106) so:
1. The verify_stripe_webhook helper has a real consumer for Phase E smoke.
2. When P-106 lands, it extends this handler with type-keyed dispatching
   rather than introducing a new route + reasoning about the verification
   pattern from scratch.

Why no audit table at MVP: B-100 is 2-6 weeks out (Stripe Atlas LLC
formation timeline). Stripe webhooks won't fire at us until then.
Pre-emptively persisting events would introduce a migration we'll
likely reshape when P-106 designs the audit log with full event-schema
awareness. Phase D's "option (a) — parse + log + ack 200 only" was
locked by Chadi 2026-05-12.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request, status

from app.services.webhooks import verify_stripe_webhook, WebhookSignatureError


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stripe", tags=["stripe"])


@router.post("/webhook")
async def stripe_webhook(request: Request) -> dict:
    """Stripe webhook handler — placeholder for P-106.

    Verifies HMAC signature. Logs event type + id. ACKs 200.
    Never raises on payload contents (Stripe expects 2xx within ~30s;
    repeat-deliveries pile up otherwise).

    Returns 400 only when signature verification fails. Stripe will
    retry with backoff on 4xx; our HMAC verifier rejecting means the
    signing secret is misconfigured (env var) or the request is from
    an attacker, not from Stripe.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = verify_stripe_webhook(payload, sig_header)
    except WebhookSignatureError as e:
        # Log type only, NOT payload (an attacker forcing 400s shouldn't
        # see their probes echoed back into our logs as content).
        logger.warning(
            "F-310 stripe_webhook: signature rejected (%s)", type(e).__name__,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid signature")

    event_type = event.get("type", "<unknown>")
    event_id = event.get("id", "<unknown>")
    logger.info(
        "F-310 stripe_webhook: received event type=%s id=%s (no handler — P-106 placeholder)",
        event_type, event_id,
    )
    return {"received": True, "type": event_type}
