"""P-202 — Pydantic schemas for the curriculum data model.

DetectionRubric is the validated shape of clusters.detection_rubric (JSONB
column). P-211 authoring should produce this shape; the diagnostic engine
(P-200) reads it. Final shape evolves with detector implementation — treat
this as the authoring target, not a frozen contract.

marker_id format (locked): {level}.{phase_num}.C{cluster_num}.{letter}
e.g. "B1.1.C1.a" = level B1, phase B1.1, cluster C1, marker letter a.
The 3-segment form ("B1.1.a") in some authored cluster docs is an
authoring error to be normalized; backend treats only the 4-segment form
as canonical.

tache_application is restricted to the three speaking Tâches for Phase 1.
"writing" gets added when P-260 starts (this Literal expands then, and
the CHECK constraint in models.Cluster.__table_args__ is widened in a
follow-up migration).
"""
from __future__ import annotations

from typing import Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


CeilingLevel = Literal["A2", "B1", "B2", "C1"]
Severity = Literal["high", "medium", "low"]
ClusterStatus = Literal["not_started", "in_progress", "absorbed", "needs_revisit"]
TacheApplication = Literal["tache_1", "tache_2", "tache_3"]
LessonFormat = Literal["markdown", "pdf", "video"]


class FiringCondition(BaseModel):
    """One detector predicate. Resolved by the engine into a yes/no
    "did this marker fire on this submission" decision."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["ratio_threshold", "presence", "count", "absence"]
    metric: str
    operator: Literal["<", "<=", ">", ">=", "==", "!="]
    value: Union[float, int]
    context: Optional[str] = None


class Marker(BaseModel):
    """One ceiling marker. When firing, contributes to the cluster's
    status under status_logic."""

    model_config = ConfigDict(extra="forbid")

    marker_id: str = Field(
        ...,
        description=(
            "4-segment ID, format {level}.{phase_num}.C{cluster_num}.{letter} "
            'e.g. "B1.1.C1.a"'
        ),
    )
    name: str
    firing_condition: FiringCondition
    severity: Severity
    ceiling_level: CeilingLevel


class StatusLogic(BaseModel):
    """Predicates for cluster status determination. Phase 1 ships these
    as plain strings the engine pattern-matches; promoted to a structured
    DSL with P-200 if needed."""

    model_config = ConfigDict(extra="forbid")

    absorbed: str
    partial: str
    needs_revisit: str


class DetectionRubric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    markers: list[Marker]
    status_logic: StatusLogic
