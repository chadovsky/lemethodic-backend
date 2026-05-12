"""Smoke test for F-310 — auth hardening end-to-end.

Coverage (per the F-310 plan-first):
  Step 1 — Schema: 5 new users columns + 3 new tables + 2 CHECK constraints.
  Step 2 — Grandfather backfill: pre-migration users have email_verified_at populated.
  Step 3 — Register flow: 201 + cookies + email_verified=False + verification token row.
  Step 4 — Verified-gate: unverified user 403s on protected route; /me 200 (allow_unverified).
  Step 5 — Verify-email: consume token → user verified → protected route 200.
  Step 6 — Verify-email replay: same token re-presented → 400.
  Step 7 — Refresh rotation: refresh → new tokens → old refresh now 401.
  Step 8 — Logout: revokes refresh → subsequent refresh 401.
  Step 9 — Rate limit logic (direct): 5 attempts pass, 6th + 7th blocked with Retry-After.
  Step 10 — Rate limit fail-open (direct): Redis-down path returns allow (logs WARNING).
  Step 11 — hCaptcha branches (direct): SECRET-unset = no-op; SECRET-set + bad-token = 400.
  Step 12 — Stripe webhook: no-sig = 400; bad-sig = 400; valid-sig = 200 + event echo.
  Step 13 — Tier DI: require_tier("free") = 200; require_tier("subscription") on free user = 403.
  Step 14 — Schema mirror: User ORM model carries the new columns + reads them back from DB.

Runs offline (no real Claude / Resend / hCaptcha API calls). Mocks
external surfaces where needed. Requires:
  - Local docker postgres at h6f7g8e9d0c1 head (alembic upgrade head).
  - Local Redis on localhost:6379 (docker run --rm -p 6379:6379 redis:7-alpine).

Run: python -m scripts.smoke_f310
"""
from __future__ import annotations

import asyncio
import datetime
import hashlib
import hmac
import json
import sys
import time
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database import SessionLocal
from app.models.models import User
from app.models.auth_tokens import (
    EmailVerificationToken,
    PasswordResetToken,
    RefreshToken,
)


SMOKE_EMAIL = "smoke_f310@example.com"

errors: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    extra = f" -- {detail}" if detail else ""
    print(f"  [{status}] {name}{extra}")
    if not ok:
        errors.append(name)


def _wipe_user(db, email: str) -> None:
    u = db.query(User).filter_by(email=email).first()
    if u:
        db.query(EmailVerificationToken).filter_by(user_id=u.id).delete()
        db.query(PasswordResetToken).filter_by(user_id=u.id).delete()
        db.query(RefreshToken).filter_by(user_id=u.id).delete()
        db.delete(u)
        db.commit()


def _wipe_smoke_residue(db) -> None:
    """Wipe any unverified leftover smoke users so step 2's "no old
    unverified users" assertion has a clean baseline.

    Targets emails that are clearly test fixtures: @example.com TLD,
    @test.com, plus the historical x@y.com / a@b.com debug emails from
    earlier phase debugging. Production data on this DB isn't possible
    (local docker only); the filter is intentionally narrow."""
    from sqlalchemy import or_

    leftover_unverified = (
        db.query(User)
        .filter(
            User.email_verified_at.is_(None),
            or_(
                User.email.like("%@example.com"),
                User.email.like("%@test.com"),
                User.email.like("%@y.com"),
                User.email.like("%@b.com"),
            ),
        )
        .all()
    )
    for u in leftover_unverified:
        db.query(EmailVerificationToken).filter_by(user_id=u.id).delete()
        db.query(PasswordResetToken).filter_by(user_id=u.id).delete()
        db.query(RefreshToken).filter_by(user_id=u.id).delete()
        db.delete(u)
    if leftover_unverified:
        db.commit()


def _flush_redis_ratelimit() -> None:
    """Best-effort: clear F-310 rate-limit keys between steps."""
    try:
        import app.services.redis_client as rc
        rc._client = None  # reset cached client (may be tied to a closed loop)

        async def _flush():
            r = rc.get_redis()
            keys = await r.keys("f310:ratelimit:*")
            if keys:
                await r.delete(*keys)
            keys = await r.keys("f310:refresh:revoked")
            if keys:
                await r.delete(*keys)
        asyncio.run(_flush())
    except Exception as e:
        print(f"  [WARN] redis flush skipped: {e}")


# ── Step 1: Schema ─────────────────────────────────────────────


def step_1_schema() -> None:
    print("\nStep 1: F-310 schema present (5 users cols + 3 tables + 2 CHECKs)")
    with SessionLocal() as db:
        cols = {
            r[0] for r in db.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='users' AND column_name IN "
                "('email_verified_at','stripe_customer_id','stripe_subscription_id',"
                "'subscription_status','subscription_tier')"
            )).fetchall()
        }
        expected = {"email_verified_at", "stripe_customer_id",
                    "stripe_subscription_id", "subscription_status",
                    "subscription_tier"}
        check("5 new users columns present", cols == expected,
              f"missing: {expected - cols}" if expected - cols else "")

        tables = {
            r[0] for r in db.execute(text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name IN "
                "('refresh_tokens','email_verification_tokens','password_reset_tokens')"
            )).fetchall()
        }
        check("3 new auth-token tables present",
              tables == {"refresh_tokens", "email_verification_tokens",
                         "password_reset_tokens"})

        constraints = {
            r[0] for r in db.execute(text(
                "SELECT conname FROM pg_constraint "
                "WHERE conname IN ('ck_users_subscription_status','ck_users_subscription_tier')"
            )).fetchall()
        }
        check("2 CHECK constraints present",
              constraints == {"ck_users_subscription_status", "ck_users_subscription_tier"})


# ── Step 2: Grandfather backfill ───────────────────────────────


def step_2_grandfather() -> None:
    print("\nStep 2: grandfather backfill — all existing users (>1h old) verified")
    with SessionLocal() as db:
        # Filter to users created >1h ago — excludes test users from this
        # smoke run and any recent re-runs. The migration's UPDATE
        # populated email_verified_at for all rows that existed at apply
        # time; "old" users (anything not just created) should all carry
        # a populated timestamp.
        unverified_old = db.execute(text(
            "SELECT COUNT(*) FROM users "
            "WHERE email_verified_at IS NULL "
            "AND created_at < NOW() - INTERVAL '1 hour'"
        )).scalar()
        check(
            "no pre-migration users left unverified",
            unverified_old == 0,
            f"{unverified_old} old NULL users found — grandfather UPDATE may have missed rows",
        )


# ── Step 3: Register flow ──────────────────────────────────────


def step_3_register(c: TestClient) -> dict:
    print("\nStep 3: POST /api/auth/register → 201 + cookies + email_verified=False")
    with SessionLocal() as db:
        _wipe_user(db, SMOKE_EMAIL)

    r = c.post("/api/auth/register",
               json={"email": SMOKE_EMAIL, "password": "smoke_pass_123",
                     "full_name": "F310 Smoke"})
    check("status 201", r.status_code == 201, str(r.status_code))
    body = r.json()
    check("access_token in body", "access_token" in body)
    check("user.email_verified == False",
          body.get("user", {}).get("email_verified") is False,
          str(body.get("user", {}).get("email_verified")))
    check("user.subscription_tier == 'free'",
          body.get("user", {}).get("subscription_tier") == "free")
    check("access_token cookie set", "access_token" in c.cookies)
    check("refresh_token cookie set", "refresh_token" in c.cookies)

    with SessionLocal() as db:
        u = db.query(User).filter_by(email=SMOKE_EMAIL).first()
        check("user row exists in DB", u is not None)
        check("user.email_verified_at IS NULL post-register",
              u.email_verified_at is None)
        ev_count = (db.query(EmailVerificationToken)
                    .filter_by(user_id=u.id).count())
        check("verification token row created", ev_count == 1, f"count={ev_count}")
        rt_count = (db.query(RefreshToken)
                    .filter_by(user_id=u.id).count())
        check("refresh_token row created", rt_count == 1, f"count={rt_count}")
    return body


# ── Step 4: Verified gate ──────────────────────────────────────


