"""F-325 — pytest coverage for the vocab browse API.

Introduces pytest convention to the codebase (was smoke-only). Runs
against the local docker-compose Postgres — same DB the dev server
uses. Fixtures are self-cleaning via slug/email namespacing
(``smoke_f325_*`` / ``smoke_f325@local`` prefixes) so concurrent runs
don't collide with each other or with smoke_*.py scripts.

12 cases (mirroring F-325 plan §6):
   1. GET /topics unauthenticated -> 401
   2. GET /topics empty namespace -> 200 with []
   3. GET /topics with 2 fixtures (free + exam_tagged_TCF) -> 2 rows, locked correct
   4. GET /topics filtered by corpus_partition=free_general -> 1 row
   5. GET /topics filtered by bad enum -> 422
   6. GET /topics/{slug} free topic -> 200 with chunk_count
   7. GET /topics/{slug} exam_tagged + free user -> 403 tier_insufficient
   8. GET /topics/{slug} unknown slug -> 404
   9. GET /topics/{slug}/chunks excludes third_party_publisher row
  10. GET /topics/{slug}/chunks pagination (limit/offset shape)
  11. GET /topics/{slug}/chunks multi-filter (cefr_level + exam_tag + register)
  12. GET /topics/{slug}/chunks exam_tagged + free user -> 403

Tests deliberately don't share state across functions — each one
asserts independently against the fixtures available at module scope.
"""
from __future__ import annotations

import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.models import User
from app.models.vocabulaire import VocabChunk, VocabTopic
from app.services.jwt_tokens import mint_access_token
from main import app


# ── slug / email namespacing ─────────────────────────────────────
_SLUG_FREE = "smoke_f325_free_loisirs"
_SLUG_EXAM = "smoke_f325_exam_tcf_voyages"
_SLUG_UNKNOWN = "smoke_f325_does_not_exist"
_USER_EMAIL = "smoke_f325@local"


client = TestClient(app)


# ── shared fixtures ──────────────────────────────────────────────


def _delete_namespace(db: Session) -> None:
    """Drop all rows this test suite owns. Safe to call before AND
    after the suite — idempotent + scoped by the slug/email prefix."""
    db.execute(
        VocabChunk.__table__.delete().where(
            VocabChunk.topic_id.in_(
                db.query(VocabTopic.id).filter(
                    VocabTopic.slug.like("smoke_f325_%")
                )
            )
        )
    )
    db.execute(
        VocabTopic.__table__.delete().where(VocabTopic.slug.like("smoke_f325_%"))
    )
    db.execute(User.__table__.delete().where(User.email == _USER_EMAIL))
    db.commit()


@pytest.fixture(scope="module")
def db_session():
    s = SessionLocal()
    yield s
    s.close()


