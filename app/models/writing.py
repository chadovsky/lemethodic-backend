import datetime
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class WritingPrompt(Base):
    __tablename__ = "writing_prompts"

    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(10), nullable=False)  # B1, B2, C1
    theme = Column(String(100), nullable=False)
    prompt_text = Column(Text, nullable=False)
    prompt_type = Column(String(50), nullable=False)  # argumentative, formal_letter, essay
    min_words = Column(Integer, default=100)
    max_words = Column(Integer, default=300)
    time_limit_minutes = Column(Integer, default=45)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    submissions = relationship("WritingSubmission", back_populates="prompt")


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
