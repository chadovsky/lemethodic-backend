"""P-105 -- server-side tier enforcement.

Proves that _resolve_user_tier() reads subscription_tier from the DB
and that enforce_min_tier() correctly gates the endpoint.

Endpoint under test: GET /api/vocab/topics/{slug} for an exam_tagged_*
topic (enforces "subscription" minimum via _enforce_partition_gate).

2 cases:
  1. subscription_tier="free" -> 403 tier_insufficient
  2. subscription_tier="subscription" -> 200
"""
from __future__ import annotations

import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.models import User
from app.models.vocabulaire import VocabTopic
from app.services.jwt_tokens import mint_access_token
from main import app


_SLUG = "p105_enforcement_exam_tcf"
_EMAIL_FREE = "p105_free@local"
_EMAIL_SUB = "p105_sub@local"

client = TestClient(app)


def _teardown(db: Session) -> None:
    db.execute(VocabTopic.__table__.delete().where(VocabTopic.slug == _SLUG))
    db.execute(
        User.__table__.delete().where(User.email.in_([_EMAIL_FREE, _EMAIL_SUB]))
    )
    db.commit()


@pytest.fixture(scope="module")
def db_session():
    s = SessionLocal()
    yield s
    s.close()


@pytest.fixture(scope="module", autouse=True)
def seed(db_session: Session):
    _teardown(db_session)

    free_user = User(
        email=_EMAIL_FREE,
        hashed_password="x",
        full_name="P105 Free",
        email_verified_at=datetime.datetime.utcnow(),
        subscription_tier="free",
    )
    sub_user = User(
        email=_EMAIL_SUB,
        hashed_password="x",
        full_name="P105 Sub",
        email_verified_at=datetime.datetime.utcnow(),
        subscription_tier="subscription",
    )
    topic = VocabTopic(
        slug=_SLUG,
        labels={"fr": "Oral TCF P105", "en": "TCF Oral P105"},
        corpus_partition="exam_tagged_TCF",
        cefr_level_min="B1",
        cefr_level_max="C1",
    )
    db_session.add_all([free_user, sub_user, topic])
    db_session.commit()

    yield

    _teardown(db_session)


@pytest.fixture(scope="module")
def free_headers():
    return {"Authorization": f"Bearer {mint_access_token(_EMAIL_FREE)}"}


@pytest.fixture(scope="module")
def sub_headers():
    return {"Authorization": f"Bearer {mint_access_token(_EMAIL_SUB)}"}


def test_free_user_gets_403_on_exam_topic(free_headers):
    r = client.get(f"/api/vocab/topics/{_SLUG}", headers=free_headers)
    assert r.status_code == 403, r.text
    detail = r.json()["detail"]
    assert detail["code"] == "tier_insufficient"
    assert detail["required"] == "subscription"
    assert detail["current"] == "free"


def test_subscription_user_gets_200_on_exam_topic(sub_headers):
    r = client.get(f"/api/vocab/topics/{_SLUG}", headers=sub_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["slug"] == _SLUG
    assert body["corpus_partition"] == "exam_tagged_TCF"
