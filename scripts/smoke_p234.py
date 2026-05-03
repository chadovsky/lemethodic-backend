"""Smoke test for P-234 cluster detail view endpoints.

Coverage (per the 2026-05-03 plan-first lock-in):
  Step 1 — Schema imports + field shapes
           ClusterDetailResponse, ClusterLesson, VocabularyThemeRef,
           UserClusterStateResponse, RecordingHistoryEntry
  Step 2 — Service correctness:
           (a) get_cluster_detail on a known b1_to_b2 cluster
           (b) get_cluster_detail on unknown slug returns None
           (c) get_user_cluster_state with no UCS row → defaults
           (d) get_user_cluster_state with UCS + 3 UCE rows → populated
               history newest-first
  Step 3 — Endpoint contract: both endpoints, 200 + 401 + 404 unknown slug
  Step 4 — extra="forbid" enforcement on response schemas

Runs offline (no Claude API). Creates a single throwaway user
(`smoke@p234.local`); cleans up at the end.

Run: python -m scripts.smoke_p234
"""
from __future__ import annotations

import datetime
import sys

from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.database import SessionLocal
from app.models.models import (
    Cluster,
    Recording,
    User,
    UserClusterEvent,
    UserClusterStatus,
)
from app.schemas.cluster import (
    ClusterDetailResponse,
    ClusterLesson,
    RecordingHistoryEntry,
    UserClusterStateResponse,
    VocabularyThemeRef,
)
from app.services.auth import create_access_token, hash_password
from app.services.cluster_lookup import (
    get_cluster_detail,
    get_user_cluster_state,
)


SMOKE_EMAIL = "smoke@p234.local"

errors: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    extra = f" -- {detail}" if detail else ""
    print(f"  [{status}] {name}{extra}")
    if not ok:
        errors.append(name)


# ── Step 1: schema ─────────────────────────────────────────────


def step_1_schema() -> None:
    print("\nStep 1: schemas import + expected fields")
    cd = ClusterDetailResponse.model_fields
    expected_cd = {
        "id", "slug", "labels", "grammar_topic", "vocabulary_theme",
        "tache_application", "cefr_level", "lesson", "practice_prompt",
        "exercise_set",
    }
    check("ClusterDetailResponse has 10 expected fields",
          set(cd.keys()) == expected_cd,
          str(set(cd.keys()) ^ expected_cd))
    check("ClusterDetailResponse does NOT expose detection_rubric (Q1)",
          "detection_rubric" not in cd)

    cl = ClusterLesson.model_fields
    check("ClusterLesson has format/markdown/asset_url",
          set(cl.keys()) == {"format", "markdown", "asset_url"},
          str(set(cl.keys())))

    vt = VocabularyThemeRef.model_fields
    check("VocabularyThemeRef has slug/labels",
          set(vt.keys()) == {"slug", "labels"},
          str(set(vt.keys())))

    us = UserClusterStateResponse.model_fields
    expected_us = {
        "cluster_slug", "status", "last_rubric_score",
        "last_detection_result", "revisit_count", "first_started_at",
        "last_status_change_at", "absorbed_at", "recording_history",
    }
    check("UserClusterStateResponse has 9 expected fields",
          set(us.keys()) == expected_us,
          str(set(us.keys()) ^ expected_us))

    rh = RecordingHistoryEntry.model_fields
    check("RecordingHistoryEntry has 4 expected fields",
          set(rh.keys()) == {"recording_id", "created_at",
                             "detection_result", "rubric_score"},
          str(set(rh.keys())))


# ── Helpers ────────────────────────────────────────────────────


def _ensure_user(db) -> User:
    u = db.query(User).filter_by(email=SMOKE_EMAIL).first()
    if u is None:
        u = User(
            email=SMOKE_EMAIL,
            hashed_password=hash_password("smoke"),
            full_name="P-234 Smoke",
        )
        db.add(u)
        db.commit()
        db.refresh(u)
    return u


def _wipe_user_state(db, user_id: int) -> None:
    db.query(UserClusterEvent).filter_by(user_id=user_id).delete()
    db.query(UserClusterStatus).filter_by(user_id=user_id).delete()
    db.query(Recording).filter_by(user_id=user_id).delete()
    db.commit()


def _first_b1_to_b2_cluster(db) -> Cluster:
    cl = db.query(Cluster).filter(Cluster.cefr_level == "B1").first()
    if cl is None:
        raise RuntimeError(
            "smoke_p234: no B1 cluster in DB — run "
            "ingest_b1_b2_cluster_content first."
        )
    return cl


