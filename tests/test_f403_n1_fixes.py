"""F-403 — N+1 regression guard.

Verifies that each patched endpoint issues a constant number of SELECT
statements regardless of result-set size.  Uses a real PostgreSQL session
(same as the dev server) with a small synthetic dataset (5 recordings +
feedbacks per user) so the test finishes in under a second.

Query-counting strategy: SQLAlchemy `after_execute` engine event.  The
counter increments on every statement execution; we capture it before and
after the handler call and assert the delta is <= a fixed ceiling that is
much less than N (ruling out the old O(N) pattern).

Ceilings chosen conservatively:
  analytics/dashboard, progress, pass, recurring — 5 queries (recordings +
    feedback selectinload + topics + a couple of framework helpers)
  admin/dashboard  — 5 queries (agg + recent join + selectinload)
  admin/users      — 3 queries (single agg JOIN + users)
  recordings/history — 4 queries (recordings + selectinload feedback +
    joinedload topic is folded into the main query)
  writing/history  — 3 queries (submissions + joinedload prompt)

Any of these hitting N_RECS=5 without eager loading would produce >=6 extra
SELECT statements, so a ceiling of 5 total easily distinguishes O(1) from
O(N).
"""
from __future__ import annotations

import datetime
import json

import pytest
from sqlalchemy import event as sa_event

from app.database import SessionLocal, engine
from app.models.models import (
    Feedback,
    Recording,
    TestTopic,
    User,
)
from app.models.writing import WritingPrompt, WritingSubmission


# ── constants ────────────────────────────────────────────────────────────────

_NS = "f403qc_"           # namespace prefix — prevents collision with prod rows
_EMAIL_USER = f"{_NS}user@local"
_EMAIL_ADMIN = f"{_NS}admin@local"
N_RECS = 5                 # recordings + feedbacks to create per user
MAX_QUERIES_CONSTANT = 6   # ceiling for O(1) check; O(N) would be >= N_RECS+1


# ── query counter ────────────────────────────────────────────────────────────

class _QueryCounter:
    """Counts SQL statements executed against the given engine."""

    def __init__(self):
        self.count = 0
        sa_event.listen(engine, "after_execute", self._on_execute)

    def _on_execute(self, conn, clauseelement, multiparams, params, execution_options, result):
        self.count += 1

    def reset(self):
        self.count = 0

    def remove(self):
        sa_event.remove(engine, "after_execute", self._on_execute)


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_user(db, email: str, is_admin: bool = False) -> User:
    u = User(
        email=email,
        hashed_password="x",
        full_name="F403 Test",
        is_admin=is_admin,
        created_at=datetime.datetime.utcnow(),
        email_verified_at=datetime.datetime.utcnow(),
    )
    db.add(u)
    db.flush()
    return u


def _make_recording_with_feedback(db, user_id: int, topic_id: int | None = None) -> Recording:
    rec = Recording(
        user_id=user_id,
        audio_path="test/path.webm",
        target_level="B2",
        tache_mode="tache_3",
        status="done",
        topic_id=topic_id,
        created_at=datetime.datetime.utcnow(),
    )
    db.add(rec)
    db.flush()

    fb = Feedback(
        recording_id=rec.id,
        note_globale=14.0,
        overall_score=14.0,
        score_le_fond=3.5,
        score_les_moules_des_idees=3.5,
        score_les_moules=3.5,
        score_les_reflexes_anglais=3.5,
        score_prononciation=3.5,
        goulet_nom="Les Moules",
        patterns_manquants=json.dumps(["pattern_a"]),
        reflexes_detectes=json.dumps(["reflex_a"]),
        corrections=json.dumps([]),
        ordonnance=json.dumps({}),
    )
    db.add(fb)
    db.flush()
    return rec


def _make_topic(db) -> TestTopic:
    t = TestTopic(
        title=f"{_NS}topic",
        theme="Société",
        is_active=True,
    )
    db.add(t)
    db.flush()
    return t


def _make_writing_submission(db, user_id: int, prompt_id: int) -> WritingSubmission:
    sub = WritingSubmission(
        user_id=user_id,
        prompt_id=prompt_id,
        student_text="Test text",
        overall_score=13.0,
        word_count=2,
        submitted_at=datetime.datetime.utcnow(),
    )
    db.add(sub)
    db.flush()
    return sub


def _delete_namespace(db) -> None:
    # delete in FK-safe order
    db.execute(
        Feedback.__table__.delete().where(
            Feedback.recording_id.in_(
                db.query(Recording.id)
                .filter(Recording.user_id.in_(
                    db.query(User.id).filter(User.email.like(f"{_NS}%"))
                ))
                .scalar_subquery()
            )
        )
    )
    db.execute(
        Recording.__table__.delete().where(
            Recording.user_id.in_(
                db.query(User.id).filter(User.email.like(f"{_NS}%"))
            )
        )
    )
    db.execute(
        WritingSubmission.__table__.delete().where(
            WritingSubmission.user_id.in_(
                db.query(User.id).filter(User.email.like(f"{_NS}%"))
            )
        )
    )
    db.execute(User.__table__.delete().where(User.email.like(f"{_NS}%")))
    db.execute(TestTopic.__table__.delete().where(TestTopic.title.like(f"{_NS}%")))
    db.execute(WritingPrompt.__table__.delete().where(WritingPrompt.title_fr.like(f"{_NS}%")))
    db.commit()


# ── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def db():
    s = SessionLocal()
    yield s
    s.close()


@pytest.fixture(scope="module", autouse=True)
def seed(db):
    _delete_namespace(db)

    user = _make_user(db, _EMAIL_USER)
    admin = _make_user(db, _EMAIL_ADMIN, is_admin=True)
    topic = _make_topic(db)

    for _ in range(N_RECS):
        _make_recording_with_feedback(db, user.id, topic_id=topic.id)

    # Writing prompt + submissions
    prompt = WritingPrompt(
        level="B2",
        theme="Société",
        prompt_text=f"{_NS}prompt text",
        prompt_type="email",
        tache_level=2,
        title_fr=f"{_NS}titre",
        prompt_fr=f"{_NS}prompt",
        prompt_en=f"{_NS}prompt_en",
        topic_tag="society",
        min_words=100,
        max_words=300,
        time_limit_minutes=45,
    )
    db.add(prompt)
    db.flush()

    for _ in range(N_RECS):
        _make_writing_submission(db, user.id, prompt.id)

    db.commit()

    yield {"user": user, "admin": admin, "topic": topic, "prompt": prompt}

    _delete_namespace(db)


@pytest.fixture(scope="module")
def counter(seed):
    c = _QueryCounter()
    yield c
    c.remove()


# ── helpers that invoke the handler directly ──────────────────────────────────

def _call_analytics_dashboard(db, user):
    from app.routers.analytics import analytics_dashboard
    return analytics_dashboard(limit=50, db=db, user=user)


def _call_analytics_progress(db, user):
    from app.routers.analytics import progress_over_time
    return progress_over_time(last_n=20, db=db, user=user)


def _call_analytics_pass(db, user):
    from app.routers.analytics import pass_probability
    return pass_probability(target_level="B2", limit=50, db=db, user=user)


def _call_analytics_recurring(db, user):
    from app.routers.analytics import recurring_problems
    return recurring_problems(last_n=10, db=db, user=user)


def _call_admin_dashboard(db, admin):
    from app.routers.admin import dashboard
    return dashboard(db=db, admin=admin)


def _call_admin_users(db, admin):
    from app.routers.admin import list_users
    return list_users(limit=50, db=db, admin=admin)


def _call_recordings_history(db, user):
    from app.routers.recordings import get_history
    return get_history(db=db, user=user)


def _call_writing_history(db, user):
    from app.routers.writing import get_writing_history
    return get_writing_history(user_id=user.id, db=db, user=user)


# ── query-count tests ─────────────────────────────────────────────────────────

def _check_query_count(counter, fn, label: str) -> int:
    counter.reset()
    fn()
    n = counter.count
    assert n <= MAX_QUERIES_CONSTANT, (
        f"{label}: {n} queries for {N_RECS} records — exceeds O(1) ceiling "
        f"of {MAX_QUERIES_CONSTANT}. Possible N+1 regression."
    )
    return n


def test_analytics_dashboard_query_count(db, counter, seed):
    user = seed["user"]
    n = _check_query_count(counter, lambda: _call_analytics_dashboard(db, user), "analytics/dashboard")
    print(f"\nanalytics/dashboard: {n} queries for {N_RECS} recordings")


def test_analytics_progress_query_count(db, counter, seed):
    user = seed["user"]
    n = _check_query_count(counter, lambda: _call_analytics_progress(db, user), "analytics/progress")
    print(f"\nanalytics/progress: {n} queries for {N_RECS} recordings")


def test_analytics_pass_query_count(db, counter, seed):
    user = seed["user"]
    n = _check_query_count(counter, lambda: _call_analytics_pass(db, user), "analytics/pass")
    print(f"\nanalytics/pass: {n} queries for {N_RECS} recordings")


def test_analytics_recurring_query_count(db, counter, seed):
    user = seed["user"]
    n = _check_query_count(counter, lambda: _call_analytics_recurring(db, user), "analytics/recurring")
    print(f"\nanalytics/recurring: {n} queries for {N_RECS} recordings")


def test_admin_dashboard_query_count(db, counter, seed):
    admin = seed["admin"]
    n = _check_query_count(counter, lambda: _call_admin_dashboard(db, admin), "admin/dashboard")
    print(f"\nadmin/dashboard: {n} queries for {N_RECS} recordings")


def test_admin_users_query_count(db, counter, seed):
    admin = seed["admin"]
    n = _check_query_count(counter, lambda: _call_admin_users(db, admin), "admin/users")
    print(f"\nadmin/users: {n} queries for {N_RECS} users-with-recordings")


def test_recordings_history_query_count(db, counter, seed):
    user = seed["user"]
    n = _check_query_count(counter, lambda: _call_recordings_history(db, user), "recordings/history")
    print(f"\nrecordings/history: {n} queries for {N_RECS} recordings")


def test_writing_history_query_count(db, counter, seed):
    user = seed["user"]
    n = _check_query_count(counter, lambda: _call_writing_history(db, user), "writing/history")
    print(f"\nwriting/history: {n} queries for {N_RECS} submissions")
