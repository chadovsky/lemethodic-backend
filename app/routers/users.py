"""User profile routes — onboarding persistence and /me.

POST /api/users/onboarding writes the six onboarding fields to the current
user's row. GET /api/users/me is an alias of /api/auth/me using the same
shared serializer, so the frontend can hit either.
"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import User
from app.services.auth import get_current_user
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


@router.post("/onboarding")
def complete_onboarding(
    data: OnboardingData,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user.target_level = data.target_level
    user.exam_profile = data.exam_profile
    user.exam_date = data.exam_date
    user.goal = data.goal
    user.current_level = data.current_level
    # Map API's `interface_language` onto the existing ui_language column.
    user.ui_language = data.interface_language
    db.commit()
    db.refresh(user)
    return serialize_user(user)
