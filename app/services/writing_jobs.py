"""V-016a — async writing-analysis job runner.

`run_writing_analysis_job` is fired via `asyncio.create_task` from the
POST /api/writing/submit handler. It:

  1. Opens its OWN DB session (decoupled from the request session
     which closes when the handler returns).
  2. UPDATEs the job row through pending → running.
  3. Calls `analyze_writing` (which has its own demo-mode fallback
     when ANTHROPIC_API_KEY is unset).
  4. On success: INSERTs WritingSubmission row + UPDATEs job to
     completed with result_json.
  5. On failure: UPDATEs job to failed with sanitized error_message.

Failure isolation: any exception during the run is caught and
surfaced via job.error_message (truncated to 500 chars). The task
NEVER raises out of the runner — there's no caller awaiting it.

Container-restart caveat (per Q2 lock-in 2026-05-07): asyncio.create_task
is bound to the FastAPI/uvicorn worker process. A restart mid-job
loses the in-flight task; the row stays in pending or running state
forever. Acceptable for soft-beta volume; users can resubmit. Upgrade
to Celery + Redis as P-260c when daily volume justifies (>50/day or
real lost-task complaints).
"""
from __future__ import annotations

import datetime
import json
import logging

from app.database import SessionLocal
# Models.User import side-effect — registers User in declarative base
# so WritingSubmission's user relationship resolves at mapper-config.
from app.models.models import User as _User  # noqa: F401
from app.models.writing import (
    WritingPrompt,
    WritingSubmission,
    WritingSubmissionJob,
)
from app.services.exam_profiles import get_profile
from app.services.writing_analysis import analyze_writing


logger = logging.getLogger(__name__)


_ERROR_MESSAGE_MAX = 500


def _truncate_error(msg: str) -> str:
    if len(msg) <= _ERROR_MESSAGE_MAX:
        return msg
    return msg[:_ERROR_MESSAGE_MAX - 3] + "..."


async def run_writing_analysis_job(
    *,
    job_id: str,
    user_id: int,
    prompt_id: int,
    student_text: str,
    time_taken_seconds: int,
    ui_language: str,
    exam_profile: str,
) -> None:
    """Background runner. Self-contained — opens its own DB session,
    handles all errors, NEVER raises.

    Caller pattern (request handler):
        asyncio.create_task(run_writing_analysis_job(...))

    Args are primitive values; no shared ORM objects with the request
    session.
    """
    db = SessionLocal()
    try:
        job = (
            db.query(WritingSubmissionJob)
            .filter(WritingSubmissionJob.id == job_id)
            .first()
        )
        if job is None:
            logger.error(
                "V-016a job runner: job_id=%s not found at start; "
                "aborting silently",
                job_id,
            )
            return

        # pending → running
        job.status = "running"
        db.commit()

        # Resolve prompt
        prompt = (
            db.query(WritingPrompt)
            .filter(WritingPrompt.id == prompt_id)
            .first()
        )
        if prompt is None:
            job.status = "failed"
            job.error_message = "Prompt not found"
            job.completed_at = datetime.datetime.utcnow()
            db.commit()
            logger.warning(
                "V-016a job runner: job_id=%s prompt_id=%s missing",
                job_id, prompt_id,
            )
            return

        # Run analysis (analyze_writing handles ANTHROPIC_API_KEY-unset
        # via _demo_writing_feedback fallback). Catches any exception
        # to flip job.status=failed cleanly.
        try:
            feedback = await analyze_writing(
                student_text=student_text,
                prompt_text=prompt.prompt_text,
                prompt_type=prompt.prompt_type,
                target_level=prompt.level,
                ui_language=ui_language,
                exam_profile=get_profile(exam_profile),
            )
        except Exception as e:
            job.status = "failed"
            job.error_message = _truncate_error(
                f"{type(e).__name__}: {e}"
            )
            job.completed_at = datetime.datetime.utcnow()
            db.commit()
            logger.exception(
                "V-016a job runner: job_id=%s analyze_writing failed",
                job_id,
            )
            return

        # Persist submission row (mirrors legacy sync handler)
        word_count = len(student_text.split())
        submission = WritingSubmission(
            user_id=user_id,
            prompt_id=prompt_id,
            student_text=student_text,
            feedback_json=json.dumps(feedback, ensure_ascii=False),
            word_count=word_count,
            overall_score=feedback.get("overall_score", 0)
                if isinstance(feedback, dict) else 0,
            time_taken_seconds=time_taken_seconds,
        )
        db.add(submission)
        db.commit()
        db.refresh(submission)

        # Build result_json mirroring legacy sync POST /submit response
        # so the FE polling consumer renders identically.
        result = {
            "id": submission.id,
            "word_count": word_count,
            "time_taken_seconds": time_taken_seconds,
            "feedback": feedback,
            "submitted_at": (
                submission.submitted_at.isoformat()
                if submission.submitted_at else ""
            ),
        }

        job.status = "completed"
        job.submission_id = submission.id
        job.result_json = json.dumps(result, ensure_ascii=False)
        job.completed_at = datetime.datetime.utcnow()
        db.commit()
        logger.info(
            "V-016a job runner: job_id=%s completed submission_id=%s "
            "word_count=%d",
            job_id, submission.id, word_count,
        )
    except Exception:
        # Defensive — catch-all so the task never raises out.
        logger.exception(
            "V-016a job runner: job_id=%s unexpected failure", job_id
        )
        try:
            job = (
                db.query(WritingSubmissionJob)
                .filter(WritingSubmissionJob.id == job_id)
                .first()
            )
            if job is not None and job.status not in ("completed", "failed"):
                job.status = "failed"
                job.error_message = "Unexpected runner failure"
                job.completed_at = datetime.datetime.utcnow()
                db.commit()
        except Exception:
            logger.exception(
                "V-016a job runner: job_id=%s could not record final "
                "failure state", job_id,
            )
    finally:
        db.close()
