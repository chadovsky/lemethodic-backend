"""P-240 — today's recommended action endpoint.

`GET /api/users/me/today` — read-only prescription surface. Drives the
"Today's focus" slot on /ecole (replaces the hardcoded DailyActionCard).

See `app/schemas/today.py` and `app/services/recommendation.py` for the
contract and rule chain rationale. Prose layer (Block 5 Dialogue Box)
deferred to P-240b — blocked on P-213 (Chadi authoring 30-50 templates).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import User
from app.schemas.today import TodayActionResponse
from app.services.auth import get_current_user
from app.services.recommendation import compute_today_action


router = APIRouter(prefix="/api/users", tags=["today"])


@router.get("/me/today", response_model=TodayActionResponse)
def today_action(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TodayActionResponse:
    return TodayActionResponse(**compute_today_action(db, user))