def _seed_history(db, user_id: int, cluster_id: int) -> list[int]:
    """Seed 3 recordings + 3 UCE rows. Returns recording_ids in seed
    order (oldest first); newest-first in the API response."""
    rec_ids: list[int] = []
    base = datetime.datetime.utcnow() - datetime.timedelta(days=5)
    results = ["fail", "wobble", "clean"]
    for i, det in enumerate(results):
        rec = Recording(
            user_id=user_id,
            audio_path=f"smoke/p234_{i}.wav",
            target_level="B1",
            tache_mode="tache_3",
            created_at=base + datetime.timedelta(days=i),
        )
        db.add(rec)
        db.flush()
        rec_ids.append(rec.id)
        ev = UserClusterEvent(
            user_id=user_id,
            cluster_id=cluster_id,
            from_status="not_started",
            to_status="not_started",
            triggered_by_recording_id=rec.id,
            rubric_score=0.0 if det == "fail" else (0.5 if det == "wobble" else 1.0),
            findings_json={"detection_result": det, "cluster_slug": "ignored"},
            created_at=base + datetime.timedelta(days=i),
        )
        db.add(ev)
    db.commit()
    return rec_ids


# ── Step 2: service correctness ────────────────────────────────


def step_2_service() -> None:
    print("\nStep 2: get_cluster_detail + get_user_cluster_state")
    db = SessionLocal()
    try:
        u = _ensure_user(db)
        _wipe_user_state(db, u.id)
        cl = _first_b1_to_b2_cluster(db)

        # (a) known slug
        out = get_cluster_detail(db, cl.slug)
        check("(a) returns dict for known slug", out is not None)
        if out is not None:
            check("(a) id matches", out["id"] == cl.id)
            check("(a) slug matches", out["slug"] == cl.slug)
            check("(a) tache_application set",
                  out["tache_application"] in {"tache_1", "tache_2", "tache_3"},
                  str(out.get("tache_application")))
            check("(a) lesson sub-object has 3 fields",
                  set(out["lesson"].keys()) == {"format", "markdown", "asset_url"})
            check("(a) detection_rubric NOT in response (Q1)",
                  "detection_rubric" not in out)
            # Pydantic round-trip — proves the dict matches the response shape
            try:
                ClusterDetailResponse(**out)
                check("(a) ClusterDetailResponse round-trip OK", True)
            except ValidationError as e:
                check("(a) ClusterDetailResponse round-trip OK", False, str(e)[:120])

        # (b) unknown slug
        out = get_cluster_detail(db, "definitely-not-a-real-cluster-zzz")
        check("(b) unknown slug → None", out is None)

        # (c) state with no UCS row → defaults
        out = get_user_cluster_state(db, u, cl.slug)
        check("(c) returns dict for cluster w/o UCS", out is not None)
        if out is not None:
            check("(c) status=not_started", out["status"] == "not_started",
                  str(out["status"]))
            check("(c) revisit_count=0", out["revisit_count"] == 0)
            check("(c) recording_history=[]",
                  out["recording_history"] == [])
            check("(c) all timestamps null",
                  all(out[k] is None for k in (
                      "first_started_at", "last_status_change_at",
                      "absorbed_at", "last_rubric_score",
                      "last_detection_result")))
            try:
                UserClusterStateResponse(**out)
                check("(c) UserClusterStateResponse round-trip OK", True)
            except ValidationError as e:
                check("(c) UserClusterStateResponse round-trip OK",
                      False, str(e)[:120])

        # (d) state with UCS + 3 UCE rows → populated history newest-first
        rec_ids = _seed_history(db, u.id, cl.id)
        ucs = UserClusterStatus(
            user_id=u.id,
            cluster_id=cl.id,
            status="in_progress",
            last_rubric_score=1.0,
            last_evaluated_recording_id=rec_ids[-1],
            last_detection_result="clean",
            revisit_count=1,
            first_started_at=datetime.datetime.utcnow(),
            last_status_change_at=datetime.datetime.utcnow(),
        )
        db.add(ucs)
        db.commit()

        out = get_user_cluster_state(db, u, cl.slug)
        check("(d) status=in_progress",
              out["status"] == "in_progress", str(out["status"]))
        check("(d) revisit_count=1", out["revisit_count"] == 1)
        check("(d) recording_history len=3",
              len(out["recording_history"]) == 3,
              str(len(out["recording_history"])))
        # Newest first → the most recently seeded (clean) recording leads
        check("(d) history[0] is newest (clean)",
              out["recording_history"][0]["detection_result"] == "clean",
              str(out["recording_history"][0]["detection_result"]))
        check("(d) history[2] is oldest (fail)",
              out["recording_history"][2]["detection_result"] == "fail",
              str(out["recording_history"][2]["detection_result"]))
        check("(d) history[0] recording_id matches newest seed",
              out["recording_history"][0]["recording_id"] == rec_ids[-1])
        try:
            UserClusterStateResponse(**out)
            check("(d) UserClusterStateResponse round-trip OK", True)
        except ValidationError as e:
            check("(d) UserClusterStateResponse round-trip OK",
                  False, str(e)[:120])
    finally:
        db.close()


# ── Step 3: endpoint contract ──────────────────────────────────