@pytest.fixture(scope="module", autouse=True)
def fixture_state(db_session: Session):
    """Module-scoped fixture: seed the 2 topics + 4 chunks + 1 user,
    yield, then clean up. autouse so every test sees the seeded state
    without explicitly depending on the fixture name."""
    _delete_namespace(db_session)

    # User — must be email_verified_at-set so get_current_user passes
    # the F-310 Phase B gate.
    user = User(
        email=_USER_EMAIL,
        hashed_password="x",
        full_name="F-325 Test",
        email_verified_at=datetime.datetime.utcnow(),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # 2 topics
    free_topic = VocabTopic(
        slug=_SLUG_FREE,
        labels={"fr": "Loisirs", "en": "Leisure"},
        description={"fr": "Activités de loisirs"},
        corpus_partition="free_general",
        cefr_level_min="A1",
        cefr_level_max="B2",
    )
    exam_topic = VocabTopic(
        slug=_SLUG_EXAM,
        labels={"fr": "Voyages TCF", "en": "TCF travel"},
        corpus_partition="exam_tagged_TCF",
        cefr_level_min="B1",
        cefr_level_max="C1",
    )
    db_session.add(free_topic)
    db_session.add(exam_topic)
    db_session.commit()
    db_session.refresh(free_topic)
    db_session.refresh(exam_topic)

    # 4 chunks under the free topic (one per source_type, including
    # the third_party row that the API must exclude).
    chunks = [
        VocabChunk(
            chunk_fr="faire la grasse matinée",
            chunk_en="to sleep in",
            topic_id=free_topic.id,
            source="https://fr.wiktionary.org/wiki/grasse_matinée",
            source_type="CC_corpus",
            register="informel",
            exam_tag="tcf",
            cefr_level="B1",
        ),
        VocabChunk(
            chunk_fr="aller au bois",
            chunk_en="to take a walk in the woods",
            topic_id=free_topic.id,
            source="andre-course-2024.docx",
            source_type="chadi_authored",
            register="formel",
            exam_tag="tcf",
            cefr_level="B2",
        ),
        VocabChunk(
            chunk_fr="prendre un verre",
            chunk_en="to grab a drink",
            topic_id=free_topic.id,
            source="book-lab-volume-2",
            source_type="book_lab",
            register="informel",
            cefr_level="B1",
        ),
        VocabChunk(
            chunk_fr="le farniente",
            topic_id=free_topic.id,
            source="Vocabulaire Progressif B1",
            source_type="third_party_publisher_DO_NOT_EXTRACT",
            cefr_level="B1",
        ),
    ]
    for chunk in chunks:
        db_session.add(chunk)
    db_session.commit()

    yield {
        "user_id": user.id,
        "free_topic_id": free_topic.id,
        "exam_topic_id": exam_topic.id,
    }

    _delete_namespace(db_session)


@pytest.fixture(scope="module")
def auth_headers() -> dict:
    """Bearer-token headers for the test user. F-325 endpoints honor
    both cookie and Authorization-header auth (see app/services/auth.py
    `_resolve_token`); header is cleaner for tests."""
    return {"Authorization": f"Bearer {mint_access_token(_USER_EMAIL)}"}


# ── tests ────────────────────────────────────────────────────────


def test_01_topics_unauthenticated_401():
    r = client.get("/api/vocab/topics")
    assert r.status_code == 401, r.text


def test_02_topics_filtered_to_empty_partition_returns_empty_array(auth_headers):
    # Use a filter value the fixtures don't populate — proves empty
    # response shape without needing a real empty DB.
    r = client.get(
        "/api/vocab/topics?corpus_partition=exam_tagged_DELF",
        headers=auth_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body == {"topics": []}, body


def test_03_topics_unfiltered_returns_both_with_locked_flag(auth_headers):
    r = client.get("/api/vocab/topics", headers=auth_headers)
    assert r.status_code == 200
    topics = r.json()["topics"]
    by_slug = {t["slug"]: t for t in topics}
    # Only our fixture slugs — earlier rows from prod/dev seeds may also
    # appear; assert on the prefix subset.
    assert _SLUG_FREE in by_slug
    assert _SLUG_EXAM in by_slug
    assert by_slug[_SLUG_FREE]["locked"] is False
    # Default tier resolver returns "free" for all users until P-105;
    # exam_tagged_* is locked for every test user today.
    assert by_slug[_SLUG_EXAM]["locked"] is True
    assert by_slug[_SLUG_FREE]["corpus_partition"] == "free_general"
    assert by_slug[_SLUG_EXAM]["corpus_partition"] == "exam_tagged_TCF"


def test_04_topics_filter_by_corpus_partition_free_general(auth_headers):
    r = client.get(
        "/api/vocab/topics?corpus_partition=free_general",
        headers=auth_headers,
    )
    assert r.status_code == 200
    slugs = {t["slug"] for t in r.json()["topics"]}
    assert _SLUG_FREE in slugs
    assert _SLUG_EXAM not in slugs


def test_05_topics_filter_invalid_enum_422(auth_headers):
    r = client.get(
        "/api/vocab/topics?corpus_partition=exam_tagged_SAT",
        headers=auth_headers,
    )
    assert r.status_code == 422, r.text


def test_06_topic_detail_free_topic_returns_chunk_count(auth_headers):
    r = client.get(f"/api/vocab/topics/{_SLUG_FREE}", headers=auth_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["slug"] == _SLUG_FREE
    # chunk_count excludes the third_party_publisher row — 3, not 4.
    assert body["chunk_count"] == 3, body
    assert body["corpus_partition"] == "free_general"


def test_07_topic_detail_exam_tagged_for_free_user_403(auth_headers):
    r = client.get(f"/api/vocab/topics/{_SLUG_EXAM}", headers=auth_headers)
    assert r.status_code == 403, r.text
    detail = r.json()["detail"]
    assert detail["code"] == "tier_insufficient"
    assert detail["required"] == "subscription"
    assert detail["current"] == "free"


def test_08_topic_detail_unknown_slug_404(auth_headers):
    r = client.get(f"/api/vocab/topics/{_SLUG_UNKNOWN}", headers=auth_headers)
    assert r.status_code == 404, r.text


def test_09_chunks_excludes_third_party_publisher(auth_headers):
    r = client.get(
        f"/api/vocab/topics/{_SLUG_FREE}/chunks", headers=auth_headers
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 3, body
    assert len(body["chunks"]) == 3
    source_types = {c["source_type"] for c in body["chunks"]}
    assert "third_party_publisher_DO_NOT_EXTRACT" not in source_types
    # Sanity: the other 3 types are present.
    assert source_types == {"CC_corpus", "chadi_authored", "book_lab"}


def test_10_chunks_pagination_shape(auth_headers):
    r = client.get(
        f"/api/vocab/topics/{_SLUG_FREE}/chunks?limit=2&offset=1",
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["limit"] == 2
    assert body["offset"] == 1
    assert body["total"] == 3  # total reflects post-exclusion, not page
    assert len(body["chunks"]) == 2


def test_11_chunks_multi_filter_intersection(auth_headers):
    r = client.get(
        f"/api/vocab/topics/{_SLUG_FREE}/chunks"
        "?cefr_level=B2&exam_tag=tcf&register=formel",
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # Only the "aller au bois" chunk matches all three filters.
    assert body["total"] == 1
    assert len(body["chunks"]) == 1
    assert body["chunks"][0]["chunk_fr"] == "aller au bois"


def test_12_chunks_exam_tagged_for_free_user_403(auth_headers):
    r = client.get(
        f"/api/vocab/topics/{_SLUG_EXAM}/chunks", headers=auth_headers
    )
    assert r.status_code == 403, r.text
    assert r.json()["detail"]["code"] == "tier_insufficient"


def test_13_pagination_bounds_enforced(auth_headers):
    """Defensive: ge/le bounds rejected as 422 (FastAPI Query
    validation). Not in original 12-case plan but trivial to add."""
    bad = client.get(
        f"/api/vocab/topics/{_SLUG_FREE}/chunks?limit=999",
        headers=auth_headers,
    )
    assert bad.status_code == 422

    bad2 = client.get(
        f"/api/vocab/topics/{_SLUG_FREE}/chunks?offset=-1",
        headers=auth_headers,
    )
    assert bad2.status_code == 422
