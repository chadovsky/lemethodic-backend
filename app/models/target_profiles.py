"""F-410 — TargetProfile model.

One row per user-profile configuration. At most one row per user should have
is_active=True at any time (enforced at the router upsert layer, not at the
DB layer — a partial unique index would be cleaner but adds complexity for
negligible benefit at Y0 scale).
"""
import datetime
from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String
from app.database import Base


class TargetProfile(Base):
    __tablename__ = "target_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    exam = Column(String(50), nullable=False)
    # b1|b2|c1|c2
    threshold_band = Column(String(10), nullable=False)
    deadline_date = Column(Date, nullable=True)
    # visa_urgent|academic|professional|general|professional_advancement
    persona_tag = Column(String(40), nullable=True)
    # soft|balanced|strict
    maitre_intensity = Column(String(20), nullable=False, default="balanced")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )
