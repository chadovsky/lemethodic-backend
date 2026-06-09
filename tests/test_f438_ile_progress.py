"""F-438 — /île progress read + write endpoints.

Tests:
  GET  /api/users/me/progress
  PATCH /api/users/me/progress

Scenarios:
  1. Unauthenticated → 401 on both endpoints.
  2. GET — user with no target profile → maitre_intensity null, F-417 defaults.
  3. GET — user with active target profile → maitre_intensity returned.
  4. PATCH — update daily_target_minutes → persisted, echoed in response.
  5. PATCH — update last_couche_signals JSONB → persisted, echoed.
  6. PATCH — omit all fields → no changes (idempotent).
  7. PATCH — daily_target_minutes out-of-range (0) → 422.
  8. PATCH — daily_target_minutes out-of-range (481) → 422.
  9. PATCH — server-managed fields (streak_days) not accepted.

Fixture email namespace: f438_ to avoid collision with prod rows.
Runs against local docker-compose PostgreSQL (same as dev server).
"""
from __future__ import annotations

import datetime

import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.models.models import User
from app.models.target_profiles import TargetProfile
from app.services.jwt_tokens import mint_access_token
from main import app


client = TestClient(app)

_EMAIL_NO_PROFILE = "f438_noprofile@local"
_EMAIL_WITH_PROFILE = "f438_withprofile@local"


# ── helpers ───────────────────────────────────────────────────────────────────


def _token(email: str) -> str:
    return mint_access_token(email)


def _auth(email: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(email)}"}


def _teardown(db) -> None:
    db.execute(
        TargetProfile.__table__.delete().where(
            TargetProfile.user_id.in_(
                db.query(User.id).filter(
                    User.email.in_([_EMAIL_NO_PROFILE, _EMAIL_WITH_PROFILE])
                )
            )
        )
    )
    db.execute(
        User.__table__.delete().where(
            User.email.in_([_EMAIL_NO_PROFILE, _EMAIL_WITH_PROFILE])
        )
    )
    db.commit()


# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def db_session():
    s = SessionLocal()
    yield s
    s.close()


@pytest.fixture(scope="module", autouse=True)
def seed(db_session):
    _teardown(db_session)

    now = datetime.datetime.utcnow()

    user_no_profile = User(
        email=_EMAIL_NO_PROFILE,
        hashed_password="x",
        full_name="F438 No Profile",
        email_verified_at=now,
        subscription_tier="free",
        current_level="B1",
        streak_days=3,
        longest_streak_days=10,
        streak_last_active_date=datetime.date(2026, 6, 3),
        production_minutes_total=90,
        daily_target_minutes=20,
        tache_attempts=5,
        last_couche_signals=None,
    )
    user_with_profile = User(
        email=_EMAIL_WITH_PROFILE,
        hashed_password="x",
        full_name="F438 With Profile",
        email_verified_at=now,
        subscription_tier="free",
        current_level="B2",
        streak_days=0,
        longest_streak_days=0,
        streak_last_active_date=None,
        production_minutes_total=0,
        daily_target_minutes=20,
        tache_attempts=0,
        last_couche_signals=None,
    )
    db_session.add_all([user_no_profile, user_with_profile])
    db_session.commit()
    db_session.refresh(user_no_profile)
    db_session.refresh(user_with_profile)

    profile = TargetProfile(
        user_id=user_with_profile.id,
        exam="tcf_canada",
        threshold_band="b2",
        maitre_intensity="strict",
        is_active=True,
    )
    db_session.add(profile)
    db_session.commit()

    yield

    _teardown(db_session)


# ── 1. Unauthenticated → 401 ──────────────────────────────────────────────────


def test_get_progress_unauthenticated():
    r = client.get("/api/users/me/progress")
    assert r.status_code == 401


def test_patch_progress_unauthenticated():
    r = client.patch("/api/users/me/progress", json={"daily_target_minutes": 30})
    assert r.status_code == 401


# ── 2. GET — no target profile ────────────────────────────────────────────────