def step_3_endpoint() -> None:
    print("\nStep 3: GET endpoints — 200 / 401 / 404")
    from main import app
    client = TestClient(app)

    db = SessionLocal()
    try:
        u = _ensure_user(db)
        cl = _first_b1_to_b2_cluster(db)
        token = create_access_token({"sub": u.email})
    finally:
        db.close()
    auth = {"Authorization": f"Bearer {token}"}

    # /api/clusters/{slug} happy path
    r = client.get(f"/api/clusters/{cl.slug}", headers=auth)
    check("/api/clusters/{slug} → 200", r.status_code == 200, str(r.status_code))
    body = r.json()
    check("body.slug matches", body.get("slug") == cl.slug)
    check("body has lesson sub-object",
          isinstance(body.get("lesson"), dict)
          and {"format", "markdown", "asset_url"}.issubset(set(body["lesson"].keys())))
    check("body does NOT include detection_rubric",
          "detection_rubric" not in body)

    # Unknown slug → 404
    r = client.get("/api/clusters/zzz-not-real", headers=auth)
    check("/api/clusters/zzz → 404", r.status_code == 404, str(r.status_code))

    # Unauth → 401
    r = client.get(f"/api/clusters/{cl.slug}")
    check("/api/clusters/{slug} unauth → 401",
          r.status_code == 401, str(r.status_code))

    # /api/users/me/clusters/{slug} happy path
    r = client.get(f"/api/users/me/clusters/{cl.slug}", headers=auth)
    check("/api/users/me/clusters/{slug} → 200",
          r.status_code == 200, str(r.status_code))
    body = r.json()
    check("body has cluster_slug echo",
          body.get("cluster_slug") == cl.slug)
    check("body has recording_history list",
          isinstance(body.get("recording_history"), list))

    # Unknown slug → 404
    r = client.get("/api/users/me/clusters/zzz-not-real", headers=auth)
    check("/api/users/me/clusters/zzz → 404",
          r.status_code == 404, str(r.status_code))

    # Unauth → 401
    r = client.get(f"/api/users/me/clusters/{cl.slug}")
    check("/api/users/me/clusters unauth → 401",
          r.status_code == 401, str(r.status_code))


# ── Step 4: extra="forbid" enforcement ─────────────────────────


def step_4_forbid_extra() -> None:
    print("\nStep 4: extra='forbid' enforcement")
    base_lesson = {"format": "markdown", "markdown": "x", "asset_url": ""}
    base_cluster = {
        "id": 1,
        "slug": "x",
        "labels": {},
        "grammar_topic": "x",
        "vocabulary_theme": None,
        "tache_application": "tache_3",
        "cefr_level": "B1",
        "lesson": base_lesson,
        "practice_prompt": {},
        "exercise_set": [],
    }
    base_state = {
        "cluster_slug": "x",
        "status": "not_started",
        "last_rubric_score": None,
        "last_detection_result": None,
        "revisit_count": 0,
        "first_started_at": None,
        "last_status_change_at": None,
        "absorbed_at": None,
        "recording_history": [],
    }

    try:
        ClusterDetailResponse(**base_cluster)
        check("ClusterDetailResponse valid input parses", True)
    except ValidationError as e:
        check("ClusterDetailResponse valid input parses", False, str(e)[:120])

    try:
        ClusterDetailResponse(**base_cluster, surprise="bad")
        check("ClusterDetailResponse extra field rejected", False, "no error")
    except ValidationError:
        check("ClusterDetailResponse extra field rejected", True)

    try:
        ClusterDetailResponse(**{**base_cluster, "tache_application": "tache_4"})
        check("invalid tache_application rejected", False, "no error")
    except ValidationError:
        check("invalid tache_application rejected", True)

    try:
        UserClusterStateResponse(**base_state)
        check("UserClusterStateResponse valid input parses", True)
    except ValidationError as e:
        check("UserClusterStateResponse valid input parses",
              False, str(e)[:120])

    try:
        UserClusterStateResponse(**{**base_state, "status": "lol"})
        check("invalid status rejected", False, "no error")
    except ValidationError:
        check("invalid status rejected", True)

    try:
        UserClusterStateResponse(**base_state, surprise="bad")
        check("UserClusterStateResponse extra field rejected", False, "no error")
    except ValidationError:
        check("UserClusterStateResponse extra field rejected", True)


# ── Cleanup ────────────────────────────────────────────────────


def cleanup() -> None:
    print("\nCleanup")
    db = SessionLocal()
    try:
        u = db.query(User).filter_by(email=SMOKE_EMAIL).first()
        if u:
            _wipe_user_state(db, u.id)
            db.delete(u)
            db.commit()
            print("  test rows removed")
    finally:
        db.close()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        step_1_schema()
        step_2_service()
        step_3_endpoint()
        step_4_forbid_extra()
    finally:
        cleanup()

    print()
    if errors:
        print(f"FAILURES ({len(errors)}): {errors}")
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
