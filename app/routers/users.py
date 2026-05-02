"""User profile routes — onboarding persistence and /me.

POST /api/users/onboarding writes the six onboarding fields to the current
user's row. GET /api/users/me is an alias of /api/auth/me using the same
shared serializer, so the frontend can hit either.
"""
import datetime as _dt
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy import String, cast, distinct, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import (
    Recording,
    RemediationModule,
    SessionDetectedModule,
    User,
    UserLevelAssessment,
    UserPathEnrollment,
)
from app.schemas.level import (
    AssignedBlock,
    LevelResponse,
    SelfReportedBlock,
)
from app.services.auth import get_current_user
from app.services.level_assignment import compute_agreement
from app.services.user_profile import serialize_user

router = APIRouter(prefix="/api/users", tags=["users"])


class OnboardingData(BaseModel):
    target_level: str
    exam_profile: str
    exam_date: Optional[date] = None
    goal: str
    current_level: str
    interface_language: str


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return serialize_user(user)


@router.get("/me/level", response_model=LevelResponse)
def get_user_level(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LevelResponse:
    """P-201 — return the user's level on two independent axes.

    self_reported: from active UserPathEnrollment (P-220 questionnaire).
    assigned: from latest UserLevelAssessment row (P-201 algorithm).
    agreement: derived top-level signal — matches | discrepancy |
               self_only | assigned_only | neither.
    """
    # Self-reported (P-220)
    enrollment = (
        db.query(UserPathEnrollment)
        .filter(
            UserPathEnrollment.user_id == user.id,
            UserPathEnrollment.is_active.is_(True),
        )
        .first()
    )
    if enrollment is not None:
        self_reported = SelfReportedBlock(
            level=enrollment.enrolled_at_level,
            confidence=enrollment.enrolled_at_confidence,
        )
    else:
        self_reported = SelfReportedBlock()

    # Assigned (latest UserLevelAssessment).
    latest = (
        db.query(UserLevelAssessment)
        .filter(UserLevelAssessment.user_id == user.id)
        .order_by(UserLevelAssessment.computed_at.desc())
        .first()
    )
    assigned = (
        AssignedBlock(
            level=latest.assigned_level,
            confidence=latest.assigned_confidence,
            coverage=latest.coverage,
            computed_at=latest.computed_at,
        )
        if latest
        else None
    )

    return LevelResponse(
        self_reported=self_reported,
        assigned=assigned,
        agreement=compute_agreement(
            self_reported.level,
            assigned.level if assigned else None,
        ),
    )


@router.post("/onboarding", deprecated=True)
def complete_onboarding(
    data: OnboardingData,
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """DEPRECATED — use POST /onboarding/submit instead.

    Kept accept-and-no-op for the duration of the FE migration window.
    Writes the original 5 fields (target_level, exam_profile, exam_date,
    goal, current_level) and ui_language; the 7 new P-220 fields are NOT
    written here. Removed entirely once the FE migrates to the new
    endpoint.
    """
    user.target_level = data.target_level
    user.exam_profile = data.exam_profile
    user.exam_date = data.exam_date
    user.goal = data.goal
    user.current_level = data.current_level
    # Map API's `interface_language` onto the existing ui_language column.
    user.ui_language = data.interface_language
    db.commit()
    db.refresh(user)
    # RFC 8594-style soft deprecation signaling.
    response.headers["Deprecation"] = "true"
    response.headers["Link"] = '</onboarding/submit>; rel="successor-version"'
    return serialize_user(user)


# F-080d threshold for surfacing a module in "Recommended for you". Three
# distinct recordings (sessions) is the minimum that justifies calling
# something a "recurring" pattern rather than a one-off detection.
RECURRING_MODULE_RECORDING_THRESHOLD = 3


def _coerce_iso(value) -> str | None:
    """SessionDetectedModule.detected_at can come back as a datetime
    (when the ORM hydrates a real row) or as an ISO string (SQLite +
    func.min/max return strings). Normalize to ISO-8601 string for the
    API response."""
    if value is None:
        return None
    if isinstance(value, _dt.datetime):
        return value.isoformat()
    return str(value)


@router.get("/me/recurring_modules")
def recurring_modules(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """F-080d B1 — modules detected in 3+ distinct recordings for this
    user, sorted by severity DESC then recurrence_count DESC.

    Response shape:
        {
          "recurring_modules": [
            {
              "module_id": str,
              "name_en": str,
              "name_fr": str,
              "category": str,
              "severity": int,
              "ecole_lesson_id": int | null,
              "recurrence_count": int,           # >= 3
              "first_detected_at": ISO-8601,
              "last_detected_at":  ISO-8601,
              "recording_ids": [int, ...]        # ascending; the spec used
                                                  # session_ids loosely —
                                                  # these are recording PKs
                                                  # (one detection-session
                                                  # per recording).
            },
            ...
          ]
        }

    Cold user (fewer than 3 sessions, or 3+ sessions with no recurring
    detection) returns ``{"recurring_modules": []}`` at status 200.

    Query plan note (F-080d.x perf follow-up): recordings.user_id is
    not indexed today. The query starts from session_detected_modules
    (small) and joins recordings via the PK index, so the user_id
    filter is a per-row check on the joined recording rows — fast for
    first-1000-users scale. If this hot-paths in production, add an
    index on recordings(user_id).
    """
    # Aggregate query: per module, count distinct recordings + min/max
    # detected_at + concatenated recording_ids. The HAVING clause filters
    # to recurring modules only.
    agg_rows = (
        db.query(
            SessionDetectedModule.module_id.label("module_id"),
            func.count(distinct(SessionDetectedModule.recording_id)).label("recurrence_count"),
            func.min(SessionDetectedModule.detected_at).label("first_detected_at"),
            func.max(SessionDetectedModule.detected_at).label("last_detected_at"),
            func.string_agg(distinct(cast(SessionDetectedModule.recording_id, String)), ",").label("recording_ids_csv"),
        )
        .join(Recording, Recording.id == SessionDetectedModule.recording_id)
        .filter(Recording.user_id == user.id)
        .group_by(SessionDetectedModule.module_id)
        .having(
            func.count(distinct(SessionDetectedModule.recording_id))
            >= RECURRING_MODULE_RECORDING_THRESHOLD
        )
        .all()
    )

    if not agg_rows:
        return {"recurring_modules": []}

    # Hydrate module rows in one IN-list query.
    module_ids = [row.module_id for row in agg_rows]
    module_rows = (
        db.query(RemediationModule)
        .filter(RemediationModule.id.in_(module_ids))
        .all()
    )
    module_by_id = {m.id: m for m in module_rows}

    out: list[dict] = []
    for row in agg_rows:
        m = module_by_id.get(row.module_id)
        if m is None:
            # Detection rows reference a deleted module — skip silently
            # (mirror of recordings.py /detected-modules behavior).
            continue
        recording_ids = sorted(
            int(x) for x in (row.recording_ids_csv or "").split(",") if x
        )
        out.append(
            {
                "module_id": row.module_id,
                "name_en": m.name_en,
                "name_fr": m.name_fr,
                "category": m.category,
                "severity": m.severity,
                "ecole_lesson_id": m.ecole_lesson_id,
                "recurrence_count": int(row.recurrence_count),
                "first_detected_at": _coerce_iso(row.first_detected_at),
                "last_detected_at": _coerce_iso(row.last_detected_at),
                "recording_ids": recording_ids,
            }
        )

    # Severity DESC, recurrence_count DESC. Stable on ties via module_id.
    out.sort(key=lambda r: (-r["severity"], -r["recurrence_count"], r["module_id"]))
    return {"recurring_modules": out}
