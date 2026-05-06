import datetime
from sqlalchemy import (
    CheckConstraint, Column, DateTime, Float, ForeignKey, Index,
    Integer, String, Text,
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


class WritingSubmissionJob(Base):
    """V-016a — async job row backing the POST→poll pattern.

    Lifecycle: pending → running → (completed | failed). The legacy
    sync POST /api/writing/submit was timing out at ~30s on prod
    because Claude analysis can take 36s+ and infrastructure (DO
    Cloudflare layer) cuts long-running requests.

    Job rows are forever-retained per Q3 lock-in 2026-05-07. File
    P-260c if table grows past noise threshold.

    See:
      - alembic/versions/g5e6f7d8c9b0_v016a_writing_jobs.py (schema)
      - app/services/writing_jobs.py (background runner)
      - app/routers/writing.py (POST /submit + GET /jobs/{id})
    """

    __tablename__ = "writing_submission_jobs"

    # UUID4 string PK (matches Conversation precedent for opaque
    # job identifiers; avoids exposing sequential integer counters
    # in URLs).
    id = Column(String(36), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # Populated only when status='completed'.
    submission_id = Column(
        Integer, ForeignKey("writing_submissions.id"), nullable=True
    )
    status = Column(String(20), nullable=False)
    created_at = Column(
        DateTime, nullable=False, default=datetime.datetime.utcnow
    )
    completed_at = Column(DateTime, nullable=True)
    # Serialized WritingSubmissionResult (mirrors legacy sync POST
    # response shape so FE polling consumer renders identically).
    result_json = Column(Text, nullable=True)
    # Sanitized error message; cap at 500 chars at write-time.
    error_message = Column(Text, nullable=True)

    user = relationship("User")
    submission = relationship("WritingSubmission")

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="ck_writing_submission_jobs_status",
        ),
        Index(
            "ix_writing_submission_jobs_user_created",
            "user_id", "created_at",
        ),
    )
