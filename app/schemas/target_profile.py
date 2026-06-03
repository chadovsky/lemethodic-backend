"""F-410 — Pydantic schemas for /api/user/target-profile endpoints."""
import datetime
from typing import Optional
from pydantic import BaseModel


class TargetProfileCreate(BaseModel):
    exam: str
    threshold_band: str           # b1|b2|c1|c2
    deadline_date: Optional[datetime.date] = None
    persona_tag: Optional[str] = None  # visa_urgent|academic|professional|general|professional_advancement
    maitre_intensity: str = "balanced"  # soft|balanced|strict


class TargetProfileResponse(BaseModel):
    id: int
    user_id: int
    exam: str
    threshold_band: str
    deadline_date: Optional[datetime.date]
    persona_tag: Optional[str]
    maitre_intensity: str
    is_active: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}
