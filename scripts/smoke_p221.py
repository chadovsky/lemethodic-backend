"""Smoke test for P-221 diagnostic state service + endpoint.

Coverage (per the 2026-05-02 plan-first lock-in):
  Step 1 — Schema imports: DiagnosticStateResponse + AssignedBlock new fields
  Step 2 — Service state machine (5 cases):
           (a) no enrollment → "no_path"
           (b) enrollment + 0 recordings → "in_progress", T1/T2/T3=False, next=1
           (c) enrollment + 1 tache_1 → "in_progress", next=2
           (d) enrollment + all 3 Tâches recorded, no assessment → next=None
           (e) enrollment + assessment row → "complete"
  Step 3 — Endpoint contract: GET /api/diagnostic/state — 200 + shape
  Step 4 — Forbid-extra: response schema rejects unexpected fields

Runs offline (no Claude API). Creates a single throwaway user
(``smoke@p221.local``); cleans up at the end.

Run: python -m scripts.smoke_p221
"""
from __future__ import annotations

import sys

from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import text

from app.database import SessionLocal
from app.models.models import (
    Recording,
    User,
    UserLevelAssessment,
    UserPathEnrollment,
)
from app.schemas.diagnostic import (
    DiagnosticStateResponse,
    TacheCoverage,
)
from app.schemas.level import AssignedBlock
from app.services.auth import create_access_token, hash_password
from app.services.diagnostic_state import get_diagnostic_state


SMOKE_EMAIL = "smoke@p221.local"

errors: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    extra = f" -- {detail}" if detail else ""
    print(f"  [{status}] {name}{extra}")
    if not ok:
        errors.append(name)


# ── Step 1: schema imports ─────────────────────────────────────


def step_1_schema() -> None:
    print("\nStep 1: schemas import + AssignedBlock has new fields")
    # AssignedBlock — coverage was already there; n_clusters_evaluated is
    # P-221; total_clusters_in_path is P-201.x (2026-05-03).
    fields = AssignedBlock.model_fields
    check("AssignedBlock has coverage", "coverage" in fields)
    check("AssignedBlock has n_clusters_evaluated", "n_clusters_evaluated" in fields)
    check("AssignedBlock has total_clusters_in_path", "total_clusters_in_path" in fields)
    check("AssignedBlock has computed_at", "computed_at" in fields)

    # DiagnosticStateResponse shape
    dfields = DiagnosticStateResponse.model_fields
    expected = {
        "stage", "recordings_done", "tache_coverage",
        "next_recommended_tache", "latest_assessment_id",
    }
    check("DiagnosticStateResponse has 5 expected fields",
          expected.issubset(set(dfields.keys())),
          str(set(dfields.keys()) - expected))

    # TacheCoverage shape
    tfields = TacheCoverage.model_fields
    check("TacheCoverage has tache_1/2/3",
          {"tache_1", "tache_2", "tache_3"} == set(tfields.keys()))


# ── Helper: clean slate ────────────────────────────────────────


def _wipe_user_state(db, user_id: int) -> None:
    db.query(UserLevelAssessment).filter_by(user_id=user_id).delete()
    db.query(UserPathEnrollment).filter_by(user_id=user_id).delete()
    db.query(Recording).filter_by(user_id=user_id).delete()
    db.commit()


def _ensure_user(db) -> User:
    u = db.query(User).filter_by(email=SMOKE_EMAIL).first()
    if u is None:
        u = User(
            email=SMOKE_EMAIL,
            hashed_password=hash_password("smoke"),
            full_name="P-221 Smoke",
        )
        db.add(u)
        db.commit()
        db.refresh(u)
    return u


def _seed_enrollment(db, user_id: int) -> None:
    path_row = db.execute(text("SELECT id FROM paths WHERE slug='b1_to_b2'")).first()
    if path_row is None:
        return
    db.add(UserPathEnrollment(
        user_id=user_id,
        path_id=path_row[0],
        enrolled_at_level="b1",
        enrolled_at_confidence="medium",
        is_active=True,
    ))
    db.commit()


def _seed_recording(db, user_id: int, tache_mode: str) -> None:
    db.add(Recording(
        user_id=user_id,
        audio_path=f"smoke/p221_{tache_mode}.wav",
        target_level="B1",
        tache_mode=tache_mode,
    ))
    db.commit()


