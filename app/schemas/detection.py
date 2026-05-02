"""P-200 — Pydantic schemas for the cluster detection engine.

Output of `app.services.detection.detect_clusters` is shaped as
`DetectionPayload`. Each `ClusterFinding` corresponds to one cluster the
LLM evaluated against the candidate's transcript.

`extra="ignore"` is deliberate (not "forbid"): Claude may emit extra
fields ("notes", "confidence", etc.) the prompt doesn't ask for.
Forbidding extras would reject otherwise-valid findings; ignoring them
preserves the per-cluster best-effort parsing semantics (partial result
beats empty result).

Two axes that show up here:

- `status_logic_path` ∈ {absorbed, partial, needs_revisit} — which prose
  branch in the cluster's status_logic the LLM matched. Maps 1-to-1 to
  detection_result: absorbed→clean, partial→wobble, needs_revisit→fail.
- `detection_result` ∈ {clean, wobble, fail, not_observed}. The 4th
  value, `not_observed`, fires when the transcript doesn't have enough
  material to evaluate the cluster (e.g. cluster requires a 60s+
  narrative but the recording is 30s). When `not_observed`,
  `status_logic_path` and `rubric_score` are both null.
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Slug literals ──────────────────────────────────────────────

DetectionResult = Literal["clean", "wobble", "fail", "not_observed"]
StatusLogicPath = Literal["absorbed", "partial", "needs_revisit"]
Severity = Literal["high", "medium"]


# ── Models ─────────────────────────────────────────────────────


class MarkerFiring(BaseModel):
    """One marker that fired against the transcript. `evidence` is a
    verbatim quote — the prompt forbids paraphrasing."""

    model_config = ConfigDict(extra="ignore")

    marker_id: str
    severity: Severity
    evidence: str


class ClusterFinding(BaseModel):
    """Per-cluster evaluation. One per cluster the LLM was asked to
    evaluate; the `cluster_findings` array holds them all."""

    model_config = ConfigDict(extra="ignore")

    cluster_slug: str
    detection_result: DetectionResult
    fired_markers: List[MarkerFiring] = Field(default_factory=list)
    silent_markers: List[str] = Field(default_factory=list)
    # Null when detection_result == "not_observed".
    status_logic_path: Optional[StatusLogicPath] = None
    # Null when detection_result == "not_observed". Float in [0, 1].
    rubric_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class DetectionPayload(BaseModel):
    """Top-level output of detect_clusters. Telemetry fields populated
    where available; missing values fall back to None (e.g. when the
    detection failed before a Claude call could produce token counts)."""

    model_config = ConfigDict(extra="ignore")

    cluster_findings: List[ClusterFinding] = Field(default_factory=list)
    model: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None


def empty_payload(model: Optional[str] = None) -> DetectionPayload:
    """Standard degrade-to-empty result for failed detections.
    Mirrors the `_EMPTY_RESULT` pattern in module_detector.py — never
    raise, always return a valid shape."""
    return DetectionPayload(cluster_findings=[], model=model)
