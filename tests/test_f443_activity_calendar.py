"""F-443 — GET /api/users/me/activity-calendar tests.

Scenarios:
  1. Unauthenticated -> 401.
  2. ?days out of range (0, 366) -> 422.
  3. Empty-history user -> all counts zero, streaks zero, days == 90.
  4. Partial-week user — 3 recordings across 2 days in window:
       counts correct, target_met only where count >= 2.
  5. Mixed-sources user — recording + ecole completion on same day: both counted.
  6. Streak math — 5 consecutive days with count >= 2 -> current_streak == 5,
     broken streak -> current_streak resets; longest_streak correct.
  7. Activity outside the window is excluded from counts.
  8. default days=90 -> response has exactly 90 day entries.
  9. ?days=7 -> response has exactly 7 day entries.

Fixture email namespace: f443_ to avoid collision.
Runs against local docker-compose PostgreSQL.
"""
from __future__ import annotations

import datetime

import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.models.models import EcoleLesson, Recording, User, UserEcoleProgress
from app.services.jwt_tokens import mint_access_token
from main import app

client = TestClient(app)

_EMAIL_EMPTY = "f443_empty@local"
_EMAIL_PARTIAL = "f443_partial@local"
_EMAIL_MIXED = "f443_mixed@local"
_EMAIL_STREAK = "f443_streak@local"

_ALL_EMAILS = [_EMAIL_EMPTY, _EMAIL_PARTIAL, _EMAIL_MIXED, _EMAIL_STREAK]

# Stable IDs that don't collide with seeded data (lesson_number > 9000).
_TEST_LESSON_NUMBER = 9443
_TEST_LESSON_CODE = "f443_test_lesson"

TODAY = datetime.date.today()


def _token(email: str) -> str:
    return mint_access_token(email)


def _auth(email: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(email)}"}


def _dt(d: datetime.date) -> datetime.datetime:
    return datetime.datetime.combine(d, datetime.time(12, 0))


def _teardown(db) -> None:
    user_ids = [
        row[0]
        for row in db.query(User.id).filter(User.email.in_(_ALL_EMAILS)).all()
    ]
    if user_ids:
        db.query(UserEcoleProgress).filter(
            UserEcoleProgress.user_id.in_(user_ids)
        ).delete(synchronize_session=False)
        db.query(Recording).filter(Recording.user_id.in_(user_ids)).delete(
            synchronize_session=False
        )
        db.query(User).filter(User.email.in_(_ALL_EMAILS)).delete(
            synchronize_session=False
        )
    # Remove the test lesson (if it exists).
    db.query(EcoleLesson).filter(
        EcoleLesson.code == _TEST_LESSON_CODE
    ).delete(synchronize_session=False)
    db.commit()


