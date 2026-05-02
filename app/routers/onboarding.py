"""P-220 — onboarding questionnaire endpoints.

GET  /onboarding/questions  — return the 11 questions in canonical
                              order with FR + EN copy.
POST /onboarding/submit     — persist answers, resolve path slug,
                              derive persona, create UserPathEnrollment
                              (when active path) or return waitlist
                              signal.

The legacy POST /api/users/onboarding endpoint stays mounted with a
Deprecation header until the frontend migrates to /onboarding/submit
(see app/routers/users.py).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import (
    Path as PathModel,
    User,
    UserPathEnrollment,
)
from app.schemas.onboarding import (
    CapacityWarning,
    OnboardingQuestionsResponse,
    OnboardingSubmitRequest,
    OnboardingSubmitResponse,
)
from app.services.auth import get_current_user
from app.services.onboarding_questions import build_questions
from app.services.onboarding_router import (
    derive_capacity_warning,
    derive_persona,
    is_path_active,
    resolve_path_slug,
    should_offer_b1_to_b2_fallback,
)


router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.get("/questions", response_model=OnboardingQuestionsResponse)
def get_questions() -> OnboardingQuestionsResponse:
    """Return the 11 onboarding questions, FR + EN. Public — pre-auth
    flows render the questionnaire before signup completes."""
    return OnboardingQuestionsResponse(questions=build_questions())


@router.post("/submit", response_model=OnboardingSubmitResponse)
def submit_onboarding(
    payload: OnboardingSubmitRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OnboardingSubmitResponse:
    """Persist the 11 answers, resolve the path, optionally create an
    active UserPathEnrollment with persona derivation."""

    # ── Persist all answers to User ─────────────────────────────
    user.current_level = payload.q1_current_level
    user.target_level = payload.q2_target_level
    user.exam_date = payload.q3_exam_date     # None when no_exam_scheduled=True
    user.goal = payload.q4_motivation         # may be None (Q4 optional)
    user.strongest_skill = payload.q5_strongest_skill
    user.weakest_skill = payload.q6_weakest_skill
    user.hours_per_week = payload.q7_hours_per_week
    user.topics_tested_on = payload.q8_topics_tested_on or None

    # Q9: store either the slug, or the free-text override when "other".
    if payload.q9_native_language == "other":
        user.native_language = (payload.q9_native_language_other or "").strip()
    else:
        user.native_language = payload.q9_native_language

    user.prior_french_exam = payload.q10_prior_exam_history
    user.feedback_mode_preference = payload.q11_feedback_mode

    # Q4-Q10 are stored but not yet routed-on. P-220.x picks up routing.
    # TODO P-220.x: motivation -> theme priority weighting
    # TODO P-220.x: strongest/weakest skill -> diagnostic emphasis
    # TODO P-220.x: weakest_skill + topics_tested_on -> cluster prioritization
    # TODO P-220.x: native_language -> detector calibration (Phase 2)
    # TODO P-220.x: prior_french_exam -> credibility-of-self-assessment

    # ── Resolve path slug + persona ─────────────────────────────
    path_slug = resolve_path_slug(payload.q1_current_level, payload.q2_target_level)
    persona = derive_persona(payload.q3_exam_date, payload.q3_no_exam_scheduled)

    # ── Waitlist branch: path not built yet (only b1_to_b2 active) ──
    if not is_path_active(path_slug):
        db.flush()
        db.commit()
        fallback = (
            "b1_to_b2"
            if should_offer_b1_to_b2_fallback(
                payload.q1_current_level, payload.q2_target_level
            )
            else None
        )
        return OnboardingSubmitResponse(
            path_slug=None,
            persona=None,
            redirect_to_diagnostic=False,
            waitlist=True,
            waitlist_reason="path_not_active",
            fallback_path_offered=fallback,
            user_path_enrollment_id=None,
        )

    # ── Active path: enroll ─────────────────────────────────────
    path = db.query(PathModel).filter(PathModel.slug == path_slug).first()
    if path is None:
        # Active set says it should exist; DB disagrees -> infrastructure bug.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Configured active path '{path_slug}' not found in DB",
        )

    # Enforce one-active-enrollment-per-user invariant (matches the partial
    # unique index on user_path_enrollments). Deactivate any existing active
    # enrollment for this user before creating the new one.
    existing_active = (
        db.query(UserPathEnrollment)
        .filter(
            UserPathEnrollment.user_id == user.id,
            UserPathEnrollment.is_active.is_(True),
        )
        .all()
    )
    for e in existing_active:
        e.is_active = False
    db.flush()

    # If the user is re-onboarding into the same path, reuse the row
    # (the (user_id, path_id) UNIQUE constraint forbids a new insert).
    enrollment = (
        db.query(UserPathEnrollment)
        .filter(
            UserPathEnrollment.user_id == user.id,
            UserPathEnrollment.path_id == path.id,
        )
        .first()
    )
    if enrollment is None:
        enrollment = UserPathEnrollment(
            user_id=user.id,
            path_id=path.id,
            enrolled_at_level=path.level_start,
            enrolled_at_confidence=None,   # P-221 fills after diagnostic
            is_active=True,
            persona=persona,
        )
        db.add(enrollment)
    else:
        enrollment.is_active = True
        enrollment.persona = persona

    db.commit()
    db.refresh(enrollment)

    # ── Capacity warning (non-blocking signal) ──────────────────
    warning_dict = derive_capacity_warning(
        payload.q3_exam_date,
        payload.q3_no_exam_scheduled,
        payload.q7_hours_per_week,
    )
    capacity_warning = CapacityWarning(**warning_dict) if warning_dict else None

    return OnboardingSubmitResponse(
        path_slug=path_slug,
        persona=persona,
        redirect_to_diagnostic=True,
        waitlist=False,
        capacity_warning=capacity_warning,
        user_path_enrollment_id=enrollment.id,
    )