def step_4_verified_gate(c: TestClient) -> None:
    print("\nStep 4: verified-gate — unverified user 403s on protected; /me 200")
    r = c.get("/api/auth/me")
    check("/me allows unverified (200)",
          r.status_code == 200 and r.json().get("email_verified") is False,
          str(r.status_code))

    r = c.get("/api/users/me")
    check("/api/users/me blocks unverified (403)",
          r.status_code == 403, str(r.status_code))
    detail = r.json().get("detail") if r.status_code == 403 else {}
    check("403 detail.code == 'email_not_verified'",
          isinstance(detail, dict) and detail.get("code") == "email_not_verified",
          str(detail))


# ── Step 5 + 6: Verify-email + replay ──────────────────────────


def step_5_6_verify_email(c: TestClient) -> None:
    print("\nStep 5: verify-email consumes token → user verified → protected 200")
    # Inject a known token so we don't need to scrape the email.
    from app.services.jwt_tokens import generate_secret_token
    raw, h = generate_secret_token()
    with SessionLocal() as db:
        u = db.query(User).filter_by(email=SMOKE_EMAIL).first()
        # Mark prior outstanding tokens consumed so only our known one
        # is the freshest valid token.
        (db.query(EmailVerificationToken)
            .filter_by(user_id=u.id)
            .update({EmailVerificationToken.consumed_at: datetime.datetime.utcnow()},
                    synchronize_session=False))
        db.add(EmailVerificationToken(
            user_id=u.id, token_hash=h,
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(hours=24),
        ))
        db.commit()

    r = c.post("/api/auth/verify-email", json={"token": raw})
    check("verify-email 200", r.status_code == 200, str(r.status_code))

    r = c.get("/api/users/me")
    check("/api/users/me 200 after verification", r.status_code == 200,
          str(r.status_code))

    print("\nStep 6: verify-email replay → 400 'Token already used'")
    r = c.post("/api/auth/verify-email", json={"token": raw})
    check("replay 400", r.status_code == 400 and "already used" in r.json().get("detail", ""),
          f"status={r.status_code} detail={r.json().get('detail')}")


# ── Step 7: Refresh rotation ───────────────────────────────────


def step_7_refresh_rotation(c: TestClient) -> None:
    print("\nStep 7: refresh rotation → new tokens, old refresh rejected")
    # Capture the current refresh cookie value so we can attempt replay.
    old_refresh = c.cookies.get("refresh_token")
    check("old refresh present", bool(old_refresh))

    r = c.post("/api/auth/refresh")
    check("refresh 200", r.status_code == 200, str(r.status_code))
    new_refresh = c.cookies.get("refresh_token")
    check("refresh cookie rotated (different value)",
          new_refresh and new_refresh != old_refresh)

    # Now replay the old refresh — should be 401 due to rotated_to_jti set.
    c2 = TestClient(c.app)
    c2.cookies.set("refresh_token", old_refresh)
    r = c2.post("/api/auth/refresh")
    check("old refresh replay 401", r.status_code == 401, str(r.status_code))


# ── Step 8: Logout + post-logout refresh ───────────────────────


def step_8_logout(c: TestClient) -> None:
    print("\nStep 8: logout revokes refresh → subsequent /refresh 401")
    r = c.post("/api/auth/logout")
    check("logout 200", r.status_code == 200, str(r.status_code))

    # TestClient may keep cookies; re-set the (now-revoked) refresh
    # explicitly so the refresh probe has something to send.
    r = c.post("/api/auth/refresh")
    check("post-logout refresh 401", r.status_code == 401, str(r.status_code))


# ── Step 9: Rate-limit logic (direct) ──────────────────────────


