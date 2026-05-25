"""M2-side BE auth fixes — route-level access control tests.

Covers three fixes from commit 9798a43 audit:

  Fix 1: GET /api/admin/themes, /topics, /random-topic now require admin.
  Fix 2: POST /api/recordings/{id}/confirm-transcript requires diagnostic quota.
  Fix 3: POST /api/auth/password-reset/confirm has IP rate-limit dep.

Tests run against local docker-compose Postgres (same as the dev server).
Rate-limit deps fail-open when Redis is down, so Redis is not required here
— the token/auth assertions are all we assert on.

Fixture namespace: ``m2auth_`` prefix on emails / slugs.
"""
from __future__ import annotations

import datetime

import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.models.models import User
from app.services.jwt_tokens import mint_access_token
from main import app


client = TestClient(app)

_EMAIL_REGULAR = "m2auth_regular@local"
_EMAIL_ADMIN = "m2auth_admin@local"


# ── fixtures ─────────────────────────────────────────────────────────────────


def _delete_namespace(db) -> None:
    db.execute(User.__table__.delete().where(
        User.email.in_([_EMAIL_REGULAR, _EMAIL_ADMIN])
    ))
    db.commit()


@pytest.fixture(scope="module")
def db_session():
    s = SessionLocal()
    yield s
    s.close()


@pytest.fixture(scope="module", autouse=True)
def fixture_state(db_session):
    _delete_namespace(db_session)

    now = datetime.datetime.utcnow()

    regular = User(
        email=_EMAIL_REGULAR,
        hashed_password="x",
        full_name="M2 Regular",
        email_verified_at=now,
        is_admin=False,
    )
    admin = User(
        email=_EMAIL_ADMIN,
        hashed_password="x",
        full_name="M2 Admin",
        email_verified_at=now,
        is_admin=True,
    )
    db_session.add(regular)
    db_session.add(admin)
    db_session.commit()

    yield

    _delete_namespace(db_session)


@pytest.fixture(scope="module")
def regular_headers() -> dict:
    return {"Authorization": f"Bearer {mint_access_token(_EMAIL_REGULAR)}"}


@pytest.fixture(scope="module")
def admin_headers() -> dict:
    return {"Authorization": f"Bearer {mint_access_token(_EMAIL_ADMIN)}"}


# ── Fix 1: admin GET guards ───────────────────────────────────────────────────


def test_admin_themes_unauthenticated_401():
    r = client.get("/api/admin/themes")
    assert r.status_code == 401, r.text


def test_admin_themes_non_admin_403(regular_headers):
    r = client.get("/api/admin/themes", headers=regular_headers)
    assert r.status_code == 403, r.text


def test_admin_themes_admin_200(admin_headers):
    r = client.get("/api/admin/themes", headers=admin_headers)
    assert r.status_code == 200, r.text


def test_admin_topics_unauthenticated_401():
    r = client.get("/api/admin/topics")
    assert r.status_code == 401, r.text


def test_admin_topics_non_admin_403(regular_headers):
    r = client.get("/api/admin/topics", headers=regular_headers)
    assert r.status_code == 403, r.text


def test_admin_topics_admin_200(admin_headers):
    r = client.get("/api/admin/topics", headers=admin_headers)
    assert r.status_code == 200, r.text


def test_admin_random_topic_unauthenticated_401():
    r = client.get("/api/admin/random-topic")
    assert r.status_code == 401, r.text


def test_admin_random_topic_non_admin_403(regular_headers):
    r = client.get("/api/admin/random-topic", headers=regular_headers)
    assert r.status_code == 403, r.text


# ── Fix 2: confirm-transcript requires auth (quota gate wraps get_current_user)


def test_confirm_transcript_unauthenticated_401():
    r = client.post(
        "/api/recordings/9999/confirm-transcript",
        json={"corrected_transcript": "bonjour"},
    )
    assert r.status_code == 401, r.text


def test_confirm_transcript_authenticated_reaches_handler(regular_headers):
    # Auth passes; recording 9999 doesn't exist → 404 from the handler.
    # This proves diagnostic_quota_required resolves the user successfully
    # and the handler executes (fail-open on Redis if not running).
    r = client.post(
        "/api/recordings/9999/confirm-transcript",
        json={"corrected_transcript": "bonjour"},
        headers=regular_headers,
    )
    assert r.status_code == 404, r.text


# ── Fix 3: password-reset/confirm rate-limit dep doesn't break the route ─────


def test_password_reset_confirm_invalid_token_400():
    # Passes rate-limit dep (fail-open when Redis is down) and reaches
    # the token-validation logic, which rejects the bogus token.
    r = client.post(
        "/api/auth/password-reset/confirm",
        json={"token": "bogus_m2_test_token", "new_password": "newpassword123"},
    )
    assert r.status_code == 400, r.text


def test_password_reset_confirm_short_password_400():
    r = client.post(
        "/api/auth/password-reset/confirm",
        json={"token": "bogus_m2_test_token", "new_password": "short"},
    )
    assert r.status_code == 400, r.text
