"""Smoke test for V-016a — async writing-job pattern.

Coverage (per the 2026-05-07 plan-first lock-in):
  Step 1 — Schema: writing_submission_jobs columns + CHECK constraint
  Step 2 — POST /api/writing/submit: 202 + job_id + status='pending'
           + DB row created with correct shape
  Step 3 — Background runner lifecycle (3 cases via direct call,
           bypassing TestClient since asyncio.create_task lifecycle
           in test context is fragile):
           (a) happy path  → pending→running→completed, result_json
                              populated, submission row created
           (b) Claude error → pending→running→failed, error_message
                              populated, submission_id stays null
           (c) prompt missing → pending→failed (skips running)
  Step 4 — GET /api/writing/jobs/{id}: 200 + 401 + 404 + 403 cross-user
  Step 5 — Pydantic extra='forbid' on response schemas

Runs offline (no Claude API). Mocks analyze_writing for steps 3a/3b
to avoid real API spend + timing.

Run: python -m scripts.smoke_v016a
"""
from __future__ import annotations

import asyncio
import datetime
import json
import sys
import uuid
from unittest.mock import patch, AsyncMock

from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import text

from app.database import SessionLocal
from app.models.models import User
from app.models.writing import (
    WritingPrompt, WritingSubmission, WritingSubmissionJob,
)
from app.schemas.writing_jobs import (
    WritingJobResponse, WritingSubmitResponse,
)
from app.services.auth import create_access_token, hash_password
from app.services.writing_analysis import COUCHE_ORDER
from app.services.writing_jobs import run_writing_analysis_job


SMOKE_EMAIL = "smoke@v016a.local"
SMOKE_OTHER_EMAIL = "other@v016a.local"

errors: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    extra = f" -- {detail}" if detail else ""
    print(f"  [{status}] {name}{extra}")
    if not ok:
        errors.append(name)


# ── Helpers ────────────────────────────────────────────────────


def _ensure_user(db, email: str) -> User:
    u = db.query(User).filter_by(email=email).first()
    if u is None:
        u = User(
            email=email,
            hashed_password=hash_password("smoke"),
            full_name="V-016a Smoke",
        )
        db.add(u)
        db.commit()
        db.refresh(u)
    return u


def _ensure_prompt(db) -> WritingPrompt:
    p = (
        db.query(WritingPrompt)
        .filter(WritingPrompt.tache_level == 1)
        .first()
    )
    if p is None:
        raise RuntimeError(
            "smoke_v016a: no Tâche 1 writing prompt — run "
            "`python -m scripts.seed_writing_prompts` first."
        )
    return p


def _wipe_jobs(db, user_id: int) -> None:
    # Order matters: delete jobs first (FK to submissions).
    db.query(WritingSubmissionJob).filter_by(user_id=user_id).delete()
    db.query(WritingSubmission).filter_by(user_id=user_id).delete()
    db.commit()


# ── Step 1 — Schema ────────────────────────────────────────────


def step_1_schema() -> None:
    print("\nStep 1: writing_submission_jobs schema")
    with SessionLocal() as db:
        cols = {
            r[0]
            for r in db.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='writing_submission_jobs'"
            )).fetchall()
        }
    expected = {
        "id", "user_id", "submission_id", "status",
        "created_at", "completed_at", "result_json", "error_message",
    }
    check("8 expected columns present",
          expected.issubset(cols),
          f"missing: {expected - cols}" if expected - cols else "")
    with SessionLocal() as db:
        constraints = {
            r[0]
            for r in db.execute(text(
                "SELECT conname FROM pg_constraint "
                "WHERE conname LIKE 'ck_writing_submission_jobs%' "
                "OR conname = 'ix_writing_submission_jobs_user_created'"
            )).fetchall()
        }
    check("CHECK constraint on status present",
          "ck_writing_submission_jobs_status" in constraints)


# ── Step 2 — POST /api/writing/submit ──────────────────────────


def step_2_post_contract() -> None:
    print("\nStep 2: POST /api/writing/submit returns 202 + job row created")
    from main import app
    client = TestClient(app)

    db = SessionLocal()
    try:
        u = _ensure_user(db, SMOKE_EMAIL)
        _wipe_jobs(db, u.id)
        prompt = _ensure_prompt(db)
        token = create_access_token({"sub": u.email})
    finally:
        db.close()

    # Mock the runner so the background task is a no-op (else it
    # would race with the assertions below).
    with patch(
        "app.routers.writing.run_writing_analysis_job",
        new=AsyncMock(return_value=None),
    ):
        r = client.post(
            "/api/writing/submit",
            json={"prompt_id": prompt.id, "student_text": "test sample"},
            headers={"Authorization": f"Bearer {token}"},
        )

    check("POST returns 202", r.status_code == 202, str(r.status_code))
    body = r.json()
    check("response has job_id (uuid-shape)",
          isinstance(body.get("job_id"), str) and len(body["job_id"]) == 36,
          str(body.get("job_id")))
    check("response.status == 'pending'",
          body.get("status") == "pending", str(body.get("status")))

    # Verify the job row exists with the right shape
    db = SessionLocal()
    try:
        job = (
            db.query(WritingSubmissionJob)
            .filter(WritingSubmissionJob.id == body["job_id"])
            .first()
        )
        check("job row exists in DB", job is not None)
        if job:
            check("job.status='pending'", job.status == "pending")
            check("job.user_id matches auth user", job.user_id == u.id)
            check("job.submission_id is None", job.submission_id is None)
            check("job.result_json is None", job.result_json is None)
            check("job.error_message is None", job.error_message is None)
    finally:
        db.close()


# ── Step 3 — Background runner lifecycle ───────────────────────


_FAKE_FEEDBACK = {
    "overall_score": 14.0,
    "word_count": 2,
    "summary": "smoke test feedback",
    "errors": [],
    "strengths": ["smoke test"],
    "next_steps": [],
    # V-016a 2026-05-12 — 5-couche surface. Distinct scores per couche so
    # Step 6 can verify ordering by checking the score round-trips at the
    # right index.
    "methode_en_couches": {
        "le_fond":              {"score": 11, "examiner_remark_fr": "smoke", "teacher_coaching": {}},
        "les_moules_des_idees": {"score": 12, "examiner_remark_fr": "smoke", "teacher_coaching": {}},
        "les_moules":           {"score": 13, "examiner_remark_fr": "smoke", "teacher_coaching": {}},
        "les_reflexes_anglais": {"score": 14, "examiner_remark_fr": "smoke", "teacher_coaching": {}},
        "la_voix":              {"score": 15, "examiner_remark_fr": "smoke", "teacher_coaching": {}},
    },
}


def _make_pending_job(db, user_id: int) -> str:
    job_id = str(uuid.uuid4())
    db.add(WritingSubmissionJob(
        id=job_id, user_id=user_id, status="pending",
    ))
    db.commit()
    return job_id


def step_3_runner_lifecycle() -> None:
    print("\nStep 3: run_writing_analysis_job lifecycle")

    # Capture primitive IDs before any session closes — ORM objects
    # detach across session boundaries and lazy-loads then raise.
    db = SessionLocal()
    try:
        u = _ensure_user(db, SMOKE_EMAIL)
        _wipe_jobs(db, u.id)
        prompt = _ensure_prompt(db)
        user_id = u.id
        prompt_id = prompt.id
    finally:
        db.close()

    # 3a — happy path: analyze_writing returns canned feedback
    db = SessionLocal()
    try:
        job_id = _make_pending_job(db, user_id)
    finally:
        db.close()
    with patch(
        "app.services.writing_jobs.analyze_writing",
        new=AsyncMock(return_value=_FAKE_FEEDBACK),
    ):
        asyncio.run(run_writing_analysis_job(
            job_id=job_id,
            user_id=user_id,
            prompt_id=prompt_id,
            student_text="test sample",
            time_taken_seconds=42,
            ui_language="en",
            exam_profile="tcf_canada",
        ))
    db = SessionLocal()
    try:
        job = db.query(WritingSubmissionJob).filter_by(id=job_id).first()
        check("(a) status='completed'", job.status == "completed")
        check("(a) submission_id populated",
              job.submission_id is not None, str(job.submission_id))
        check("(a) result_json populated",
              job.result_json is not None
              and "overall_score" in job.result_json)
        check("(a) completed_at set", job.completed_at is not None)
        check("(a) error_message stays null",
              job.error_message is None)
        # WritingSubmission row was created
        sub = db.query(WritingSubmission).filter_by(id=job.submission_id).first()
        check("(a) WritingSubmission row created", sub is not None)
        check("(a) submission.time_taken_seconds passed through",
              sub.time_taken_seconds == 42)
    finally:
        db.close()

    # 3b — failure path: analyze_writing raises
    db = SessionLocal()
    try:
        job_id = _make_pending_job(db, user_id)
    finally:
        db.close()
    with patch(
        "app.services.writing_jobs.analyze_writing",
        new=AsyncMock(side_effect=RuntimeError("Claude API 429")),
    ):
        asyncio.run(run_writing_analysis_job(
            job_id=job_id,
            user_id=user_id,
            prompt_id=prompt_id,
            student_text="test sample",
            time_taken_seconds=0,
            ui_language="en",
            exam_profile="tcf_canada",
        ))
    db = SessionLocal()
    try:
        job = db.query(WritingSubmissionJob).filter_by(id=job_id).first()
        check("(b) status='failed'", job.status == "failed",
              str(job.status))
        check("(b) error_message populated",
              job.error_message is not None
              and "RuntimeError" in job.error_message)
        check("(b) submission_id stays null",
              job.submission_id is None)
        check("(b) completed_at set", job.completed_at is not None)
    finally:
        db.close()

    # 3c — prompt-missing path: pending → failed without running Claude
    db = SessionLocal()
    try:
        job_id = _make_pending_job(db, user_id)
    finally:
        db.close()
    with patch(
        "app.services.writing_jobs.analyze_writing",
        new=AsyncMock(side_effect=AssertionError("should not be called")),
    ):
        asyncio.run(run_writing_analysis_job(
            job_id=job_id,
            user_id=user_id,
            prompt_id=999_999_999,   # non-existent
            student_text="test sample",
            time_taken_seconds=0,
            ui_language="en",
            exam_profile="tcf_canada",
        ))
    db = SessionLocal()
    try:
        job = db.query(WritingSubmissionJob).filter_by(id=job_id).first()
        check("(c) prompt-missing → status='failed'",
              job.status == "failed", str(job.status))
        check("(c) error_message='Prompt not found'",
              job.error_message == "Prompt not found",
              str(job.error_message))
    finally:
        db.close()


# ── Step 4 — GET /api/writing/jobs/{id} contract ───────────────


def step_4_get_contract() -> None:
    print("\nStep 4: GET /api/writing/jobs/{job_id} — 200 / 401 / 403 / 404")
    from main import app
    client = TestClient(app)

    db = SessionLocal()
    try:
        u = _ensure_user(db, SMOKE_EMAIL)
        other = _ensure_user(db, SMOKE_OTHER_EMAIL)
        _wipe_jobs(db, u.id)
        _wipe_jobs(db, other.id)
        # Create a completed job for u
        job_id = str(uuid.uuid4())
        db.add(WritingSubmissionJob(
            id=job_id,
            user_id=u.id,
            status="completed",
            result_json='{"foo": "bar"}',
            completed_at=datetime.datetime.utcnow(),
        ))
        db.commit()
        token_u = create_access_token({"sub": u.email})
        token_other = create_access_token({"sub": other.email})
    finally:
        db.close()

    # 200 happy path
    r = client.get(
        f"/api/writing/jobs/{job_id}",
        headers={"Authorization": f"Bearer {token_u}"},
    )
    check("200 happy path", r.status_code == 200, str(r.status_code))
    body = r.json()
    check("body.job_id matches", body.get("job_id") == job_id)
    check("body.status='completed'", body.get("status") == "completed")
    check("body.result deserialized to dict",
          isinstance(body.get("result"), dict)
          and body["result"].get("foo") == "bar")
    check("body.error is null", body.get("error") is None)
    check("body.created_at present", body.get("created_at") is not None)
    check("body.completed_at present",
          body.get("completed_at") is not None)

    # 404 unknown id
    r = client.get(
        f"/api/writing/jobs/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token_u}"},
    )
    check("404 unknown job", r.status_code == 404, str(r.status_code))

    # 401 unauth
    r = client.get(f"/api/writing/jobs/{job_id}")
    check("401 no auth", r.status_code == 401, str(r.status_code))

    # 403 cross-user
    r = client.get(
        f"/api/writing/jobs/{job_id}",
        headers={"Authorization": f"Bearer {token_other}"},
    )
    check("403 cross-user (job belongs to a different user)",
          r.status_code == 403, str(r.status_code))


# ── Step 5 — Pydantic extra='forbid' ───────────────────────────


