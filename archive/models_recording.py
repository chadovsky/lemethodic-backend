# Dead code from pre-routers async scaffold. Archived during F-077
# PostgreSQL migration to prevent accidental Alembic Base.metadata
# pollution. 5-minute insurance against accidental import.
from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Recording(Base):
    __tablename__ = "recordings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    topic = Column(String(500), nullable=False)
    audio_url = Column(String(1000))  # S3 path
    audio_duration_sec = Column(Float)
    transcript = Column(Text)
    status = Column(String(50), default="uploaded")  # uploaded | transcribing | analyzing | complete | error
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="recordings")
    feedback = relationship("Feedback", back_populates="recording", uselist=False)


class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    recording_id = Column(Integer, ForeignKey("recordings.id"), unique=True, nullable=False)
    score = Column(Float)  # 0-20 (TCF scale)
    analysis = Column(JSON)  # structured Les Moules breakdown
    corrections = Column(Text)  # readable corrections with examples
    raw_response = Column(Text)  # full LLM response for debugging
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    recording = relationship("Recording", back_populates="feedback")
