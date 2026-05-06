import json, logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import User
from app.models.writing import WritingPrompt, WritingSubmission
from app.services.auth import get_current_user
from app.services.writing_analysis import analyze_writing
from app.services.exam_profiles import get_profile
from app.services.scoring_maps import cefr_from_score, clb_from_cefr

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


@router.post("/submit")
async def submit_writing(
    req: SubmitWritingRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Submit writing for AI analysis."""
    # Validate prompt exists
    prompt = db.query(WritingPrompt).filter(WritingPrompt.id == req.prompt_id).first()
    if not prompt:
        raise HTTPException(404, "Writing prompt not found")

    # Validate text is not empty
    text = req.student_text.strip()
    if not text:
        raise HTTPException(400, "Text cannot be empty")

    word_count = len(text.split())

    # F-044 Spanish fallback: generate content in English until ES is fully
    # supported. UI labels still render in Spanish via frontend i18n.
    effective_ui_language = req.ui_language
    if req.ui_language == "es":
        logger.warning(
            f"Spanish content generation not yet implemented, "
            f"falling back to English for user_id={user.id}"
        )
        effective_ui_language = "en"

    # Call Claude for analysis
    try:
        feedback = await analyze_writing(
            student_text=text,
            prompt_text=prompt.prompt_text,
            prompt_type=prompt.prompt_type,
            target_level=prompt.level,
            ui_language=effective_ui_language,
            exam_profile=get_profile(req.exam_profile),
        )
    except Exception as e:
        raise HTTPException(500, f"Analysis failed: {str(e)}")

    # Save submission
    submission = WritingSubmission(
        user_id=user.id,
        prompt_id=req.prompt_id,
        student_text=text,
        feedback_json=json.dumps(feedback, ensure_ascii=False),
        word_count=word_count,
        overall_score=feedback.get("overall_score", 0),
        time_taken_seconds=req.time_taken_seconds,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    return {
        "id": submission.id,
        "word_count": word_count,
        "time_taken_seconds": req.time_taken_seconds,
        "feedback": feedback,
        "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else "",
    }


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
