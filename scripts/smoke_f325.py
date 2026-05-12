"""F-325 smoke — Le Vocabulaire vocab browse API end-to-end.

Run with: python -m scripts.smoke_f325
Expected: prints PASS lines and exits 0. Cleans up its own fixtures.

Two-phase coverage:
  Phase 1 (empty-DB shape check):
    Before seeding, hit each endpoint and verify the empty-array
    response shape. Proves the F-321 seed gap doesn't break the
    browse API; F-322 FE can render an empty topic browser without
    blowing up.

  Phase 2 (seeded fixture coverage):
    Seed 1 free_general + 1 exam_tagged_TCF topic + 4 chunks (one
    per source_type). Walk every gate / filter / pagination / 404 /
    403 path the FE will exercise.

Smoke runs against the live local docker-compose Postgres via
FastAPI TestClient — same in-process pattern as scripts/smoke_f310.py
and scripts/smoke_f311.py. NOT a curl-against-localhost script; the
TestClient gives deterministic auth + DB control without spinning a
separate uvicorn.

Pytest in tests/test_vocab_browse.py covers the same surface with
more granularity; smoke is the operator-facing "is the whole thing
wired correctly" pass.
"""
from __future__ import annotations

import datetime
import sys

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.models import User
from app.models.vocabulaire import VocabChunk, VocabTopic
from app.services.jwt_tokens import mint_access_token
from main import app


_SLUG_FREE = "smoke_f325_free_loisirs"
_SLUG_EXAM = "smoke_f325_exam_tcf_voyages"
_USER_EMAIL = "smoke_f325@local"


errors: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    extra = f" -- {detail}" if detail else ""
    print(f"  [{status}] {name}{extra}")
    if not ok:
        errors.append(name)


def _cleanup(db: Session) -> None:
    """Drop all rows this smoke owns. Idempotent — slug/email
    prefixed so concurrent smoke / pytest runs don't collide."""
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


