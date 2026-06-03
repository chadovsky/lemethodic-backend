"""F-410 — target-profile endpoints.

POST /api/user/target-profile  — create or update the user's active profile.
GET  /api/user/target-profile  — read the active profile (404 if none).

Upsert logic: mark any existing active row for this user as inactive, then
INSERT the new profile as the active one. This keeps full history for future
analytics without requiring a partial unique index.
"""
import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.target_profiles import TargetProfile
from app.models.models import User
from app.schemas.target_profile import TargetProfileCreate, TargetProfileResponse
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/user", tags=["target-profile"])

_VALID_BANDS = {"b1", "b2", "c1", "c2"}
_VALID_PERSONA_TAGS = {
    "visa_urgent", "academic", "professional", "general", "professional_advancement", None
}
_VALID_MAITRE_INTENSITY = {"soft", "balanced", "strict"}


@router.post("/target-profile", response_model=TargetProfileResponse, status_code=201)
def create_or_update_target_profile(
    payload: TargetProfileCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TargetProfileResponse:
    if payload.threshold_band not in _VALID_BANDS:
        raise HTTPException(
            status_code=422,
            detail=f"threshold_band must be one of {sorted(_VALID_BANDS)}",
        )
    if payload.maitre_intensity not in _VALID_MAITRE_INTENSITY:
        raise HTTPException(
            status_code=422,
            detail=f"maitre_intensity must be one of {sorted(_VALID_MAITRE_INTENSITY)}",
        )
    if payload.persona_tag not in _VALID_PERSONA_TAGS:
        raise HTTPException(
            status_code=422,
            detail=f"persona_tag must be one of {sorted(t for t in _VALID_PERSONA_TAGS if t)}",
        )

    # Deactivate any existing active profile for this user.
    db.query(TargetProfile).filter(
        TargetProfile.user_id == user.id,
        TargetProfile.is_active.is_(True),
    ).update(
        {"is_active": False, "updated_at": datetime.datetime.utcnow()},
        synchronize_session=False,
    )

    profile = TargetProfile(
        user_id=user.id,
        exam=payload.exam,
        threshold_band=payload.threshold_band,
        deadline_date=payload.deadline_date,
        persona_tag=payload.persona_tag,
        maitre_intensity=payload.maitre_intensity,
        is_active=True,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/target-profile", response_model=TargetProfileResponse)
def get_target_profile(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TargetProfileResponse:
    profile = (
        db.query(TargetProfile)
        .filter(
            TargetProfile.user_id == user.id,
            TargetProfile.is_active.is_(True),
        )
        .first()
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="No active target profile found.")
    return profile
