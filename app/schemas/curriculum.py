"""P-202 — Pydantic schemas for the curriculum data model.

DetectionRubric is the validated shape of clusters.detection_rubric (JSONB
column). The shape is dual-source:

- P-211 ingestion writes the prose-faithful form: marker_id, name,
  firing_condition_prose (verbatim from authored markdown), severity,
  ceiling_level. Structured `firing_condition` is left empty.
- P-200 detector implementation promotes prose -> structured
  `FiringCondition` per marker as detectors come online. Both fields can
  coexist on a marker; the engine prefers structured when present.

A `Marker` MUST have at least one of `firing_condition` or
`firing_condition_prose` (validator enforces). Final shape continues to
evolve with detector implementation — treat this as the authoring
target, not a frozen contract.

marker_id format (locked): {level}.{phase_num}.C{cluster_num}.{letter}
e.g. "B1.1.C1.a" = level B1, phase B1.1, cluster C1, marker letter a.
The 3-segment form ("B1.1.a") in some authored cluster docs is an
authoring error normalized at ingest time; backend treats only the
4-segment form as canonical (see P-211a).

tache_application is restricted to the three speaking Tâches for Phase 1.
"writing" gets added when P-260 starts (this Literal expands then, and
the CHECK constraint in models.Cluster.__table_args__ is widened in a
follow-up migration).
"""
from __future__ import annotations

from typing import Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator


CeilingLevel = Literal["A2", "B1", "B2", "C1"]
Severity = Literal["high", "medium", "low"]
ClusterStatus = Literal["not_started", "in_progress", "absorbed", "needs_revisit"]
TacheApplication = Literal["tache_1", "tache_2", "tache_3"]
LessonFormat = Literal["markdown", "pdf", "video"]


class FiringCondition(BaseModel):
    """Structured detector predicate. Populated by P-200 as detectors
    come online. Until then, P-211 ingestion stores the authored prose
    in Marker.firing_condition_prose instead."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["ratio_threshold", "presence", "count", "absence"]
    metric: str
    operator: Literal["<", "<=", ">", ">=", "==", "!="]
    value: Union[float, int]
    context: Optional[str] = None


class Marker(BaseModel):
    """One ceiling marker. When firing, contributes to the cluster's
    status under status_logic.

    Dual-source firing definition:
    - `firing_condition` — structured form; populated by P-200.
    - `firing_condition_prose` — verbatim authored prose; populated by
      P-211 ingest from the cluster markdown.

    At least one must be present (validator)."""

    model_config = ConfigDict(extra="forbid")

    marker_id: str = Field(
        ...,
        description=(
            "4-segment ID, format {level}.{phase_num}.C{cluster_num}.{letter} "
            'e.g. "B1.1.C1.a"'
        ),
    )
    name: str
    firing_condition: Optional[FiringCondition] = None
    firing_condition_prose: Optional[str] = None
    severity: Severity
    ceiling_level: CeilingLevel

    @model_validator(mode="after")
    def _at_least_one_firing(self) -> "Marker":
        if self.firing_condition is None and not self.firing_condition_prose:
            raise ValueError(
                "Marker must have either firing_condition (structured) or "
                "firing_condition_prose (authored text)"
            )
        return self


class StatusLogic(BaseModel):
    """Predicates for cluster status determination. Phase 1 ships these
    as plain strings the engine pattern-matches; promoted to a structured
    DSL with P-200 if needed."""

    model_config = ConfigDict(extra="forbid")

    absorbed: str
    partial: str
    needs_revisit: str


class DetectionRubric(BaseModel):
    """Cluster-level detection rubric.

    `quantitative_signals` is preserved from the authored "Quantitative
    signals" table verbatim (rows: name / computation / threshold). P-200
    detector specs draw from this list; Phase 1 dashboards may render it
    for transparency."""

    model_config = ConfigDict(extra="forbid")

    markers: list[Marker]
    status_logic: StatusLogic
    quantitative_signals: Optional[list[dict]] = None