def main() -> int:
    db = SessionLocal()
    client = TestClient(app)
    try:
        _cleanup(db)

        # Smoke user
        user = User(
            email=_USER_EMAIL,
            hashed_password="x",
            full_name="F-325 Smoke",
            email_verified_at=datetime.datetime.utcnow(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        headers = {"Authorization": f"Bearer {mint_access_token(_USER_EMAIL)}"}

        # ── Phase 1: empty-DB shape check ──────────────────────────
        print("Phase 1: empty-DB shape (no smoke fixtures seeded yet)")

        r = client.get("/api/vocab/topics", headers=headers)
        check(
            "GET /topics returns 200",
            r.status_code == 200,
            f"got {r.status_code}: {r.text[:120]}",
        )
        # No smoke_f325_* slugs yet; OK if other dev seeds exist as long
        # as our namespace is empty.
        slugs_now = {t["slug"] for t in r.json().get("topics", [])}
        check(
            "no smoke_f325_* topics present pre-seed",
            not any(s.startswith("smoke_f325_") for s in slugs_now),
            f"saw: {sorted(s for s in slugs_now if s.startswith('smoke_f325_'))}",
        )

        r = client.get(
            "/api/vocab/topics?corpus_partition=exam_tagged_DELF",
            headers=headers,
        )
        check(
            "GET /topics?corpus_partition=exam_tagged_DELF empty-shape 200 + []",
            r.status_code == 200 and r.json() == {"topics": []},
            f"got {r.status_code}: {r.text[:120]}",
        )

        r = client.get("/api/vocab/topics/smoke_f325_does_not_exist", headers=headers)
        check(
            "GET /topics/{unknown} returns 404",
            r.status_code == 404,
            f"got {r.status_code}",
        )

        r = client.get("/api/vocab/topics")
        check(
            "GET /topics unauthenticated returns 401",
            r.status_code == 401,
            f"got {r.status_code}",
        )

        # ── Phase 2: seed fixtures + walk the surface ──────────────
        print("\nPhase 2: seed 2 topics + 4 chunks, walk full surface")

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
        )
        db.add(free_topic)
        db.add(exam_topic)
        db.commit()
        db.refresh(free_topic)
        db.refresh(exam_topic)

        # 4 chunks under the free topic, one per source_type
        chunks_seed = [
            ("CC_corpus", "faire la grasse matinée", "informel", "tcf", "B1"),
            ("chadi_authored", "aller au bois", "formel", "tcf", "B2"),
            ("book_lab", "prendre un verre", "informel", None, "B1"),
            ("third_party_publisher_DO_NOT_EXTRACT", "le farniente", None, None, "B1"),
        ]
        for source_type, fr, reg, exam, lvl in chunks_seed:
            db.add(VocabChunk(
                chunk_fr=fr,
                topic_id=free_topic.id,
                source_type=source_type,
                register=reg,
                exam_tag=exam,
                cefr_level=lvl,
            ))
        db.commit()

        # /topics returns both with correct locked flags
        body = client.get("/api/vocab/topics", headers=headers).json()
        by_slug = {t["slug"]: t for t in body["topics"]}
        check(
            "/topics surfaces both fixture topics",
            _SLUG_FREE in by_slug and _SLUG_EXAM in by_slug,
        )
        check(
            "free_general locked=False",
            by_slug.get(_SLUG_FREE, {}).get("locked") is False,
        )
        check(
            "exam_tagged_TCF locked=True (free-tier user)",
            by_slug.get(_SLUG_EXAM, {}).get("locked") is True,
        )

        # /topics/{slug} free — 200 + chunk_count excludes third_party
        r = client.get(f"/api/vocab/topics/{_SLUG_FREE}", headers=headers)
        body = r.json()
        check(
            "/topics/{free_slug} returns 200 + chunk_count=3 (excludes third_party)",
            r.status_code == 200 and body.get("chunk_count") == 3,
            f"got status={r.status_code} count={body.get('chunk_count')}",
        )

        # /topics/{slug} exam — 403 with F-310 tier_insufficient body
        r = client.get(f"/api/vocab/topics/{_SLUG_EXAM}", headers=headers)
        det = r.json().get("detail", {})
        check(
            "/topics/{exam_slug} returns 403 tier_insufficient",
            r.status_code == 403
            and det.get("code") == "tier_insufficient"
            and det.get("required") == "subscription"
            and det.get("current") == "free",
            f"got {r.status_code} body={r.text[:200]}",
        )

        # /chunks free — excludes third_party
        r = client.get(
            f"/api/vocab/topics/{_SLUG_FREE}/chunks", headers=headers
        )
        body = r.json()
        source_types_seen = {c["source_type"] for c in body.get("chunks", [])}
        check(
            "/chunks excludes third_party_publisher_DO_NOT_EXTRACT",
            r.status_code == 200
            and body.get("total") == 3
            and "third_party_publisher_DO_NOT_EXTRACT" not in source_types_seen,
            f"types: {source_types_seen}",
        )

        # /chunks pagination shape
        r = client.get(
            f"/api/vocab/topics/{_SLUG_FREE}/chunks?limit=2&offset=1",
            headers=headers,
        )
        body = r.json()
        check(
            "/chunks pagination: limit/offset echoed + total=3 + page=2",
            r.status_code == 200
            and body.get("limit") == 2
            and body.get("offset") == 1
            and body.get("total") == 3
            and len(body.get("chunks", [])) == 2,
        )

        # /chunks multi-filter intersection
        r = client.get(
            f"/api/vocab/topics/{_SLUG_FREE}/chunks"
            "?cefr_level=B2&exam_tag=tcf&register=formel",
            headers=headers,
        )
        body = r.json()
        check(
            "/chunks multi-filter (cefr_level=B2 + exam_tag=tcf + register=formel)"
            " returns 1 row",
            r.status_code == 200
            and body.get("total") == 1
            and (body.get("chunks") or [{}])[0].get("chunk_fr") == "aller au bois",
        )

        # /chunks exam-tagged — 403
        r = client.get(
            f"/api/vocab/topics/{_SLUG_EXAM}/chunks", headers=headers
        )
        check(
            "/chunks exam_tagged_TCF for free-tier user returns 403",
            r.status_code == 403
            and r.json().get("detail", {}).get("code") == "tier_insufficient",
            f"got {r.status_code}",
        )

        # /chunks invalid pagination — 422
        r = client.get(
            f"/api/vocab/topics/{_SLUG_FREE}/chunks?limit=999",
            headers=headers,
        )
        check(
            "/chunks limit>100 rejected as 422",
            r.status_code == 422,
            f"got {r.status_code}",
        )

        print("\nCleanup")
        _cleanup(db)
        print("  smoke fixtures removed")

        print()
        if errors:
            print(f"FAILURES: {errors}")
            return 1
        print("ALL CHECKS PASSED")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
