"""F-401 — AI endpoint rate limit tests.

Verifies that the dual-window ai_rate_limit dependency returns 429 +
Retry-After when the counter exceeds the configured ceiling, and allows
the request through when under the ceiling.

Two representative endpoints tested:
  - POST /api/writing/submit  (cheap: 5/min limit — easy to exceed)
  - POST /api/recordings/transcribe  (expensive: 20/min limit)

Redis is mocked via unittest.mock.patch so tests run without a live
Redis instance and without polluting real counters.  The DB fixture
creates a minimal test user so get_current_user resolves (auth must
pass before the rate-limit dependency fires).

Mock strategy:
  patch("app.services.rate_limit.get_redis") returns a mock whose
  .pipeline() returns an AsyncMock with .execute() returning [count, 1].
  _check_window calls pipeline() once per window; we create a fresh
  mock pipe per call so both windows are independently counted.
"""
from __future__ import annotations

import datetime
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.models.models import Feedback, Recording, User
from app.services.jwt_tokens import mint_access_token
from main import app


client = TestClient(app)

_NS = "f401rl_"
_EMAIL = f"{_NS}user@local"


# ── Redis mock factories ──────────────────────────────────────────────────────

def _mock_redis_with_count(count: int):
    """Return a mock Redis whose pipeline().execute() always returns [count, 1].

    Each pipeline() call produces a fresh AsyncMock so the short-window
    and long-window checks are independent and both see the same count.
    """
    def _new_pipe():
        pipe = AsyncMock()
        pipe.incr = MagicMock(return_value=pipe)
        pipe.expire = MagicMock(return_value=pipe)
        pipe.execute = AsyncMock(return_value=[count, 1])
        return pipe

    mock_r = MagicMock()
    mock_r.pipeline = MagicMock(side_effect=_new_pipe)
    return mock_r


# ── DB fixtures ───────────────────────────────────────────────────────────────

def _delete_ns(db) -> None:
    user_ids_q = db.query(User.id).filter(User.email.like(f"{_NS}%")).scalar_subquery()
    rec_ids_q = db.query(Recording.id).filter(Recording.user_id.in_(user_ids_q)).scalar_subquery()
    db.execute(Feedback.__table__.delete().where(Feedback.recording_id.in_(rec_ids_q)))
    db.execute(Recording.__table__.delete().where(Recording.user_id.in_(user_ids_q)))
    db.execute(User.__table__.delete().where(User.email.like(f"{_NS}%")))
    db.commit()


@pytest.fixture(scope="module")
def db_session():
    s = SessionLocal()
    yield s
    s.close()


@pytest.fixture(scope="module")
def auth_token(db_session):
    _delete_ns(db_session)
    user = User(
        email=_EMAIL,
        hashed_password="x",
        full_name="F401 Test",
        email_verified_at=datetime.datetime.utcnow(),
        subscription_tier="free",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = mint_access_token(_EMAIL)
    yield token

    _delete_ns(db_session)


# ── helpers ───────────────────────────────────────────────────────────────────

def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── writing/submit tests (5/min limit) ───────────────────────────────────────

class TestWritingSubmitRateLimit:
    def test_429_when_burst_window_exceeded(self, auth_token):
        """Count=6 > short_max=5 triggers 429 on writing/submit."""
        with patch("app.services.rate_limit.get_redis", return_value=_mock_redis_with_count(6)):
            resp = client.post(
                "/api/writing/submit",
                json={"prompt_id": 1, "student_text": "Bonjour le monde."},
                headers=_auth(auth_token),
            )
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers
        detail = resp.json()["detail"]
        assert detail["code"] == "ai_rate_limit_exceeded"
        assert detail["window"] == "short"
        assert detail["endpoint"] == "writing_submit"
        assert int(resp.headers["Retry-After"]) > 0

    def test_429_when_long_window_exceeded(self, auth_token):
        """Count=31 > long_max=30 triggers 429 on the long window."""
        with patch("app.services.rate_limit.get_redis", return_value=_mock_redis_with_count(31)):
            resp = client.post(
                "/api/writing/submit",
                json={"prompt_id": 1, "student_text": "Test."},
                headers=_auth(auth_token),
            )
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers

    def test_passes_rate_limit_under_ceiling(self, auth_token):
        """Count=1 is under both ceilings; endpoint proceeds past rate limiter.

        The request reaches the handler which returns 404 (prompt not found)
        not 429, confirming the rate-limit gate was passed.
        """
        with patch("app.services.rate_limit.get_redis", return_value=_mock_redis_with_count(1)):
            resp = client.post(
                "/api/writing/submit",
                json={"prompt_id": 999999, "student_text": "Bonjour."},
                headers=_auth(auth_token),
            )
        assert resp.status_code != 429
        assert "Retry-After" not in resp.headers

    def test_429_response_has_retry_after_header(self, auth_token):
        """Retry-After header must be present and numeric on 429."""
        with patch("app.services.rate_limit.get_redis", return_value=_mock_redis_with_count(99)):
            resp = client.post(
                "/api/writing/submit",
                json={"prompt_id": 1, "student_text": "Test."},
                headers=_auth(auth_token),
            )
        assert resp.status_code == 429
        retry_after = resp.headers.get("Retry-After", "")
        assert retry_after.isdigit(), f"Retry-After not numeric: {retry_after!r}"
        assert int(retry_after) >= 1


# ── recordings/transcribe tests (20/min limit) ───────────────────────────────

class TestRecordingsTranscribeRateLimit:
    def test_429_when_burst_window_exceeded(self, auth_token):
        """Count=21 > short_max=20 triggers 429 on recordings/transcribe."""
        with patch("app.services.rate_limit.get_redis", return_value=_mock_redis_with_count(21)):
            resp = client.post(
                "/api/recordings/transcribe",
                data={"tache_mode": "tache_3", "target_level": "B2"},
                files={"audio": ("clip.webm", BytesIO(b"\x00"), "audio/webm")},
                headers=_auth(auth_token),
            )
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers
        detail = resp.json()["detail"]
        assert detail["code"] == "ai_rate_limit_exceeded"
        assert detail["endpoint"] == "transcribe"

    def test_passes_rate_limit_under_ceiling(self, auth_token):
        """Count=1 passes; endpoint proceeds and fails on STT (not 429).

        We don't mock the STT service so the call fails later in the
        pipeline, but the important assertion is that we did NOT get 429.
        """
        with patch("app.services.rate_limit.get_redis", return_value=_mock_redis_with_count(1)):
            resp = client.post(
                "/api/recordings/transcribe",
                data={"tache_mode": "tache_3", "target_level": "B2"},
                files={"audio": ("clip.webm", BytesIO(b"\x00"), "audio/webm")},
                headers=_auth(auth_token),
            )
        assert resp.status_code != 429

    def test_fail_open_when_redis_down(self, auth_token):
        """When Redis raises, the limiter fails open (request proceeds).

        A real AssemblyAI call would fail downstream, but we should NOT
        see 429 — the fail-open path lets the request through.
        """
        with patch(
            "app.services.rate_limit.get_redis",
            side_effect=Exception("redis unavailable"),
        ):
            resp = client.post(
                "/api/recordings/transcribe",
                data={"tache_mode": "tache_3", "target_level": "B2"},
                files={"audio": ("clip.webm", BytesIO(b"\x00"), "audio/webm")},
                headers=_auth(auth_token),
            )
        assert resp.status_code != 429
