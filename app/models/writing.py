import datetime
from sqlalchemy import (
    CheckConstraint, Column, DateTime, Float, ForeignKey, Integer,
    String, Text,
)
from sqlalchemy.orm import relationship
from app.database import Base


class WritingPrompt(Base):
    __tablename__ = "writing_prompts"

    id = Column(Integer, primary_key=True, index=True)

    # ── Legacy columns (kept for backward-compat with existing
    # endpoints + writing_analysis.py). Auto-backfilled at seed-time
    # from the canonical fields below; see scripts/seed_writing_prompts.py
    # for the topic_tag→theme + tache_level→prompt_type mapping rules.
    level = Column(String(10), nullable=False)              # = target_level
    theme = Column(String(100), nullable=False)             # = topic_tag (FR-capitalized)
    prompt_text = Column(Text, nullable=False)              # = prompt_fr
    prompt_type = Column(String(50), nullable=False)        # derived from tache_level
    time_limit_minutes = Column(Integer, default=45)        # = time_limit_min
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # ── F-224 v1 pack canonical fields. CHECK constraints mirrored in
    # Alembic migration f4d5e6c7b8a9.
    tache_level = Column(Integer, nullable=False)
    title_fr = Column(String(120), nullable=False)
    prompt_fr = Column(Text, nullable=False)
    prompt_en = Column(Text, nullable=False)
    topic_tag = Column(String(40), nullable=False)

    min_words = Column(Integer, default=100)
    max_words = Column(Integer, default=300)

    submissions = relationship("WritingSubmission", back_populates="prompt")

    __table_args__ = (
        CheckConstraint(
            "tache_level IN (1, 2, 3)",
            name="ck_writing_prompts_tache_level",
        ),
        CheckConstraint(
            "topic_tag IN ("
            "'travel', 'work', 'family', 'education', 'health', "
            "'technology', 'environment', 'society'"
            ")",
            name="ck_writing_prompts_topic_tag",
        ),
    )


class WritingSubmission(Base):
    __tablename__ = "writing_submissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    prompt_id = Column(Integer, ForeignKey("writing_prompts.id"), nullable=False)
    student_text = Column(Text, nullable=False)
    feedback_json = Column(Text, default="{}")  # Full Claude response JSON
    word_count = Column(Integer, default=0)
    overall_score = Column(Float, default=0)
    time_taken_seconds = Column(Integer, default=0)
    submitted_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User")
    prompt = relationship("WritingPrompt", back_populates="submissions")
