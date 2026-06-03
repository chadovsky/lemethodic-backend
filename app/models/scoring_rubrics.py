"""F-411 — ScoringRubric model.

Per (exam, level, couche_key) weight + score_mapping. Starting weights are
seeded by scripts/seed_scoring_rubrics.py; calibration is a Chadi task tracked
separately.
"""
import datetime
from sqlalchemy import Column, DateTime, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base


class ScoringRubric(Base):
    __tablename__ = "scoring_rubrics"

    id = Column(Integer, primary_key=True, index=True)
    exam = Column(String(50), nullable=False, index=True)
    # a1|a2|b1|b2|c1|c2
    level = Column(String(10), nullable=False)
    # le_propos|le_plan|la_construction|les_pieges_anglais|la_musique
    couche_key = Column(String(40), nullable=False)
    # 0.000–1.000; weights must sum to 1.0 per (exam, level) (enforced by seed/seeder)
    weight = Column(Numeric(4, 3), nullable=False)
    # e.g. {"A":"0-4","B":"5-9","C":"10-14","D":"15-20"}
    score_mapping = Column(JSONB, nullable=False, default=dict)
    passing_threshold = Column(Numeric(5, 2), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    __table_args__ = (
        UniqueConstraint(
            "exam", "level", "couche_key",
            name="uq_scoring_rubrics_exam_level_couche",
        ),
    )
