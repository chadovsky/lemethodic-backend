import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status as http_status
from pydantic import BaseModel

logger = logging.getLogger(__name__)
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import User
from app.models.writing import (
    WritingPrompt, WritingSubmission, WritingSubmissionJob,
)
from app.schemas.writing_jobs import (
    WritingJobResponse,
    WritingSubmitResponse,
)
from app.services.auth import get_current_user
from app.services.writing_analysis import analyze_writing
from app.services.exam_profiles import get_profile
from app.services.scoring_maps import cefr_from_score, clb_from_cefr
from app.services.writing_jobs import run_writing_analysis_job

router = APIRouter(prefix="/api/writing", tags=["writing"])


# ── Request schemas ────────────────────────────────────────────────

class SubmitWritingRequest(BaseModel):
    prompt_id: int
    student_text: str
    time_taken_seconds: int = 0
    ui_language: str = "en"
    exam_profile: str = "tcf_canada"


# ── Endpoints ──────────────────────────────────────────────────────

@router.get("/prompts")
def get_prompts(
    level: str = None,
    tache_level: int = None,
    topic_tag: str = None,
    db: Session = Depends(get_db),
):
    """Get writing prompts, optionally filtered by level, tache_level,
    or topic_tag. Response carries both legacy fields (level, theme,
    prompt_text, prompt_type, time_limit_minutes — for backward-compat
    with existing FE consumers) and the F-224 v1 pack canonical fields
    (tache_level, title_fr, prompt_fr, prompt_en, topic_tag).

    The new fields are additive — existing consumers ignore unknown keys.
    """
    query = db.query(WritingPrompt).filter(WritingPrompt.is_active == 1)
    if level:
        query = query.filter(WritingPrompt.level == level.upper())
    if tache_level:
        query = query.filter(WritingPrompt.tache_level == tache_level)
    if topic_tag:
        query = query.filter(WritingPrompt.topic_tag == topic_tag)
    prompts = query.order_by(
        WritingPrompt.tache_level, WritingPrompt.level, WritingPrompt.theme
    ).all()
    return [
        {
            # Legacy fields (kept for backward-compat).
            "id": p.id,
            "level": p.level,
            "theme": p.theme,
            "prompt_text": p.prompt_text,
            "prompt_type": p.prompt_type,
            "min_words": p.min_words,
            "max_words": p.max_words,
            "time_limit_minutes": p.time_limit_minutes,
            # F-224 v1 pack canonical fields (additive).
            "tache_level": p.tache_level,
            "title_fr": p.title_fr,
            "prompt_fr": p.prompt_fr,
            "prompt_en": p.prompt_en,
            "topic_tag": p.topic_tag,
        }
        for p in prompts
    ]


