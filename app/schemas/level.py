"""P-201 — Pydantic schemas for the level assignment endpoint.

GET /api/users/me/level returns a `LevelResponse` with two independent
axes:

  - `self_reported`: from UserPathEnrollment.enrolled_at_level/_confidence
    (P-220 questionnaire data). What the user said.
  - `assigned`: from UserLevelAssessment latest row. What the system
    detected from their actual production via P-200 cluster findings.

The two axes coexist deliberately — discrepancy is product signal, not
a bug. The `agreement` field is a derived top-level enum so the FE
doesn't have to compare the sub-objects itself.

Honest assigned-level labels (below_B1 / B1_emerging / B1_solid /
above_B1 / insufficient_data) instead of raw CEFR codes — Phase 1's
13 authored clusters are all B1, so we directly validate B1 but only
INFER above/below. Labels graduate to {A2, B1, B2, C1} when other-
level curriculum content lands (P-211b).
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Slug literals ──────────────────────────────────────────────

# The system-assigned bucket — see migration d7e4f3c2b1a9 for the
# matching CHECK constraint domain.
AssignedLevel = Literal[
    "below_B1", "B1_emerging", "B1_solid", "above_B1", "insufficient_data"
]
AssignedConfidence = Literal["high", "medium", "low"]

# What the user self-reported during onboarding (P-220 Q1). Note the
# casing/wording differs intentionally — these are different domains.
SelfReportedLevel = Literal["a2", "b1", "b2", "c1", "not_sure"]
SelfReportedConfidence = Literal["high", "medium", "low"]

# Top-level derived field. "neither" is included for completeness but
# the endpoint short-circuits for the common rendering paths.
Agreement = Literal[
    "matches", "discrepancy", "self_only", "assigned_only", "neither"
]


# ── Response blocks ────────────────────────────────────────────


class SelfReportedBlock(BaseModel):
    """What the user told us during onboarding."""

    model_config = ConfigDict(extra="forbid")

    level: Optional[SelfReportedLevel] = None
    confidence: Optional[SelfReportedConfidence] = None


class AssignedBlock(BaseModel):
    """Latest system-derived assessment from P-201 algorithm."""

    model_config = ConfigDict(extra="forbid")

    level: AssignedLevel
    confidence: AssignedConfidence
    coverage: float = Field(ge=0.0, le=1.0)
    computed_at: datetime


class LevelResponse(BaseModel):
    """Full response shape for GET /api/users/me/level."""

    model_config = ConfigDict(extra="forbid")

    self_reported: SelfReportedBlock
    assigned: Optional[AssignedBlock] = None
    agreement: Agreement
