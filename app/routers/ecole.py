"""F-053 — L'École curriculum endpoints.

Flow the UI expects:
  GET  /api/ecole/lessons                   → all 16 with per-user status
  GET  /api/ecole/lessons/{id}              → unlocked-only content
  POST /api/ecole/lessons/{id}/start        → flip to in_progress
  GET  /api/ecole/lessons/{id}/quiz         → 5 questions (no answers)
  POST /api/ecole/lessons/{id}/quiz/submit  → score + unlock next
  GET  /api/ecole/progress                  → home-card aggregate

Progress rows are created lazily on first read so the 19 pre-existing
users don't need a backfill migration.
"""
from __future__ import annotations

import datetime
import json
import logging
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import (
    EcoleLesson,
    EcoleQuizQuestion,
    User,
    UserEcoleProgress,
)
from app.services.auth import get_current_user
from app.services.ecole_gating import (
    QUIZ_PASS_THRESHOLD,
    ensure_progress_rows,
    is_above_a2,
    lessons_completed,
    lesson_unlocked,
    next_lesson,
    record_quiz_attempt,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ecole", tags=["ecole"])


# ═══════════════════════════════════════════════════════════════
# Serialization helpers
# ═══════════════════════════════════════════════════════════════

def _lesson_row_to_summary(
    lesson: EcoleLesson,
    progress: UserEcoleProgress | None,
    ui_language: str,
) -> dict:
    """Light-weight lesson card (no detailed content body)."""
    title = {
        "fr": lesson.title_fr,
        "en": lesson.title_en,
        "es": lesson.title_es,
    }.get(ui_language) or lesson.title_fr or lesson.code

    short = {
        "fr": lesson.short_description_fr,
        "en": lesson.short_description_en,
        "es": lesson.short_description_es,
    }.get(ui_language) or lesson.short_description_fr or ""

    return {
        "id": lesson.id,
        "lesson_number": lesson.lesson_number,
        "code": lesson.code,
        "title": title,
        "short_description": short,
        "estimated_duration_minutes": lesson.estimated_duration_minutes,
        "prerequisite_lesson_number": lesson.prerequisite_lesson_number,
        # F-087: phase drives the home-tab visual separator between
        # lessons 16 and 17. F-089 will surface subline_en under the
        # title; exposed here today so the field is available on the
        # same response shape that's already cached client-side.
        "phase": lesson.phase or 1,
        "subline_en": lesson.subline_en,
        "status": progress.status if progress else "locked",
        "quiz_attempts": progress.quiz_attempts if progress else 0,
        "quiz_best_score": progress.quiz_best_score if progress else 0,
        "completed_at": progress.completed_at.isoformat() if progress and progress.completed_at else None,
    }


def _lesson_full_detail(lesson: EcoleLesson, ui_language: str) -> dict:
    summary_keys = {
        "fr": (lesson.title_fr, lesson.short_description_fr, lesson.detailed_content_fr),
        "en": (lesson.title_en, lesson.short_description_en, lesson.detailed_content_en),
        "es": (lesson.title_es, lesson.short_description_es, lesson.detailed_content_es),
    }
    title, short, detail = summary_keys.get(ui_language, (None, None, None))
    # Fall back to FR when a translation slot is empty (common for ES
    # detailed_content which is null by design today).
    return {
        "id": lesson.id,
        "lesson_number": lesson.lesson_number,
        "code": lesson.code,
        "title": title or lesson.title_fr or lesson.code,
        "short_description": short or lesson.short_description_fr or "",
        "detailed_content": detail or lesson.detailed_content_fr or "",
        "estimated_duration_minutes": lesson.estimated_duration_minutes,
        "prerequisite_lesson_number": lesson.prerequisite_lesson_number,
        # F-087 — see _lesson_row_to_summary for the same fields.
        "phase": lesson.phase or 1,
        "subline_en": lesson.subline_en,
    }


def _question_public(question: EcoleQuizQuestion, ui_language: str) -> dict:
    """Student-facing shape: omits ``correct_answer`` and
    ``accepted_alternatives`` — only the scorer sees those."""
    q_text = {
        "fr": question.question_fr,
        "en": question.question_en,
        "es": question.question_es,
    }.get(ui_language) or question.question_fr or ""
    try:
        options = json.loads(question.options or "[]")
        if not isinstance(options, list):
            options = []
    except json.JSONDecodeError:
        options = []
    return {
        "id": question.id,
        "question_number": question.question_number,
        "question_type": question.question_type,
        "question": q_text,
        "options": options,
    }


def _question_with_feedback(
    question: EcoleQuizQuestion,
    user_answer: str | None,
    correct: bool,
    ui_language: str,
) -> dict:
    expl = {
        "fr": question.explanation_fr,
        "en": question.explanation_en,
        "es": question.explanation_es,
    }.get(ui_language) or question.explanation_fr or ""
    return {
        "question_number": question.question_number,
        "question_type": question.question_type,
        "user_answer": user_answer or "",
        "correct_answer": question.correct_answer or "",
        "correct": bool(correct),
        "explanation": expl,
    }


# ═══════════════════════════════════════════════════════════════
# Answer scoring
# ═══════════════════════════════════════════════════════════════

_NORM_RE = re.compile(r"[^\w'\-]+", flags=re.UNICODE)


def _normalise(s: str) -> str:
    """Loose normalisation for fill-blank / translate grading: strip
    punctuation + outer whitespace + fold case. Accent handling is
    deliberately NOT done — students should still get marked wrong on
    « français » vs « francais », since accents are grading-relevant."""
    if not s:
        return ""
    return _NORM_RE.sub(" ", s.strip().lower()).strip()


def _score_single_answer(question: EcoleQuizQuestion, user_answer: str) -> bool:
    user_norm = _normalise(user_answer)
    if not user_norm:
        return False
    if question.question_type == "multiple_choice":
        # MC grading is an exact match against the stored correct_answer
        # (we don't normalise option strings — they come from our own
        # seeder and are expected to be one of the listed options).
        return (user_answer or "").strip() == (question.correct_answer or "").strip()
    # Fill-blank / translate: canonical + alternatives, all normalised.
    candidates = [question.correct_answer or ""]
    try:
        alts = json.loads(question.accepted_alternatives or "[]")
        if isinstance(alts, list):
            candidates.extend(str(a) for a in alts)
    except json.JSONDecodeError:
        pass
    return any(_normalise(c) == user_norm for c in candidates if c)


# ═══════════════════════════════════════════════════════════════
# Endpoints
# ═══════════════════════════════════════════════════════════════

@router.get("/lessons")
def list_lessons(
    ui_language: str = "en",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return all 16 lessons with the current user's progress stamp."""
    ensure_progress_rows(user, db)
    rows = (
        db.query(EcoleLesson)
        .filter(EcoleLesson.is_active == True)  # noqa: E712
        .order_by(EcoleLesson.lesson_number)
        .all()
    )
    progress_map = {
        p.lesson_id: p
        for p in db.query(UserEcoleProgress)
        .filter(UserEcoleProgress.user_id == user.id)
        .all()
    }
    return {
        "lessons": [
            _lesson_row_to_summary(lesson, progress_map.get(lesson.id), ui_language)
            for lesson in rows
        ],
        "above_a2": is_above_a2(user, db),
    }


@router.get("/progress")
def get_progress(
    ui_language: str = "en",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Home-card aggregate. Never 404s — bootstraps progress rows on
    first access so new/legacy users get a valid shape back."""
    ensure_progress_rows(user, db)
    completed = lessons_completed(user, db)
    nl = next_lesson(user, db)
    nl_payload: dict | None = None
    if nl is not None:
        title = {
            "fr": nl.title_fr, "en": nl.title_en, "es": nl.title_es,
        }.get(ui_language) or nl.title_fr or nl.code
        nl_payload = {
            "id": nl.id,
            "lesson_number": nl.lesson_number,
            "code": nl.code,
            "title": title,
        }
    return {
        "lessons_completed": completed,
        "total": 16,
        "above_a2": is_above_a2(user, db),
        "next_lesson": nl_payload,
        "quiz_pass_threshold": QUIZ_PASS_THRESHOLD,
    }


def _require_lesson_and_access(
    lesson_id: int, user: User, db: Session
) -> EcoleLesson:
    ensure_progress_rows(user, db)
    lesson = db.query(EcoleLesson).filter(EcoleLesson.id == lesson_id).first()
    if not lesson or not lesson.is_active:
        raise HTTPException(404, "Lesson not found")
    if not lesson_unlocked(user, lesson_id, db):
        raise HTTPException(403, "Lesson locked. Complete the previous one first.")
    return lesson


@router.get("/lessons/{lesson_id}")
def get_lesson(
    lesson_id: int,
    ui_language: str = "en",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    lesson = _require_lesson_and_access(lesson_id, user, db)
    return _lesson_full_detail(lesson, ui_language)


@router.post("/lessons/{lesson_id}/start")
def start_lesson(
    lesson_id: int,
    ui_language: str = "en",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Mark an unlocked lesson as ``in_progress`` so the home-card
    'next_lesson' heuristic prefers it. Idempotent; returns the
    same lesson-detail shape as ``GET /lessons/{id}``."""
    lesson = _require_lesson_and_access(lesson_id, user, db)
    progress = (
        db.query(UserEcoleProgress)
        .filter(
            UserEcoleProgress.user_id == user.id,
            UserEcoleProgress.lesson_id == lesson_id,
        )
        .first()
    )
    if progress and progress.status == "unlocked":
        progress.status = "in_progress"
        progress.updated_at = datetime.datetime.utcnow()
        db.commit()
    return _lesson_full_detail(lesson, ui_language)


@router.get("/lessons/{lesson_id}/quiz")
def get_quiz(
    lesson_id: int,
    ui_language: str = "en",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    lesson = _require_lesson_and_access(lesson_id, user, db)
    questions = (
        db.query(EcoleQuizQuestion)
        .filter(EcoleQuizQuestion.lesson_id == lesson.id)
        .order_by(EcoleQuizQuestion.question_number)
        .all()
    )
    return {
        "lesson_id": lesson.id,
        "lesson_number": lesson.lesson_number,
        "questions": [_question_public(q, ui_language) for q in questions],
        "pass_threshold": QUIZ_PASS_THRESHOLD,
    }


class QuizAnswer(BaseModel):
    question_number: int
    answer: str


class QuizSubmitRequest(BaseModel):
    answers: list[QuizAnswer]
    ui_language: str = "en"


@router.post("/lessons/{lesson_id}/quiz/submit")
def submit_quiz(
    lesson_id: int,
    req: QuizSubmitRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Score all 5 questions, update progress, unlock next lesson on
    pass (≥ 80%). Missing / malformed answers are counted as wrong but
    don't crash the submission."""
    lesson = _require_lesson_and_access(lesson_id, user, db)
    questions = (
        db.query(EcoleQuizQuestion)
        .filter(EcoleQuizQuestion.lesson_id == lesson.id)
        .order_by(EcoleQuizQuestion.question_number)
        .all()
    )
    if not questions:
        raise HTTPException(400, "No quiz questions configured for this lesson.")

    user_answers = {a.question_number: a.answer for a in (req.answers or [])}
    total = len(questions)
    correct_count = 0
    feedback = []
    for q in questions:
        user_answer = user_answers.get(q.question_number, "")
        is_correct = _score_single_answer(q, user_answer)
        if is_correct:
            correct_count += 1
        feedback.append(_question_with_feedback(q, user_answer, is_correct, req.ui_language))

    # Integer percentage rounded down — matches the threshold comparison
    # (79.999 rounds to 79, stays a fail).
    score_pct = int((correct_count * 100) // total)
    passed, progress = record_quiz_attempt(user, lesson, db, score_pct)

    return {
        "score": score_pct,
        "correct_count": correct_count,
        "total": total,
        "passed": passed,
        "pass_threshold": QUIZ_PASS_THRESHOLD,
        "feedback": feedback,
        "status": progress.status,
        "next_unlocked": _next_unlocked_summary(user, lesson, db, req.ui_language),
        "above_a2": is_above_a2(user, db),
    }


def _next_unlocked_summary(
    user: User,
    passed_lesson: EcoleLesson,
    db: Session,
    ui_language: str,
) -> dict | None:
    """If ``passed_lesson`` just unlocked the next row, return a tiny
    summary of that lesson for the UI to render as a celebratory link.
    Otherwise return None."""
    nxt = (
        db.query(EcoleLesson)
        .filter(EcoleLesson.lesson_number == (passed_lesson.lesson_number or 0) + 1)
        .first()
    )
    if not nxt:
        return None
    progress = (
        db.query(UserEcoleProgress)
        .filter(
            UserEcoleProgress.user_id == user.id,
            UserEcoleProgress.lesson_id == nxt.id,
        )
        .first()
    )
    if not progress or progress.status == "locked":
        return None
    title = {
        "fr": nxt.title_fr, "en": nxt.title_en, "es": nxt.title_es,
    }.get(ui_language) or nxt.title_fr or nxt.code
    return {
        "id": nxt.id,
        "lesson_number": nxt.lesson_number,
        "code": nxt.code,
        "title": title,
    }
