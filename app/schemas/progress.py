"""F-438 — Pydantic schemas for /api/users/me/progress endpoints."""
from __future__ import annotations

import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ProgressResponse(BaseModel):
    # From users.current_level (onboarding self-report).
    current_level: Optional[str]
    # From active target_profile.maitre_intensity — null when no profile exists.
    maitre_intensity: Optional[str]

    # F-417 engagement + progress fields (all on users table).
    streak_days: int
    longest_streak_days: int
    streak_last_active_date: Optional[datetime.date]
    production_minutes_total: int
    daily_target_minutes: int
    tache_attempts: int
    last_couche_signals: Optional[Any]

    model_config = {"from_attributes": True}


class ProgressPatch(BaseModel):
    """Fields the FE is allowed to write.

    streak_days / longest_streak_days / streak_last_active_date /
    tache_attempts are server-managed — not accepted here.
    """
    daily_target_minutes: Optional[int] = Field(None, ge=1, le=480)
    last_couche_signals: Optional[Any] = None