def step_5_forbid() -> None:
    print("\nStep 5: extra='forbid' on response schemas")

    # WritingSubmitResponse rejects extra fields + bad status
    try:
        WritingSubmitResponse(job_id="x" * 36, status="pending")
        check("WritingSubmitResponse valid input parses", True)
    except ValidationError as e:
        check("WritingSubmitResponse valid input parses", False, str(e)[:120])

    try:
        WritingSubmitResponse(
            job_id="x" * 36, status="pending", surprise="bad",
        )
        check("WritingSubmitResponse extra rejected", False, "no error")
    except ValidationError:
        check("WritingSubmitResponse extra rejected", True)

    try:
        WritingSubmitResponse(job_id="x" * 36, status="lol")
        check("WritingSubmitResponse invalid status rejected",
              False, "no error")
    except ValidationError:
        check("WritingSubmitResponse invalid status rejected", True)

    # WritingJobResponse round-trip
    try:
        WritingJobResponse(
            job_id="x" * 36,
            status="completed",
            result={"foo": "bar"},
            error=None,
            created_at=datetime.datetime.utcnow(),
            completed_at=datetime.datetime.utcnow(),
        )
        check("WritingJobResponse valid input parses", True)
    except ValidationError as e:
        check("WritingJobResponse valid input parses", False, str(e)[:120])

    try:
        WritingJobResponse(
            job_id="x" * 36,
            status="invalid_status",
            created_at=datetime.datetime.utcnow(),
        )
        check("WritingJobResponse invalid status rejected",
              False, "no error")
    except ValidationError:
        check("WritingJobResponse invalid status rejected", True)


# ── Step 6 — 5-couche surface in result_json (V-016a 2026-05-12) ────


def step_6_five_couche_surface() -> None:
    print("\nStep 6: result_json carries the 5-couche surface")

    db = SessionLocal()
    try:
        u = _ensure_user(db, SMOKE_EMAIL)
        _wipe_jobs(db, u.id)
        prompt = _ensure_prompt(db)
        user_id = u.id
        prompt_id = prompt.id
        job_id = _make_pending_job(db, user_id)
    finally:
        db.close()

    with patch(
        "app.services.writing_jobs.analyze_writing",
        new=AsyncMock(return_value=_FAKE_FEEDBACK),
    ):
        asyncio.run(run_writing_analysis_job(
            job_id=job_id,
            user_id=user_id,
            prompt_id=prompt_id,
            student_text="test sample for couche surface",
            time_taken_seconds=33,
            ui_language="en",
            exam_profile="tcf_canada",
        ))

    db = SessionLocal()
    try:
        job = db.query(WritingSubmissionJob).filter_by(id=job_id).first()
        check("job completed", job and job.status == "completed")
        if not job or not job.result_json:
            check("result_json present", False)
            return
        result = json.loads(job.result_json)
    finally:
        db.close()

    # Top-level couches array
    couches = result.get("couches")
    check("result.couches is a list",
          isinstance(couches, list), str(type(couches).__name__))
    check("result.couches has 5 rows",
          isinstance(couches, list) and len(couches) == 5,
          str(len(couches)) if isinstance(couches, list) else "n/a")
    if not isinstance(couches, list) or len(couches) != 5:
        return

    # Order check
    keys = [c.get("key") for c in couches]
    check("couches order matches COUCHE_ORDER",
          tuple(keys) == COUCHE_ORDER, str(keys))

    # Each row has display labels + score
    shape_ok = all(
        isinstance(c.get("display_label_en"), str)
        and isinstance(c.get("display_label_fr"), str)
        and isinstance(c.get("score"), (int, float))
        for c in couches
    )
    check("each row has display_label_en/fr + numeric score", shape_ok)

    # La Voix row sanity (Voice / Voix)
    la_voix = couches[4]
    check("la_voix.display_label_en == 'Voice'",
          la_voix.get("display_label_en") == "Voice",
          str(la_voix.get("display_label_en")))
    check("la_voix.display_label_fr == 'Voix'",
          la_voix.get("display_label_fr") == "Voix",
          str(la_voix.get("display_label_fr")))

    # Score round-trip — _FAKE_FEEDBACK uses 11/12/13/14/15 in canonical order
    expected_scores = [11.0, 12.0, 13.0, 14.0, 15.0]
    actual_scores = [float(c.get("score", 0)) for c in couches]
    check("scores round-trip in canonical order",
          actual_scores == expected_scores,
          f"actual={actual_scores}")

    # Feedback's methode_en_couches still embedded (FE may read either)
    feedback = result.get("feedback") or {}
    mec = feedback.get("methode_en_couches") if isinstance(feedback, dict) else None
    check("feedback.methode_en_couches preserved",
          isinstance(mec, dict) and "la_voix" in mec,
          str(list(mec.keys())) if isinstance(mec, dict) else "n/a")


# ── Cleanup ────────────────────────────────────────────────────


def cleanup() -> None:
    print("\nCleanup")
    db = SessionLocal()
    try:
        for email in (SMOKE_EMAIL, SMOKE_OTHER_EMAIL):
            u = db.query(User).filter_by(email=email).first()
            if u:
                _wipe_jobs(db, u.id)
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
        step_2_post_contract()
        step_3_runner_lifecycle()
        step_4_get_contract()
        step_5_forbid()
        step_6_five_couche_surface()
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