def test_get_progress_no_profile():
    r = client.get("/api/users/me/progress", headers=_auth(_EMAIL_NO_PROFILE))
    assert r.status_code == 200
    body = r.json()
    assert body["current_level"] == "B1"
    assert body["maitre_intensity"] is None
    assert body["streak_days"] == 3
    assert body["longest_streak_days"] == 10
    assert body["streak_last_active_date"] == "2026-06-03"
    assert body["production_minutes_total"] == 90
    assert body["daily_target_minutes"] == 20
    assert body["tache_attempts"] == 5
    assert body["last_couche_signals"] is None


# ── 3. GET — with active target profile ───────────────────────────────────────


def test_get_progress_with_profile():
    r = client.get("/api/users/me/progress", headers=_auth(_EMAIL_WITH_PROFILE))
    assert r.status_code == 200
    body = r.json()
    assert body["current_level"] == "B2"
    assert body["maitre_intensity"] == "strict"


# ── 4. PATCH — daily_target_minutes ──────────────────────────────────────────


def test_patch_daily_target_minutes():
    r = client.patch(
        "/api/users/me/progress",
        json={"daily_target_minutes": 45},
        headers=_auth(_EMAIL_NO_PROFILE),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["daily_target_minutes"] == 45
    # Other fields unchanged.
    assert body["streak_days"] == 3

    # Re-GET confirms persistence.
    r2 = client.get("/api/users/me/progress", headers=_auth(_EMAIL_NO_PROFILE))
    assert r2.json()["daily_target_minutes"] == 45


# ── 5. PATCH — last_couche_signals JSONB ─────────────────────────────────────


def test_patch_last_couche_signals():
    signals = {"ile_1": {"le_fond": 14.5, "les_moules": 12.0}}
    r = client.patch(
        "/api/users/me/progress",
        json={"last_couche_signals": signals},
        headers=_auth(_EMAIL_NO_PROFILE),
    )
    assert r.status_code == 200
    assert r.json()["last_couche_signals"] == signals

    r2 = client.get("/api/users/me/progress", headers=_auth(_EMAIL_NO_PROFILE))
    assert r2.json()["last_couche_signals"] == signals


# ── 6. PATCH — empty body (idempotent) ───────────────────────────────────────


def test_patch_empty_body_idempotent():
    r_before = client.get("/api/users/me/progress", headers=_auth(_EMAIL_WITH_PROFILE))
    before = r_before.json()

    r = client.patch("/api/users/me/progress", json={}, headers=_auth(_EMAIL_WITH_PROFILE))
    assert r.status_code == 200
    after = r.json()
    assert after["daily_target_minutes"] == before["daily_target_minutes"]
    assert after["streak_days"] == before["streak_days"]


# ── 7. PATCH — daily_target_minutes = 0 (out of range) ───────────────────────


def test_patch_daily_target_minutes_zero_rejected():
    r = client.patch(
        "/api/users/me/progress",
        json={"daily_target_minutes": 0},
        headers=_auth(_EMAIL_NO_PROFILE),
    )
    assert r.status_code == 422


# ── 8. PATCH — daily_target_minutes = 481 (out of range) ─────────────────────


def test_patch_daily_target_minutes_over_max_rejected():
    r = client.patch(
        "/api/users/me/progress",
        json={"daily_target_minutes": 481},
        headers=_auth(_EMAIL_NO_PROFILE),
    )
    assert r.status_code == 422


# ── 9. PATCH — streak_days not in writable contract ──────────────────────────


def test_patch_streak_days_not_accepted():
    """streak_days is NOT a field in ProgressPatch — extra keys are ignored
    by Pydantic's default behavior, so the request succeeds but streak_days
    is unchanged on the User row."""
    original_r = client.get("/api/users/me/progress", headers=_auth(_EMAIL_NO_PROFILE))
    original_streak = original_r.json()["streak_days"]

    r = client.patch(
        "/api/users/me/progress",
        json={"streak_days": 999},
        headers=_auth(_EMAIL_NO_PROFILE),
    )
    # Extra keys are silently ignored (Pydantic v2 default).
    assert r.status_code == 200
    assert r.json()["streak_days"] == original_streak