def _seed_assessment(db, user_id: int) -> int:
    row = UserLevelAssessment(
        user_id=user_id,
        assigned_level="B1_emerging",
        assigned_confidence="low",
        coverage=0.5,
        top_bucket_share=0.6,
        confidence_score=0.3,
        n_clusters_evaluated=6,
        n_clusters_clean=3,
        n_clusters_wobble=2,
        n_clusters_fail=1,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row.id


# ── Step 2: service state machine ──────────────────────────────


def step_2_state_machine() -> None:
    print("\nStep 2: get_diagnostic_state — 5 transition cases")
    db = SessionLocal()
    try:
        u = _ensure_user(db)
        _wipe_user_state(db, u.id)

        # (a) no enrollment → no_path
        s = get_diagnostic_state(db, u)
        check("(a) no enrollment → stage=no_path", s["stage"] == "no_path", s["stage"])
        check("(a) recordings_done=0", s["recordings_done"] == 0)
        check("(a) all coverage False",
              s["tache_coverage"] == {"tache_1": False, "tache_2": False, "tache_3": False})
        check("(a) next_recommended_tache None",
              s["next_recommended_tache"] is None)
        check("(a) latest_assessment_id None",
              s["latest_assessment_id"] is None)

        # (b) enrollment + 0 recordings → in_progress, next=1
        _seed_enrollment(db, u.id)
        s = get_diagnostic_state(db, u)
        check("(b) enrollment, no recordings → in_progress",
              s["stage"] == "in_progress", s["stage"])
        check("(b) recordings_done=0", s["recordings_done"] == 0)
        check("(b) next_recommended_tache=1", s["next_recommended_tache"] == 1,
              str(s["next_recommended_tache"]))

        # (c) enrollment + 1 tache_1 → in_progress, T1=true, next=2
        _seed_recording(db, u.id, "tache_1")
        s = get_diagnostic_state(db, u)
        check("(c) recordings_done=1", s["recordings_done"] == 1)
        check("(c) tache_1=True", s["tache_coverage"]["tache_1"] is True)
        check("(c) tache_2=False", s["tache_coverage"]["tache_2"] is False)
        check("(c) next_recommended_tache=2",
              s["next_recommended_tache"] == 2, str(s["next_recommended_tache"]))

        # (d) all 3 Tâches recorded, no assessment yet → in_progress, next=None
        _seed_recording(db, u.id, "tache_2")
        _seed_recording(db, u.id, "tache_3")
        s = get_diagnostic_state(db, u)
        check("(d) recordings_done=3", s["recordings_done"] == 3)
        check("(d) all coverage True",
              all(s["tache_coverage"].values()), str(s["tache_coverage"]))
        check("(d) next_recommended_tache None",
              s["next_recommended_tache"] is None)
        check("(d) stage still in_progress (no assessment)",
              s["stage"] == "in_progress", s["stage"])

        # (e) assessment row exists → complete
        assess_id = _seed_assessment(db, u.id)
        s = get_diagnostic_state(db, u)
        check("(e) stage=complete", s["stage"] == "complete", s["stage"])
        check("(e) latest_assessment_id matches",
              s["latest_assessment_id"] == assess_id,
              f"{s['latest_assessment_id']} vs {assess_id}")
    finally:
        db.close()


# ── Step 3: endpoint contract ──────────────────────────────────


def step_3_endpoint() -> None:
    print("\nStep 3: GET /api/diagnostic/state — endpoint contract")
    from main import app
    client = TestClient(app)

    db = SessionLocal()
    try:
        u = _ensure_user(db)
        # State carried over from step 2 (e): enrollment + 3 recordings + assessment
        # → expect stage=complete in the response.
        token = create_access_token({"sub": u.email})
    finally:
        db.close()
    auth = {"Authorization": f"Bearer {token}"}

    r = client.get("/api/diagnostic/state", headers=auth)
    check("200 OK", r.status_code == 200, str(r.status_code))
    body = r.json()
    check("stage=complete", body.get("stage") == "complete", str(body.get("stage")))
    check("recordings_done=3", body.get("recordings_done") == 3,
          str(body.get("recordings_done")))
    check("tache_coverage all True",
          body.get("tache_coverage") == {"tache_1": True, "tache_2": True, "tache_3": True},
          str(body.get("tache_coverage")))
    check("next_recommended_tache null", body.get("next_recommended_tache") is None)
    check("latest_assessment_id is int", isinstance(body.get("latest_assessment_id"), int))

    # Unauthenticated → 401 (auth dependency must run before handler)
    r2 = client.get("/api/diagnostic/state")
    check("unauth → 401", r2.status_code == 401, str(r2.status_code))


# ── Step 4: extra="forbid" behavior ────────────────────────────


def step_4_forbid_extra() -> None:
    print("\nStep 4: extra='forbid' enforcement on response schemas")
    base = {
        "stage": "in_progress",
        "recordings_done": 0,
        "tache_coverage": {"tache_1": False, "tache_2": False, "tache_3": False},
        "next_recommended_tache": None,
        "latest_assessment_id": None,
    }
    # Valid input parses
    try:
        DiagnosticStateResponse(**base)
        check("valid input parses", True)
    except ValidationError as e:
        check("valid input parses", False, str(e))

    # Extra field → ValidationError
    try:
        DiagnosticStateResponse(**base, surprise="bad")
        check("extra field rejected", False, "no ValidationError raised")
    except ValidationError:
        check("extra field rejected", True)

    # Bad stage value
    try:
        DiagnosticStateResponse(**{**base, "stage": "lol"})
        check("invalid stage rejected", False, "no ValidationError raised")
    except ValidationError:
        check("invalid stage rejected", True)

    # next_recommended_tache outside 1..3
    try:
        DiagnosticStateResponse(**{**base, "next_recommended_tache": 4})
        check("next_recommended_tache=4 rejected", False, "no ValidationError")
    except ValidationError:
        check("next_recommended_tache=4 rejected", True)


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
        step_2_state_machine()
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