@router.post(
    "/submit",
    status_code=http_status.HTTP_202_ACCEPTED,
    response_model=WritingSubmitResponse,
)
async def submit_writing(
    req: SubmitWritingRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WritingSubmitResponse:
    """V-016a — submit writing for async AI analysis.

    Creates a `writing_submission_jobs` row + spawns a background
    asyncio task to run the Claude analysis. Returns 202 with the
    `job_id` immediately. FE polls `GET /api/writing/jobs/{job_id}`
    until status='completed' or 'failed' (poll cadence locked at
    3s, abandon after 5 min).

    Pre-V-016a this was a sync endpoint that returned the full
    analysis after 30-90s of blocking. Cut by infrastructure
    (Cloudflare/DO request_timeout) on prod. The async pattern is
    the structural fix; the .do/app.yaml `request_timeout: 180`
    bump is cosmetic insurance for any sync paths.
    """
    # Validate prompt exists (synchronous — fast)
    prompt = (
        db.query(WritingPrompt)
        .filter(WritingPrompt.id == req.prompt_id)
        .first()
    )
    if not prompt:
        raise HTTPException(404, "Writing prompt not found")

    # Validate text is not empty (synchronous — fast)
    text = req.student_text.strip()
    if not text:
        raise HTTPException(400, "Text cannot be empty")

    # F-044 Spanish fallback: generate content in English until ES is fully
    # supported. UI labels still render in Spanish via frontend i18n.
    effective_ui_language = req.ui_language
    if req.ui_language == "es":
        logger.warning(
            f"Spanish content generation not yet implemented, "
            f"falling back to English for user_id={user.id}"
        )
        effective_ui_language = "en"

    # Insert job row (status=pending) BEFORE spawning the task — task
    # opens its own DB session and reads this row by id.
    job_id = str(uuid.uuid4())
    db.add(WritingSubmissionJob(
        id=job_id,
        user_id=user.id,
        status="pending",
    ))
    db.commit()
    logger.info(
        "V-016a submit JOB_CREATED job_id=%s user_id=%s prompt_id=%s "
        "word_count=%d ui_language=%s",
        job_id, user.id, req.prompt_id, len(text.split()),
        effective_ui_language,
    )

    # Spawn the background task. asyncio.create_task fire-and-forget —
    # task lifecycle is bound to the uvicorn event loop, NOT this
    # request. Container restart loses in-flight tasks (acceptable
    # for soft-beta volume per Q2 lock-in 2026-05-07; user resubmits).
    task = asyncio.create_task(run_writing_analysis_job(
        job_id=job_id,
        user_id=user.id,
        prompt_id=req.prompt_id,
        student_text=text,
        time_taken_seconds=req.time_taken_seconds,
        ui_language=effective_ui_language,
        exam_profile=req.exam_profile,
    ))
    # Capture task identity so log readers can correlate runner
    # entries back to the submit handler. Don't await — fire-and-forget.
    logger.info(
        "V-016a submit TASK_SPAWNED job_id=%s task_name=%s",
        job_id, task.get_name(),
    )

    return WritingSubmitResponse(job_id=job_id, status="pending")


@router.get("/jobs/{job_id}", response_model=WritingJobResponse)
def get_writing_job(
    job_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WritingJobResponse:
    """V-016a — poll a writing-analysis job's state.

    FE consumer polls every 3s (abandon after 5 min). Returns
    current status + result (when completed) or error (when failed).

    Auth: 403 cross-user (matches /history/{user_id} precedent —
    auth-leaks job existence to the owner; non-owners get 403 not
    404).
    """
    job = (
        db.query(WritingSubmissionJob)
        .filter(WritingSubmissionJob.id == job_id)
        .first()
    )
    if job is None:
        raise HTTPException(404, "Job not found")
    if job.user_id != user.id and not user.is_admin:
        raise HTTPException(403, "Not authorized to view this job")

    return WritingJobResponse(
        job_id=job.id,
        status=job.status,
        result=json.loads(job.result_json) if job.result_json else None,
        error=job.error_message,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )


@router.get("/history/{user_id}")
def get_writing_history(
    user_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get writing submission history for a user."""
    # Users can only view their own history (unless admin)
    if user.id != user_id and not user.is_admin:
        raise HTTPException(403, "Not authorized to view this history")

    submissions = (
        db.query(WritingSubmission)
        .filter(WritingSubmission.user_id == user_id)
        .order_by(WritingSubmission.submitted_at.desc())
        .limit(50)
        .all()
    )

    results = []
    for s in submissions:
        prompt = db.query(WritingPrompt).filter(WritingPrompt.id == s.prompt_id).first()
        profile_summary = _writing_profile_summary(s)
        entry = {
            "id": s.id,
            "prompt_text": prompt.prompt_text if prompt else "",
            "prompt_type": prompt.prompt_type if prompt else "",
            "level": prompt.level if prompt else "",
            "theme": prompt.theme if prompt else "",
            "word_count": s.word_count,
            "overall_score": s.overall_score,
            "time_taken_seconds": s.time_taken_seconds,
            "submitted_at": s.submitted_at.isoformat() if s.submitted_at else "",
            "text_preview": (s.student_text or "")[:120],
            "cefr_level": profile_summary["cefr_level"],
            "clb_level": profile_summary["secondary_framework_value"],
        }
        results.append(entry)

    return results


def _writing_profile_summary(sub: WritingSubmission) -> dict:
    """Extract the exam-profile block from a writing submission's feedback_json,
    backfilling CEFR/CLB from overall_score for legacy submissions that predate
    5-criterion scoring.
    """
    try:
        feedback = json.loads(sub.feedback_json) if sub.feedback_json else {}
    except json.JSONDecodeError:
        feedback = {}

    existing = feedback.get("exam_profile") if isinstance(feedback, dict) else None
    if isinstance(existing, dict) and existing.get("cefr_level"):
        return existing

    score = float(sub.overall_score or 0)
    cefr = cefr_from_score(score)
    return {
        "profile_id": "tcf_canada",
        "display_name": "TCF Canada",
        "frameworks_shown": ["raw20", "cefr", "clb"],
        "overall_score": score,
        "cefr_level": cefr,
        "secondary_framework_label": "CLB",
        "secondary_framework_value": clb_from_cefr(cefr),
        "criteria_breakdown": [],
        "legacy": True,
    }


@router.get("/submission/{submission_id}")
def get_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a single writing submission with full feedback."""
    sub = db.query(WritingSubmission).filter(WritingSubmission.id == submission_id).first()
    if not sub:
        raise HTTPException(404, "Submission not found")
    if sub.user_id != user.id and not user.is_admin:
        raise HTTPException(403, "Not authorized")

    prompt = db.query(WritingPrompt).filter(WritingPrompt.id == sub.prompt_id).first()

    feedback = {}
    try:
        feedback = json.loads(sub.feedback_json) if sub.feedback_json else {}
    except json.JSONDecodeError:
        pass

    # Ensure exam_profile block exists, backfilling for legacy submissions.
    if isinstance(feedback, dict) and not feedback.get("exam_profile"):
        feedback["exam_profile"] = _writing_profile_summary(sub)

    return {
        "id": sub.id,
        "prompt_text": prompt.prompt_text if prompt else "",
        "prompt_type": prompt.prompt_type if prompt else "",
        "level": prompt.level if prompt else "",
        "theme": prompt.theme if prompt else "",
        "student_text": sub.student_text,
        "word_count": sub.word_count,
        "overall_score": sub.overall_score,
        "time_taken_seconds": sub.time_taken_seconds,
        "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else "",
        "feedback": feedback,
    }
