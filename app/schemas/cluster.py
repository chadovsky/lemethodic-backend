"""P-234 — cluster detail view schemas.

Two endpoints surface the FE's cluster detail page:

  - `GET /api/clusters/{slug}` returns `ClusterDetailResponse` (the
    curriculum content — grammar topic, vocabulary theme, lesson body,
    practice prompt, exercise set).
  - `GET /api/users/me/clusters/{slug}` returns `UserClusterStateResponse`
    (per-user state snapshot + last 10 recordings of history).

Plan-first lock-in (2026-05-03):

  Q1: `detection_rubric` is hidden — internal scoring infrastructure,
      leaking marker conditions gives sophisticated users the test
      answers.
  Q2: Recording history is last 10 newest-first, fields = recording_id,
      created_at, detection_result, rubric_score.
  Q3: When the user has no UserClusterStatus row for the cluster,
      return graceful defaults (`status="not_started"`, all timestamps
      null, empty history). 404 only on unknown slugs.
  Q4: Lesson markdown is FR-only Phase 1. FE renders the language hint
      based on `interface_language` — promotion to JSONB is P-211b's
      scope when other-language lesson content is authored.
  Q5: Both endpoints require auth (any logged-in user). No path-
      enrollment scoping — curriculum browsing is friction-free,
      enrollment gates the practice flow.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Slug literals ──────────────────────────────────────────────


# Mirror of Cluster.tache_application CHECK constraint domain.
# Phase 1 speaking-only — promote when P-260 (writing) lands.
TacheApplication = Literal["tache_1", "tache_2", "tache_3"]

# Lifecycle (UserClusterStatus.status). Independent axis from
# detection_result — see P-200 design notes.
ClusterLifecycle = Literal[
    "not_started", "in_progress", "absorbed", "needs_revisit"
]

# Per-event detection finding (mirrors DetectionResult in
# app/schemas/detection.py — duplicated here so this module doesn't
# depend on the detection schema's transitive imports).
DetectionResult = Literal["clean", "wobble", "fail", "not_observed"]

# Cluster.lesson_format CHECK domain.
LessonFormat = Literal["markdown", "pdf", "video"]


# ── Cluster content ────────────────────────────────────────────


class VocabularyThemeRef(BaseModel):
    """Joined VocabularyTheme — slug + i18n labels only. Returns null
    on the parent ClusterDetailResponse when the cluster has no theme
    assigned (vocabulary_theme_id IS NULL)."""

    model_config = ConfigDict(extra="forbid")

    slug: str
    labels: dict[str, str]


class ClusterLesson(BaseModel):
    """Combined lesson sub-object on ClusterDetailResponse.

    `markdown` is the rendered lesson body — FR-only Phase 1, populated
    when `format == "markdown"`. `asset_url` carries a CDN URL when
    `format ∈ {pdf, video}`. Exactly one of the two carries content
    per the lesson_format invariant.
    """

    model_config = ConfigDict(extra="forbid")

    format: LessonFormat
    markdown: str = ""
    asset_url: str = ""


class ClusterDetailResponse(BaseModel):
    """Full response for `GET /api/clusters/{slug}`.

    `detection_rubric` deliberately omitted — internal scoring
    infrastructure (Q1 lock-in). `practice_prompt` and `exercise_set`
    are JSONB pass-throughs whose shape is owned by the cluster
    authoring rubric (P-211 / P-211a) — kept loose here so authoring
    schema drift doesn't break this contract.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    slug: str
    labels: dict[str, str]
    grammar_topic: str
    vocabulary_theme: Optional[VocabularyThemeRef] = None
    tache_application: TacheApplication
    cefr_level: str
    lesson: ClusterLesson
    practice_prompt: dict[str, Any]
    exercise_set: list[Any]


# ── User-cluster state ─────────────────────────────────────────


class RecordingHistoryEntry(BaseModel):
    """One entry in the recording history list. Sourced from
    UserClusterEvent rows (one per detection event on this cluster).
    """

    model_config = ConfigDict(extra="forbid")

    recording_id: int
    created_at: datetime
    detection_result: DetectionResult
    rubric_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class UserClusterStateResponse(BaseModel):
    """Full response for `GET /api/users/me/clusters/{slug}`.

    Defaults applied when the user has no UserClusterStatus row for
    this cluster (Q3 lock-in — graceful "not started" UX, not 404).
    `recording_history` is last 10 newest-first (Q2).
    """

    model_config = ConfigDict(extra="forbid")

    cluster_slug: str
    status: ClusterLifecycle
    last_rubric_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    last_detection_result: Optional[DetectionResult] = None
    revisit_count: int = Field(ge=0)
    first_started_at: Optional[datetime] = None
    last_status_change_at: Optional[datetime] = None
    absorbed_at: Optional[datetime] = None
    recording_history: list[RecordingHistoryEntry]
