"""F-485 - Pydantic schemas for /api/users/me/skill-estimates endpoints."""
from typing import Any, Dict, Optional

from pydantic import BaseModel


class SkillEstimateValue(BaseModel):
    """One per-skill estimate as submitted by the client.

    Only `level` is accepted from the client; `updated_at` is always set
    server-side on write and any client-supplied value is ignored.
    """

    level: str


class SkillEstimatesUpdate(BaseModel):
    """Partial upsert payload.

    `estimates` is optional and maps skill code (CO|CE|EO|EE) to its value.
    Provided skills overwrite; omitted skills are left untouched (merge).
    """

    estimates: Optional[Dict[str, SkillEstimateValue]] = None


class SkillEstimatesRead(BaseModel):
    """Read response. `estimates` is the full per-skill map.

    Shape: {"CO": {"level": "B1", "updated_at": iso}, ...}. Empty dict when
    the user has no estimates yet.
    """

    estimates: Dict[str, Any]
