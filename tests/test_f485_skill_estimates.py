"""F-485 - user-global per-skill CEFR estimates.

Tests:
  GET /api/users/me/skill-estimates
  PUT /api/users/me/skill-estimates

Scenarios:
  1. Unauthenticated -> 401 on both endpoints.
  2. GET -- fresh user with no estimates row -> 200, estimates {} (no 404).
  3. PUT then GET -> the write is reflected, server stamps updated_at.
  4. Partial PUT merges: a single-skill write does not clobber other skills.
  5. PUT with an invalid level -> 422, nothing written.
  6. PUT with an invalid skill code -> 422, nothing written.

Fixture email namespace: f485_ to avoid collision with prod rows.
Runs against local docker-compose PostgreSQL (same as dev server).
"""
from __future__ import annotations

import datetime

import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.models.models import User
from app.models.user_skill_estimates import UserSkillEstimate
from app.services.jwt_tokens import mint_access_token
from main import app


client = TestClient(app)

_EMAIL_FRESH = "f485_fresh@local"
_EMAIL_MERGE = "f485_merge@local"
_EMAILS = [_EMAIL_FRESH, _EMAIL_MERGE]


# ── helpers ───────────────────────────────────────────────────────────────────


def _auth(email: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {mint_access_token(email)}"}


def _teardown(db) -> None:
    db.execute(
        UserSkillEstimate.__table__.delete().where(
            UserSkillEstimate.user_id.in_(
                db.query(User.id).filter(User.email.in_(_EMAILS))
            )
        )
    )
    db.execute(User.__table__.delete().where(User.email.in_(_EMAILS)))
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
    db_session.add_all([
        User(
            email=_EMAIL_FRESH,
            hashed_password="x",
            full_name="F485 Fresh",
            email_verified_at=now,
            subscription_tier="free",
            current_level="B1",
        ),
        User(
            email=_EMAIL_MERGE,
            hashed_password="x",
            full_name="F485 Merge",
            email_verified_at=now,
            subscription_tier="free",
            current_level="B1",
        ),
    ])
    db_session.commit()

    yield

    _teardown(db_session)


# ── 1. Unauthenticated -> 401 ─────────────────────────────────────────────────


def test_get_skill_estimates_unauthenticated():
    r = client.get("/api/users/me/skill-estimates")
    assert r.status_code == 401


def test_put_skill_estimates_unauthenticated():
    r = client.put(
        "/api/users/me/skill-estimates",
        json={"estimates": {"CO": {"level": "B1"}}},
    )
    assert r.status_code == 401


# ── 2. GET -- empty default for a fresh user ──────────────────────────────────


def test_get_empty_default_fresh_user():
    r = client.get("/api/users/me/skill-estimates", headers=_auth(_EMAIL_FRESH))
    assert r.status_code == 200
    assert r.json() == {"estimates": {}}


# ── 3. PUT then GET reflects the write ────────────────────────────────────────


def test_put_then_get_reflects_write():
    r = client.put(
        "/api/users/me/skill-estimates",
        json={"estimates": {"CO": {"level": "B1"}, "CE": {"level": "A2"}}},
        headers=_auth(_EMAIL_FRESH),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["estimates"]["CO"]["level"] == "B1"
    assert body["estimates"]["CE"]["level"] == "A2"
    # Server stamps updated_at on each written skill.
    assert "updated_at" in body["estimates"]["CO"]
    assert "updated_at" in body["estimates"]["CE"]

    r2 = client.get("/api/users/me/skill-estimates", headers=_auth(_EMAIL_FRESH))
    assert r2.status_code == 200
    assert r2.json()["estimates"]["CO"]["level"] == "B1"
    assert r2.json()["estimates"]["CE"]["level"] == "A2"


# ── 4. Partial PUT merges without clobbering other skills ─────────────────────


def test_partial_put_merges():
    # Seed two skills.
    client.put(
        "/api/users/me/skill-estimates",
        json={"estimates": {"CO": {"level": "B1"}, "EO": {"level": "B2"}}},
        headers=_auth(_EMAIL_MERGE),
    )
    # Write only EO -> CO must be retained untouched.
    r = client.put(
        "/api/users/me/skill-estimates",
        json={"estimates": {"EO": {"level": "C1"}}},
        headers=_auth(_EMAIL_MERGE),
    )
    assert r.status_code == 200
    est = r.json()["estimates"]
    assert est["EO"]["level"] == "C1"      # overwritten
    assert est["CO"]["level"] == "B1"      # retained, not clobbered

    # Confirm via GET.
    r2 = client.get("/api/users/me/skill-estimates", headers=_auth(_EMAIL_MERGE))
    est2 = r2.json()["estimates"]
    assert est2["EO"]["level"] == "C1"
    assert est2["CO"]["level"] == "B1"


# ── 5. Invalid level -> 422 ───────────────────────────────────────────────────


def test_put_invalid_level_rejected():
    r = client.put(
        "/api/users/me/skill-estimates",
        json={"estimates": {"CO": {"level": "C2"}}},  # C2 is out of A1..C1 enum
        headers=_auth(_EMAIL_FRESH),
    )
    assert r.status_code == 422


# ── 6. Invalid skill code -> 422 ──────────────────────────────────────────────


def test_put_invalid_skill_rejected():
    r = client.put(
        "/api/users/me/skill-estimates",
        json={"estimates": {"XX": {"level": "B1"}}},  # XX is not a known skill
        headers=_auth(_EMAIL_FRESH),
    )
    assert r.status_code == 422