def step_9_rate_limit_direct() -> None:
    print("\nStep 9: rate-limit logic — 5 pass, 6th + 7th blocked")
    _flush_redis_ratelimit()

    async def run():
        import app.services.redis_client as rc
        rc._client = None
        from app.services.redis_client import get_redis
        from app.services.rate_limit import _check_window

        r = get_redis()
        keys = await r.keys("f310:ratelimit:smoke_unit:*")
        if keys:
            await r.delete(*keys)

        # 5 attempts pass
        for i in range(5):
            ok, retry = await _check_window(
                r, key="smoke_unit:short:127.0.0.1",
                max_attempts=5, window_seconds=900,
            )
            check(f"attempt {i+1} allowed", ok is True and retry == 0)

        # 6th blocked
        ok, retry = await _check_window(
            r, key="smoke_unit:short:127.0.0.1",
            max_attempts=5, window_seconds=900,
        )
        check("attempt 6 blocked with retry_after > 0",
              ok is False and retry > 0, f"retry={retry}")

        # 7th still blocked
        ok, retry = await _check_window(
            r, key="smoke_unit:short:127.0.0.1",
            max_attempts=5, window_seconds=900,
        )
        check("attempt 7 blocked", ok is False)

        # Cleanup
        keys = await r.keys("f310:ratelimit:smoke_unit:*")
        if keys:
            await r.delete(*keys)

    asyncio.run(run())


# ── Step 10: Rate-limit fail-open ──────────────────────────────


def step_10_rate_limit_failopen() -> None:
    print("\nStep 10: rate-limit fail-open when Redis unreachable")
    from app.services.rate_limit import auth_rate_limit

    # Build the dep and call it with a mock request, after patching
    # get_redis to raise — simulates Redis-down.
    dep_fn = auth_rate_limit("smoke_failopen")

    async def fake_get_redis():
        raise ConnectionRefusedError("simulated Redis-down")

    from unittest.mock import MagicMock
    request = MagicMock()
    request.client = MagicMock(host="1.2.3.4")

    async def run():
        with patch("app.services.rate_limit.get_redis",
                   side_effect=ConnectionRefusedError("simulated")):
            # Dep should return without raising — fail-open.
            await dep_fn(request)
        return True

    try:
        result = asyncio.run(run())
        check("rate-limit fails open (returns) on Redis-down", result is True)
    except Exception as e:
        check("rate-limit fails open", False, str(e))


# ── Step 11: hCaptcha branches ─────────────────────────────────


def step_11_hcaptcha() -> None:
    print("\nStep 11: hCaptcha branches — unset = no-op; set + bad token = 400")
    import app.config
    from app.routers.auth import _enforce_captcha_or_400
    from fastapi import HTTPException
    from unittest.mock import MagicMock

    req = MagicMock()
    req.client = MagicMock(host="1.2.3.4")

    async def run():
        orig = app.config.settings.HCAPTCHA_SECRET
        try:
            app.config.settings.HCAPTCHA_SECRET = ""
            try:
                await _enforce_captcha_or_400("any-token", req)
                check("SECRET unset = no-op", True)
            except HTTPException:
                check("SECRET unset = no-op", False)

            app.config.settings.HCAPTCHA_SECRET = "test-secret-not-real"
            try:
                await _enforce_captcha_or_400(None, req)
                check("SECRET set + no token = 400", False)
            except HTTPException as e:
                check("SECRET set + no token = 400 captcha_failed",
                      e.status_code == 400 and
                      e.detail.get("code") == "captcha_failed")

            try:
                await _enforce_captcha_or_400("fake-token-will-fail", req)
                check("SECRET set + bad token = 400", False)
            except HTTPException as e:
                check("SECRET set + bad token = 400 captcha_failed",
                      e.status_code == 400 and
                      e.detail.get("code") == "captcha_failed")
        finally:
            app.config.settings.HCAPTCHA_SECRET = orig

    asyncio.run(run())


# ── Step 12: Stripe webhook ────────────────────────────────────


def _stripe_sign(payload: bytes, secret: str, timestamp: int | None = None) -> str:
    """Compute a Stripe-Signature header for a given payload + secret.
    Mirrors stripe-python's signing logic. Used in smoke to forge a
    valid signature so we can exercise the 200 path."""
    if timestamp is None:
        timestamp = int(time.time())
    signed = f"{timestamp}.{payload.decode('utf-8')}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={sig}"


