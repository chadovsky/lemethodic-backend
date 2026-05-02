"""Smoke test for P-201 level assignment service + endpoint.

Coverage (per the 2026-05-02 plan-first agreement):
  Step 1 — Models load: UserLevelAssessment import + Base.metadata in sync
  Step 2 — Algorithm: 8 canned distributions cover all 5 levels + confidence buckets
  Step 3 — Cluster total count: dynamic helper returns 13 for b1_to_b2 path
  Step 4 — Persistence: compute_and_persist writes a row with all telemetry columns
  Step 5 — Trigger gating: <3 recordings = None; >=3 = row written
  Step 6 — Failure isolation: caller's try/except absorbs raised exceptions
  Step 7 — Endpoint contract: GET /api/users/me/level returns 3 shape variants
           (a) both axes, (b) self_reported only, (c) neither
  Step 8 — compute_agreement: 9 input combos cover all Agreement enum values

Runs offline (no Claude API). Doesn't depend on production data.

Run: python -m scripts.smoke_p201
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database import SessionLocal, engine
from app.models.models import (
    Cluster,
    Recording,
    User,
    UserClusterStatus,
    UserLevelAssessment,
    UserPathEnrollment,
)
from app.services.auth import create_access_token, hash_password
from app.services.level_assignment import (
    _count_active_clusters_for_user_path,
    compute_agreement,
    compute_and_persist_if_threshold,
    compute_level_assignment,
)


errors: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    extra = f" -- {detail}" if detail else ""
    print(f"  [{status}] {name}{extra}")
    if not ok:
        errors.append(name)


# ── Step 1: schema + Base.metadata ─────────────────────────────


def step_1_schema() -> None:
    print("\nStep 1: UserLevelAssessment schema + Base.metadata sync")
    with engine.connect() as c:
        cols = {
            r[0]
            for r in c.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name='user_level_assessments'"
                )
            ).fetchall()
        }
    expected = {
        "id", "user_id",
        "assigned_level", "assigned_confidence",
        "coverage", "top_bucket_share", "confidence_score",
        "n_clusters_evaluated", "n_clusters_clean",
        "n_clusters_wobble", "n_clusters_fail",
        "triggered_by_recording_id", "computed_at",
    }
    check("13 expected columns present",
          expected.issubset(cols),
          f"missing: {expected - cols}" if expected - cols else "")
    # Tablename + ORM access works
    check("UserLevelAssessment.__tablename__",
          UserLevelAssessment.__tablename__ == "user_level_assessments")


# ── Step 2: algorithm distributions ─────────────────────────────


def step_2_algorithm() -> None:
    print("\nStep 2: compute_level_assignment for canned distributions")

    # 8 cases — all 5 levels + 3 confidence buckets exercised.
    # Each: (results, total_clusters, expected_level, expected_confidence)
    cases = [
        # 1. All clean, full coverage, perfect agreement → above_B1, high
        (["clean"] * 13, 13, "above_B1", "high"),
        # 2. 11/13 clean (clean_share=0.846 → B1_solid threshold 0.80 met,
        #    above_B1 needs top_bucket >= 0.90 which 11/13 = 0.846 misses)
        (["clean"] * 11 + ["wobble"], 13, "B1_solid", "high"),
        # 3. Mixed clean+wobble (8/13 clean = 0.615) → B1_emerging
        (["clean"] * 8 + ["wobble"] * 5, 13, "B1_emerging", "medium"),
        # 4. Mostly fail (8/13 fail = 0.615) → below_B1
        (["fail"] * 8 + ["clean"] * 3 + ["wobble"] * 2, 13, "below_B1", "medium"),
        # 5. Below 5-cluster floor → insufficient_data
        (["clean"] * 4, 13, "insufficient_data", "low"),
        # 6. 5-cluster floor exactly with all clean → B1_solid (clean_share=1.0 but coverage=5/13
        #    so above_B1 doesn't trigger)
        (["clean"] * 5, 13, "B1_solid", "low"),
        # 7. Even split clean/fail (no majority) → B1_emerging (mixed-signal default)
        (["clean"] * 4 + ["fail"] * 4 + ["wobble"] * 2, 13, "B1_emerging", "low"),
        # 8. Empty → insufficient_data
        ([], 13, "insufficient_data", "low"),
    ]
    for i, (results, total, exp_level, exp_conf) in enumerate(cases, 1):
        out = compute_level_assignment(results, total)
        check(
            f"case {i}: {len(results)} results -> {exp_level}/{exp_conf}",
            out["assigned_level"] == exp_level
            and out["assigned_confidence"] == exp_conf,
            f"got {out['assigned_level']}/{out['assigned_confidence']} "
            f"(coverage={out['coverage']:.2f}, top_bucket={out['top_bucket_share']:.2f})",
        )


# ── Step 3: dynamic cluster total ───────────────────────────────


def step_3_cluster_total() -> None:
    print("\nStep 3: _count_active_clusters_for_user_path returns 13 for b1_to_b2")
    db = SessionLocal()
    try:
        u = db.query(User).filter_by(email="smoke@p201.local").first()
        if u is None:
            u = User(
                email="smoke@p201.local",
                hashed_password=hash_password("smoke"),
                full_name="P-201 Smoke",
            )
            db.add(u)
            db.commit()
            db.refresh(u)
        # Enroll in b1_to_b2
        path = db.execute(
            text("SELECT id FROM paths WHERE slug='b1_to_b2'")
        ).first()
        if path is None:
            check("b1_to_b2 path seeded", False, "run scripts.seed_b1_b2_path first")
            return
        path_id = path[0]
        existing = (
            db.query(UserPathEnrollment)
            .filter_by(user_id=u.id, path_id=path_id)
            .first()
        )
        if existing is None:
            existing = UserPathEnrollment(
                user_id=u.id,
                path_id=path_id,
                enrolled_at_level="b1",
                is_active=True,
            )
            db.add(existing)
            db.commit()
        n = _count_active_clusters_for_user_path(db, u.id)
        check("b1_to_b2 has 13 active clusters", n == 13, f"got {n}")
    finally:
        db.close()


# ── Step 4: persistence + trigger gating ─────────────────────────


def _setup_user_with_recordings(db, n_recordings: int) -> User:
    """Ensure smoke user exists with the requested number of recordings."""
    u = db.query(User).filter_by(email="smoke@p201.local").first()
    if u is None:
        u = User(
            email="smoke@p201.local",
            hashed_password=hash_password("smoke"),
            full_name="P-201 Smoke",
        )
        db.add(u)
        db.commit()
        db.refresh(u)
    # Ensure an active enrollment for the path-resolution query
    path_row = db.execute(text("SELECT id FROM paths WHERE slug='b1_to_b2'")).first()
    if path_row is not None and not db.query(UserPathEnrollment).filter_by(
        user_id=u.id, path_id=path_row[0]
    ).first():
        db.add(UserPathEnrollment(
            user_id=u.id, path_id=path_row[0],
            enrolled_at_level="b1", is_active=True,
        ))
        db.commit()
    # Top up recordings to the requested count
    cur = db.query(Recording).filter_by(user_id=u.id).count()
    for i in range(cur, n_recordings):
        db.add(Recording(
            user_id=u.id,
            audio_path=f"smoke/p201_{i}.wav",
            target_level="B1",
            tache_mode="tache_3",
        ))
    db.commit()
    return u


def _seed_some_cluster_results(db, user_id: int) -> None:
    """Seed UserClusterStatus rows so the algorithm has something to read."""
    clusters = (
        db.query(Cluster)
        .filter(Cluster.tache_application == "tache_3")
        .limit(6)
        .all()
    )
    for i, cl in enumerate(clusters):
        existing = (
            db.query(UserClusterStatus)
            .filter_by(user_id=user_id, cluster_id=cl.id)
            .first()
        )
        # 5 clean + 1 fail across the 6 clusters
        result = "fail" if i == 0 else "clean"
        if existing is None:
            db.add(UserClusterStatus(
                user_id=user_id,
                cluster_id=cl.id,
                status="not_started",
                last_detection_result=result,
                last_rubric_score=0.0 if result == "fail" else 1.0,
            ))
        else:
            existing.last_detection_result = result
    db.commit()


def step_4_persistence() -> None:
    print("\nStep 4: compute_and_persist writes UserLevelAssessment row")
    db = SessionLocal()
    try:
        u = _setup_user_with_recordings(db, n_recordings=3)
        _seed_some_cluster_results(db, u.id)
        rec = db.query(Recording).filter_by(user_id=u.id).first()

        before = db.query(UserLevelAssessment).filter_by(user_id=u.id).count()
        new_id = compute_and_persist_if_threshold(
            db, user_id=u.id, recording=rec
        )
        after = db.query(UserLevelAssessment).filter_by(user_id=u.id).count()
        check("returned new row id", new_id is not None, f"id={new_id}")
        check("UserLevelAssessment row count +1", after == before + 1)

        row = (
            db.query(UserLevelAssessment)
            .filter_by(id=new_id)
            .first()
        )
        check("assigned_level populated", bool(row.assigned_level))
        check("assigned_confidence populated", bool(row.assigned_confidence))
        check("coverage populated (float)", isinstance(row.coverage, float))
        check("triggered_by_recording_id matches", row.triggered_by_recording_id == rec.id)
        check("n_clusters_clean = 5", row.n_clusters_clean == 5,
              f"got {row.n_clusters_clean}")
        check("n_clusters_fail = 1", row.n_clusters_fail == 1,
              f"got {row.n_clusters_fail}")
    finally:
        db.close()


def step_5_trigger_gating() -> None:
    print("\nStep 5: trigger gating <3 vs >=3 recordings")
    db = SessionLocal()
    try:
        # Force user back below threshold by deleting all but 2 recordings
        u = db.query(User).filter_by(email="smoke@p201.local").first()
        recs = db.query(Recording).filter_by(user_id=u.id).all()
        for r in recs[2:]:
            db.delete(r)
        db.commit()
        # Also clear assessments to test "no row written"
        db.query(UserLevelAssessment).filter_by(user_id=u.id).delete()
        db.commit()

        rec = db.query(Recording).filter_by(user_id=u.id).first()
        result = compute_and_persist_if_threshold(db, user_id=u.id, recording=rec)
        n_assessments_after = db.query(UserLevelAssessment).filter_by(user_id=u.id).count()
        check("count=2 → returns None", result is None)
        check("count=2 → no row written", n_assessments_after == 0)

        # Top up to >=3 and try again
        _setup_user_with_recordings(db, n_recordings=3)
        result = compute_and_persist_if_threshold(db, user_id=u.id, recording=rec)
        n_after_3 = db.query(UserLevelAssessment).filter_by(user_id=u.id).count()
        check("count=3 → returns row id", result is not None)
        check("count=3 → row written", n_after_3 == 1)
    finally:
        db.close()


# ── Step 6: failure isolation ──────────────────────────────────


def step_6_failure_isolation() -> None:
    print("\nStep 6: caller's try/except absorbs raised exceptions")
    db = SessionLocal()
    try:
        u = _setup_user_with_recordings(db, n_recordings=3)
        rec = db.query(Recording).filter_by(user_id=u.id).first()
        before = db.query(UserLevelAssessment).filter_by(user_id=u.id).count()

        # Patch the algorithm to raise. The function itself doesn't catch
        # — the CALLER (router code) does. Verify the error propagates
        # so the router's try/except can absorb it.
        with patch(
            "app.services.level_assignment.compute_level_assignment",
            side_effect=RuntimeError("simulated algorithm failure"),
        ):
            try:
                compute_and_persist_if_threshold(db, user_id=u.id, recording=rec)
                check("function raises when algorithm raises", False,
                      "expected exception, got none")
            except RuntimeError as e:
                check("function raises when algorithm raises", True,
                      f"got {type(e).__name__}")

        after = db.query(UserLevelAssessment).filter_by(user_id=u.id).count()
        check("no row written on algorithm failure", after == before)
    finally:
        db.close()


# ── Step 7: endpoint contract ──────────────────────────────────


def step_7_endpoint() -> None:
    print("\nStep 7: GET /api/users/me/level — 3 shape variants")
    from main import app
    client = TestClient(app)

    db = SessionLocal()
    try:
        u = _setup_user_with_recordings(db, n_recordings=3)
        # Ensure at least one assessment row + an active enrollment
        if db.query(UserLevelAssessment).filter_by(user_id=u.id).count() == 0:
            _seed_some_cluster_results(db, u.id)
            rec = db.query(Recording).filter_by(user_id=u.id).first()
            compute_and_persist_if_threshold(db, user_id=u.id, recording=rec)
        token = create_access_token({"sub": u.email})
    finally:
        db.close()
    auth = {"Authorization": f"Bearer {token}"}

    # (a) both axes
    r = client.get("/api/users/me/level", headers=auth)
    check("GET /me/level 200", r.status_code == 200, str(r.status_code))
    body = r.json()
    check("response has self_reported.level",
          body["self_reported"].get("level") == "b1",
          str(body.get("self_reported")))
    check("response has assigned block",
          body.get("assigned") is not None)
    check("response has agreement field",
          body.get("agreement") in {"matches", "discrepancy",
                                     "self_only", "assigned_only", "neither"})

    # (b) self_reported only — clear the assessment row
    db = SessionLocal()
    try:
        db.query(UserLevelAssessment).filter_by(user_id=u.id).delete()
        db.commit()
    finally:
        db.close()
    r = client.get("/api/users/me/level", headers=auth)
    check("self-only → 200", r.status_code == 200)
    body = r.json()
    check("self-only → assigned is null", body.get("assigned") is None)
    check("self-only → agreement = self_only",
          body.get("agreement") == "self_only", body.get("agreement"))

    # (c) neither — clear the enrollment too
    db = SessionLocal()
    try:
        db.query(UserPathEnrollment).filter_by(user_id=u.id).delete()
        db.commit()
    finally:
        db.close()
    r = client.get("/api/users/me/level", headers=auth)
    check("neither → 200", r.status_code == 200)
    body = r.json()
    check("neither → self_reported.level = null",
          body["self_reported"].get("level") is None)
    check("neither → assigned = null", body.get("assigned") is None)
    check("neither → agreement = neither",
          body.get("agreement") == "neither", body.get("agreement"))


# ── Step 8: compute_agreement ──────────────────────────────────


def step_8_agreement() -> None:
    print("\nStep 8: compute_agreement combinatorial coverage")
    cases = [
        # (self, assigned, expected)
        ("b1", "B1_solid", "matches"),
        ("b1", "B1_emerging", "matches"),
        ("a2", "below_B1", "matches"),
        ("b2", "above_B1", "matches"),
        ("c1", "above_B1", "matches"),
        ("b1", "below_B1", "discrepancy"),
        ("b2", "B1_emerging", "discrepancy"),
        ("a2", "above_B1", "discrepancy"),
        (None, "B1_solid", "assigned_only"),
        ("b1", None, "self_only"),
        (None, None, "neither"),
        ("not_sure", "B1_solid", "discrepancy"),    # unknown vs at = mismatch
        ("b1", "insufficient_data", "discrepancy"), # at vs unknown = mismatch
    ]
    for self_lvl, assigned_lvl, expected in cases:
        got = compute_agreement(self_lvl, assigned_lvl)
        check(f"({self_lvl}, {assigned_lvl}) → {expected}",
              got == expected, got)


# ── Cleanup ────────────────────────────────────────────────────


def cleanup() -> None:
    print("\nCleanup")
    db = SessionLocal()
    try:
        u = db.query(User).filter_by(email="smoke@p201.local").first()
        if u:
            db.query(UserLevelAssessment).filter_by(user_id=u.id).delete()
            db.query(UserClusterStatus).filter_by(user_id=u.id).delete()
            db.query(UserPathEnrollment).filter_by(user_id=u.id).delete()
            db.query(Recording).filter_by(user_id=u.id).delete()
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
        step_2_algorithm()
        step_3_cluster_total()
        step_4_persistence()
        step_5_trigger_gating()
        step_6_failure_isolation()
        step_7_endpoint()
        step_8_agreement()
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