def _make_user(db, email: str) -> User:
    u = User(
        email=email,
        hashed_password="x",
        full_name="F443 Test",
        email_verified_at=datetime.datetime.utcnow(),
        subscription_tier="free",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _recording(db, user_id: int, dt: datetime.datetime) -> None:
    r = Recording(
        user_id=user_id,
        audio_path="f443_test.webm",
        tache_mode="tache_3",
    )
    r.created_at = dt
    db.add(r)


def _ecole_done(db, user_id: int, dt: datetime.datetime, lesson_id: int) -> None:
    e = UserEcoleProgress(
        user_id=user_id,
        lesson_id=lesson_id,
        status="completed",
    )
    e.completed_at = dt
    db.add(e)


@pytest.fixture(scope="module")
def db_session():
    s = SessionLocal()
    yield s
    s.close()


@pytest.fixture(scope="module", autouse=True)
def seed(db_session):
    _teardown(db_session)

    # Create a minimal ecole lesson for FK-safe ecole-progress rows.
    lesson = EcoleLesson(
        lesson_number=_TEST_LESSON_NUMBER,
        code=_TEST_LESSON_CODE,
        title_fr="F443 Leçon Test",
        title_en="F443 Test Lesson",
    )
    db_session.add(lesson)
    db_session.commit()
    db_session.refresh(lesson)
    lesson_id = lesson.id

    # Empty-history user — no activity at all.
    _make_user(db_session, _EMAIL_EMPTY)

    # Partial user: 3 recordings — 2 on day-5-ago, 1 on day-2-ago.
    u_partial = _make_user(db_session, _EMAIL_PARTIAL)
    _recording(db_session, u_partial.id, _dt(TODAY - datetime.timedelta(days=5)))
    _recording(db_session, u_partial.id, _dt(TODAY - datetime.timedelta(days=5)))
    _recording(db_session, u_partial.id, _dt(TODAY - datetime.timedelta(days=2)))

    # Mixed user: 1 recording + 1 ecole completion on the same day.
    # Verifies both sources contribute to the count.
    u_mixed = _make_user(db_session, _EMAIL_MIXED)
    _recording(db_session, u_mixed.id, _dt(TODAY))
    _ecole_done(db_session, u_mixed.id, _dt(TODAY), lesson_id=lesson_id)

    # Streak user: 5 consecutive days ending yesterday, then a gap, then today.
    u_streak = _make_user(db_session, _EMAIL_STREAK)
    for offset in range(1, 6):   # yesterday (1) back to 5-ago: 5 days
        _recording(db_session, u_streak.id, _dt(TODAY - datetime.timedelta(days=offset)))
        _recording(db_session, u_streak.id, _dt(TODAY - datetime.timedelta(days=offset)))
    # Gap at 6-ago — intentionally no activity.
    # Older run: 3 days at 7/8/9-ago (should not beat the 5-day streak).
    for offset in range(7, 10):
        _recording(db_session, u_streak.id, _dt(TODAY - datetime.timedelta(days=offset)))
        _recording(db_session, u_streak.id, _dt(TODAY - datetime.timedelta(days=offset)))
    # Today: 1 recording only (below target=2).
    _recording(db_session, u_streak.id, _dt(TODAY))

    db_session.commit()
    yield
    _teardown(db_session)


# ── 1. Unauthenticated ────────────────────────────────────────────────────────


def test_unauthenticated():
    r = client.get("/api/users/me/activity-calendar")
    assert r.status_code == 401


# ── 2. ?days out of range ─────────────────────────────────────────────────────


def test_days_zero_rejected():
    r = client.get(
        "/api/users/me/activity-calendar",
        params={"days": 0},
        headers=_auth(_EMAIL_EMPTY),
    )
    assert r.status_code == 422


def test_days_over_max_rejected():
    r = client.get(
        "/api/users/me/activity-calendar",
        params={"days": 366},
        headers=_auth(_EMAIL_EMPTY),
    )
    assert r.status_code == 422


# ── 3. Empty-history user ─────────────────────────────────────────────────────


def test_empty_history_all_zeros():
    r = client.get("/api/users/me/activity-calendar", headers=_auth(_EMAIL_EMPTY))
    assert r.status_code == 200
    body = r.json()
    assert len(body["days"]) == 90
    assert all(d["count"] == 0 for d in body["days"])
    assert all(d["target_met"] is False for d in body["days"])
    assert body["today_count"] == 0
    assert body["current_streak"] == 0
    assert body["longest_streak"] == 0
    assert body["daily_target"] == 2
    assert body["today_target"] == 2


# ── 4. Partial-week counts ────────────────────────────────────────────────────


def test_partial_week_counts():
    r = client.get("/api/users/me/activity-calendar", headers=_auth(_EMAIL_PARTIAL))
    assert r.status_code == 200
    body = r.json()
    days_by_date = {d["date"]: d for d in body["days"]}

    day5 = (TODAY - datetime.timedelta(days=5)).isoformat()
    day2 = (TODAY - datetime.timedelta(days=2)).isoformat()

    assert days_by_date[day5]["count"] == 2
    assert days_by_date[day5]["target_met"] is True

    assert days_by_date[day2]["count"] == 1
    assert days_by_date[day2]["target_met"] is False

    for d in body["days"]:
        if d["date"] not in (day5, day2):
            assert d["count"] == 0, f"Unexpected count on {d['date']}"


# ── 5. Mixed sources (recording + ecole) both counted ────────────────────────


def test_mixed_sources_count():
    r = client.get("/api/users/me/activity-calendar", headers=_auth(_EMAIL_MIXED))
    assert r.status_code == 200
    body = r.json()
    today_str = TODAY.isoformat()
    today_day = next(d for d in body["days"] if d["date"] == today_str)
    # 1 recording + 1 ecole completion = 2 events
    assert today_day["count"] == 2
    assert today_day["target_met"] is True
    assert body["today_count"] == 2


# ── 6. Streak math ────────────────────────────────────────────────────────────


def test_streak_math():
    r = client.get("/api/users/me/activity-calendar", headers=_auth(_EMAIL_STREAK))
    assert r.status_code == 200
    body = r.json()

    # 5 consecutive days ending yesterday (today has only 1 < target=2).
    # current_streak anchors to yesterday and walks back 5 days.
    assert body["current_streak"] == 5

    # Longest run: 5 consecutive (1–5 ago). The older 3-day run (7–9 ago) is shorter.
    assert body["longest_streak"] == 5

    # Today has 1 recording, below target.
    assert body["today_count"] == 1


# ── 7. Activity outside window excluded ───────────────────────────────────────


def test_activity_outside_window_excluded():
    r = client.get(
        "/api/users/me/activity-calendar",
        params={"days": 3},
        headers=_auth(_EMAIL_STREAK),
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["days"]) == 3
    # Window covers: today (1), yesterday (2), day-before (2) = 5 total.
    # Days 5-ago, 9-ago etc. are outside the 3-day window.
    total = sum(d["count"] for d in body["days"])
    assert total == 5


# ── 8. Default days=90 ────────────────────────────────────────────────────────


def test_default_days_90():
    r = client.get("/api/users/me/activity-calendar", headers=_auth(_EMAIL_EMPTY))
    assert r.status_code == 200
    assert len(r.json()["days"]) == 90


# ── 9. ?days=7 ────────────────────────────────────────────────────────────────


def test_days_7():
    r = client.get(
        "/api/users/me/activity-calendar",
        params={"days": 7},
        headers=_auth(_EMAIL_EMPTY),
    )
    assert r.status_code == 200
    assert len(r.json()["days"]) == 7
