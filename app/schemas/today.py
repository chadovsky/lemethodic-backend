"""P-240 — Today's recommended action schemas.

`GET /api/users/me/today` returns the single next action the
prescription engine recommends. Per the 2026-05-02 plan-first
lock-in, P-240 ships the **action layer** only — what cluster, what
Tâche, what prompt, plus a `reason_code` telling the FE why.

The **prose layer** (Block 5 Dialogue Box rendering — Chadi-voice
templates filled with detected data) is deferred to P-240b, blocked
on P-213 (30-50 templates authored by Chadi). The `dialogue_box` slot
is reserved in the contract from day one so P-240b is purely
additive — never breaks this shape.

Rule chain (first-match-wins, factored in `recommendation._pick_cluster`):

  1. regression       — any cluster with `last_detection_result == "fail"`
                        (even absorbed). Lowest path position breaks ties.
  2. needs_revisit    — any cluster with `status == "needs_revisit"`.
  3. in_progress      — any cluster with `status == "in_progress"`.
  4. next_in_path     — lowest-position `not_started` cluster.
  5. free_practice    — path complete (all clusters absorbed without
                        recent fail). No specific cluster pointer.
  6. no_path          — user has no active enrollment (waitlist /
                        pre-onboarding). Mirrors /api/diagnostic/state's
                        `no_path` semantics.

P-241 will reuse the same `_pick_cluster` helper to enforce a hard
navigation gate on rules 1+2 (route the user back to that cluster);
this endpoint is the soft-recommendation surface only.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Slug literals ──────────────────────────────────────────────


Kind = Literal[
    "cluster_practice",   # rules 1-4 — recommend a specific cluster's Tâche
    "free_practice",      # rule 5 — path complete, free practice
    "path_complete",      # alias when there's literally nothing left to do
    "no_path",            # rule 6 — no active enrollment
]

ReasonCode = Literal[
    "regression",
    "needs_revisit",
    "in_progress",
    "next_in_path",
    "free_practice",
    "no_path",
]

# Phase 1 speaking-only — promote when P-260 (writing) lands.
TacheApplication = Literal["tache_1", "tache_2", "tache_3"]


# ── Response blocks ────────────────────────────────────────────


class ActionBlock(BaseModel):
    """The recommendation itself.

    For `kind == "cluster_practice"`, all of `cluster_id`, `cluster_slug`,
    `tache_application`, and `practice_prompt` are populated.
    For `free_practice` / `path_complete` / `no_path`, those four are
    null and `reason_code` carries the meaning.
    """

    model_config = ConfigDict(extra="forbid")

    kind: Kind
    cluster_id: Optional[int] = None
    cluster_slug: Optional[str] = None
    tache_application: Optional[TacheApplication] = None
    # JSONB pass-through from Cluster.practice_prompt. Shape varies by
    # cluster — kept as a free-form dict here so the FE renders whatever
    # the cluster authored. P-211 / P-211a defines the canonical shape.
    practice_prompt: Optional[dict[str, Any]] = None
    reason_code: ReasonCode


class ContextBlock(BaseModel):
    """Surrounding state the FE may want to show alongside the action.

    `current_phase_id` / `current_phase_position` reflect the phase that
    the recommended cluster lives in. Both are null for free_practice /
    path_complete / no_path.

    `clusters_remaining_in_path` counts non-absorbed clusters in the
    user's enrolled path (regardless of which one was recommended).
    """

    model_config = ConfigDict(extra="forbid")

    current_phase_id: Optional[int] = None
    current_phase_position: Optional[int] = Field(default=None, ge=1)
    clusters_remaining_in_path: int = Field(ge=0)
    last_recording_at: Optional[datetime] = None


class TodayActionResponse(BaseModel):
    """Full response for `GET /api/users/me/today`."""

    model_config = ConfigDict(extra="forbid")

    action: ActionBlock
    context: ContextBlock
    # Reserved slot for P-240b. Always null in P-240; kept in the contract
    # so adding prose later is purely additive.
    dialogue_box: Optional[dict[str, Any]] = None
