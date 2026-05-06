"""V-016a — Pydantic schemas for the async writing-job pattern.

POST /api/writing/submit returns 202 with `WritingSubmitResponse`
(job_id + status). The FE polls GET /api/writing/jobs/{id} which
returns `WritingJobResponse` carrying status + result | error +
timestamps.

`result` is a free-form dict (the legacy sync-POST response shape
serialized as JSON in the job row). FE consumer reads `result.feedback`
to render the 4-layer Claude analysis.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict


JobStatus = Literal["pending", "running", "completed", "failed"]


class WritingSubmitResponse(BaseModel):
    """POST /api/writing/submit — 202 response."""

    model_config = ConfigDict(extra="forbid")

    job_id: str
    status: JobStatus


class WritingJobResponse(BaseModel):
    """GET /api/writing/jobs/{job_id} — full job state."""

    model_config = ConfigDict(extra="forbid")

    job_id: str
    status: JobStatus
    # Populated when status='completed'. Free-form dict — same shape as
    # the legacy sync POST /submit response (id, word_count,
    # time_taken_seconds, feedback, submitted_at).
    result: Optional[dict[str, Any]] = None
    # Populated when status='failed'.
    error: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
