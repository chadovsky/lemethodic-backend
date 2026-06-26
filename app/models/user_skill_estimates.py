"""F-485 - UserSkillEstimate model.

User-global per-skill CEFR estimate store. One row per user (unique user_id).
This is the coarse, persona-independent layer: a single estimated CEFR level
per skill (CO, CE, EO, EE) that carries across personas. It is deliberately
NOT the persona-scoped recency-decayed mastery engine (that is a later ticket),
and it is NOT the F-410 target_profiles store (exam target / persona config),
which is a separate, already-shipped table.

The `estimates` JSON holds the shape:
    {
        "CO": {"level": "B1", "updated_at": "2026-06-26T12:00:00"},
        "CE": {"level": "A2", "updated_at": "..."},
        "EO": {...},
        "EE": {...}
    }
Skills not yet estimated are simply absent from the dict.
"""
import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class UserSkillEstimate(Base):
    __tablename__ = "user_skill_estimates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    estimates = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )
