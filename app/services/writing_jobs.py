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
import time

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
from app.services.writing_analysis import _extract_couches, analyze_writing


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
    # V-016a diagnostic logging (2026-05-07): structured trace at every
    # state transition + Claude-call duration. Surfaces stalls in the
    # async-job pipeline that the AnalyzingPanel symptoms exposed.
    runner_t0 = time.time()
    word_count_in = len(student_text.split())
    logger.info(
        "V-016a runner ENTRY job_id=%s user_id=%s prompt_id=%s "
        "word_count=%d ui_language=%s exam_profile=%s",
        job_id, user_id, prompt_id, word_count_in,
        ui_language, exam_profile,
    )

    db = SessionLocal()
    try:
        job = (
            db.query(WritingSubmissionJob)
            .filter(WritingSubmissionJob.id == job_id)
            .first()
        )
        if job is None:
            logger.error(
                "V-016a runner ABORT job_id=%s reason=job_row_missing "
                "elapsed_s=%.2f",
                job_id, time.time() - runner_t0,
            )
            return

        # pending → running
        job.status = "running"
        db.commit()
        logger.info(
            "V-016a runner STATUS=running job_id=%s elapsed_s=%.2f",
            job_id, time.time() - runner_t0,
        )

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
                "V-016a runner FAIL job_id=%s reason=prompt_not_found "
                "prompt_id=%s elapsed_s=%.2f",
                job_id, prompt_id, time.time() - runner_t0,
            )
            return

        # Run analysis (analyze_writing handles ANTHROPIC_API_KEY-unset
        # via _demo_writing_feedback fallback). Catches any exception
        # to flip job.status=failed cleanly.
        logger.info(
            "V-016a runner CLAUDE_CALL_START job_id=%s "
            "target_level=%s prompt_type=%s",
            job_id, prompt.level, prompt.prompt_type,
        )
        claude_t0 = time.time()
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
            claude_elapsed = time.time() - claude_t0
            job.status = "failed"
            job.error_message = _truncate_error(
                f"{type(e).__name__}: {e}"
            )
            job.completed_at = datetime.datetime.utcnow()
            db.commit()
            logger.exception(
                "V-016a runner FAIL job_id=%s reason=claude_exception "
                "exception_type=%s claude_elapsed_s=%.2f total_elapsed_s=%.2f",
                job_id, type(e).__name__, claude_elapsed,
                time.time() - runner_t0,
            )
            return

        claude_elapsed = time.time() - claude_t0
        feedback_kind = "dict" if isinstance(feedback, dict) else "str"
        logger.info(
            "V-016a runner CLAUDE_CALL_DONE job_id=%s claude_elapsed_s=%.2f "
            "feedback_kind=%s",
            job_id, claude_elapsed, feedback_kind,
        )

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
        logger.info(
            "V-016a runner SUBMISSION_PERSISTED job_id=%s "
            "submission_id=%s elapsed_s=%.2f",
            job_id, submission.id, time.time() - runner_t0,
        )

        # Build result_json mirroring legacy sync POST /submit response
        # so the FE polling consumer renders identically. V-016a (2026-05-12):
        # added top-level `couches` array (5-couche La Méthode en Couches
        # surface) so the FE polling consumer reads couche scores without
        # descending into feedback.methode_en_couches.
        result = {
            "id": submission.id,
            "word_count": word_count,
            "time_taken_seconds": time_taken_seconds,
            "feedback": feedback,
            "couches": (
                _extract_couches(feedback) if isinstance(feedback, dict) else []
            ),
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
            "V-016a runner COMPLETED job_id=%s submission_id=%s "
            "word_count=%d total_elapsed_s=%.2f",
            job_id, submission.id, word_count,
            time.time() - runner_t0,
        )
    except Exception:
        # Defensive — catch-all so the task never raises out.
        logger.exception(
            "V-016a runner UNEXPECTED_FAILURE job_id=%s elapsed_s=%.2f",
            job_id, time.time() - runner_t0
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