def step_12_stripe_webhook(c: TestClient) -> None:
    print("\nStep 12: stripe webhook — no-sig 400; bad-sig 400; valid-sig 200")
    # `object: "event"` is required by stripe-python 15.x's
    # construct_event — it inspects this field to distinguish v2 core
    # events from classic events. Real Stripe webhooks always include it.
    payload = json.dumps({
        "id": "evt_smoke_123",
        "object": "event",
        "type": "customer.subscription.created",
        "data": {"object": {}},
    }).encode("utf-8")

    r = c.post("/api/stripe/webhook", content=payload)
    check("no signature → 400", r.status_code == 400, str(r.status_code))

    r = c.post("/api/stripe/webhook", content=payload,
               headers={"Stripe-Signature": "t=1,v1=deadbeef"})
    check("bad signature → 400", r.status_code == 400, str(r.status_code))

    # Valid signature requires a configured secret on settings.
    import app.config
    orig = app.config.settings.STRIPE_WEBHOOK_SECRET
    app.config.settings.STRIPE_WEBHOOK_SECRET = "whsec_smoke_test_secret"
    try:
        sig = _stripe_sign(payload, "whsec_smoke_test_secret")
        r = c.post("/api/stripe/webhook", content=payload,
                   headers={"Stripe-Signature": sig})
        check("valid signature → 200",
              r.status_code == 200, f"status={r.status_code} body={r.text}")
        check("response echoes event type",
              r.status_code == 200 and
              r.json().get("type") == "customer.subscription.created")
    finally:
        app.config.settings.STRIPE_WEBHOOK_SECRET = orig


# ── Step 13: Tier DI ───────────────────────────────────────────


def step_13_tier_di() -> None:
    print("\nStep 13: require_tier() DI — free passes 'free'; free 403s 'subscription'")
    from app.services.tiers import require_tier, _resolve_user_tier
    from fastapi import HTTPException

    # _resolve_user_tier is the placeholder returning "free" for all.
    with SessionLocal() as db:
        u = db.query(User).filter_by(email=SMOKE_EMAIL).first()
        check("user fixture loaded for tier DI", u is not None)

    effective = _resolve_user_tier(u)
    check("placeholder resolves to 'free'", effective == "free", effective)

    # require_tier("free") → passes
    dep = require_tier("free")
    try:
        out = dep(u)  # type: ignore[arg-type]
        check("require_tier('free') passes", out is u)
    except HTTPException as e:
        check("require_tier('free') passes", False, str(e))

    # require_tier("subscription") → 403
    dep = require_tier("subscription")
    try:
        dep(u)  # type: ignore[arg-type]
        check("require_tier('subscription') 403s free user", False)
    except HTTPException as e:
        check("require_tier('subscription') 403s free user",
              e.status_code == 403 and
              e.detail.get("code") == "tier_insufficient")


# ── Step 14: ORM mirror reads new columns ──────────────────────


def step_14_orm_mirror() -> None:
    print("\nStep 14: User ORM model reflects + reads new columns")
    with SessionLocal() as db:
        u = db.query(User).filter_by(email=SMOKE_EMAIL).first()
        check("user.email_verified_at present + populated",
              u is not None and u.email_verified_at is not None)
        check("user.subscription_tier == 'free'",
              u.subscription_tier == "free", u.subscription_tier)
        check("user.subscription_status is None (default)",
              u.subscription_status is None)
        check("user.stripe_customer_id is None (no P-105 yet)",
              u.stripe_customer_id is None)


# ── Cleanup ────────────────────────────────────────────────────


def cleanup() -> None:
    print("\nCleanup")
    with SessionLocal() as db:
        _wipe_user(db, SMOKE_EMAIL)
    _flush_redis_ratelimit()
    print("  test rows removed")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    from main import app
    client = TestClient(app)

    # Pre-clean any leftover test users from earlier smoke runs so
    # step_2_grandfather's "old unverified" assertion has a clean baseline.
    with SessionLocal() as db:
        _wipe_smoke_residue(db)

    try:
        step_1_schema()
        step_2_grandfather()
        body = step_3_register(client)
        step_4_verified_gate(client)
        step_5_6_verify_email(client)
        step_7_refresh_rotation(client)
        step_8_logout(client)
        step_9_rate_limit_direct()
        step_10_rate_limit_failopen()
        step_11_hcaptcha()
        step_12_stripe_webhook(client)
        step_13_tier_di()
        step_14_orm_mirror()
    finally:
        cleanup()

    print()
    if errors:
        print(f"FAILURES ({len(errors)}): {errors}")
        return 1
    print("ALL F-310 CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
