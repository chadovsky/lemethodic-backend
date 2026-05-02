"""P-221 — diagnostic state schemas.

GET /api/diagnostic/state returns the user's progress through the
3-recording diagnostic. Phase 1 implements (B) implicit-with-banner
from the 2026-05-02 plan-first lock-in: no hard gating, just per-Tâche
coverage telemetry so the FE can render a "next recording" banner on
/ecole.

Stage transitions:

  - "no_path"    — user has no active UserPathEnrollment (waitlist or
                   pre-onboarding). FE skips the banner.
  - "in_progress"— enrollment exists, no UserLevelAssessment yet.
                   FE shows the diagnostic banner pointing at
                   `next_recommended_tache`.
  - "complete"   — at least one UserLevelAssessment row exists. FE
                   gates the one-time "diagnostic results" screen on
                   this signal (per Q3 lock-in: derived from latest
                   assessment, not a separate `diagnostic_completed_at`
                   column).

The "first 3 recordings = diagnostic" identity is implicit — P-201's
trigger fires at recording_count >= 3, which creates the first
assessment row and flips this endpoint's stage to "complete." The two
signals converge in practice.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


DiagnosticStage = Literal["in_progress", "complete", "no_path"]


class TacheCoverage(BaseModel):
    """Per-Tâche "has the user recorded at least one of these?" flags.

    Drives the `next_recommended_tache` derivation and the FE banner's
    "Tâche 1 ✓ — Tâche 2 — Tâche 3" progress chip. Counts any
    Recording row regardless of status (mirrors P-201's count rule).
    """

    model_config = ConfigDict(extra="forbid")

    tache_1: bool
    tache_2: bool
    tache_3: bool


class DiagnosticStateResponse(BaseModel):
    """Full response for GET /api/diagnostic/state."""

    model_config = ConfigDict(extra="forbid")

    stage: DiagnosticStage
    recordings_done: int = Field(ge=0)
    tache_coverage: TacheCoverage
    # Lowest Tâche (1, 2, or 3) the user hasn't recorded yet, or null
    # when all three are done. The FE banner CTA uses this; null +
    # stage="in_progress" means the user has all-Tâche coverage but
    # hasn't crossed the recording_count >= 3 threshold yet (rare —
    # would require deletes / pre-counted edge cases).
    next_recommended_tache: Optional[Literal[1, 2, 3]] = None
    # Pointer to the latest UserLevelAssessment row when stage="complete";
    # null otherwise. FE consumes this to deep-link to the results screen
    # without re-querying /me/level.
    latest_assessment_id: Optional[int] = None
