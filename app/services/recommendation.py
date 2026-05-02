"""P-240 — recommendation service.

Pure rule-based prescription. No Claude API call — Phase 1's 13-cluster
inventory makes LLM-based recommendation overkill (per the 2026-05-02
plan-first decision Q2). Hot path on every `/ecole` visit, so latency
+ determinism dominate over expressive output.

Read-only. No writes. Three queries per call (enrollment, ordered path,
all UserClusterStatus rows for the user) plus a single recency lookup.

`_pick_cluster` is factored as a stand-alone helper so P-241 (hard
navigation gate on regression / needs_revisit) can import it and
enforce the same rule chain.

Rule chain (first-match-wins):
  1. regression     — any cluster with `last_detection_result == "fail"`
  2. needs_revisit  — any cluster with `status == "needs_revisit"`
  3. in_progress    — any cluster with `status == "in_progress"`
  4. next_in_path   — lowest-position `not_started` cluster
  5. free_practice  — all path clusters absorbed (rule 5 returns no
                      specific cluster — caller surfaces `kind="free_practice"`)

Tiebreak across multiple matches within a rule: lowest PathCluster
position (advance the path linearly).

`UserPathEnrollment.current_phase_id` / `.current_cluster_id` cache
columns exist in the schema but are NOT written by application code
today (verified 2026-05-02). Derive on-the-fly here; revisit caching
once a writer ships.
"""
from __future__ import annotations

import logging
from typing import Iterable, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.models import (
    Cluster,
    PathCluster,
    Phase,
    Recording,
    User,
    UserClusterStatus,
    UserPathEnrollment,
)


logger = logging.getLogger(__name__)


# ── Path traversal ─────────────────────────────────────────────


_PathRow = Tuple[Phase, PathCluster, Cluster]


def _ordered_path_clusters(db: Session, path_id: int) -> list[_PathRow]:
    """All (Phase, PathCluster, Cluster) rows in the path, sorted by
    Phase.position ASC then PathCluster.position ASC. Phase 1 b1_to_b2
    has 5 phases × ~3 clusters = ≤22 rows; trivial."""
    rows = (
        db.query(Phase, PathCluster, Cluster)
        .join(PathCluster, PathCluster.phase_id == Phase.id)
        .join(Cluster, Cluster.id == PathCluster.cluster_id)
        .filter(Phase.path_id == path_id)
        .order_by(Phase.position.asc(), PathCluster.position.asc())
        .all()
    )
    return list(rows)


def _statuses_by_cluster_id(
    db: Session, user_id: int
) -> dict[int, UserClusterStatus]:
    rows = (
        db.query(UserClusterStatus)
        .filter(UserClusterStatus.user_id == user_id)
        .all()
    )
    return {r.cluster_id: r for r in rows}


# ── Rule chain ─────────────────────────────────────────────────


def _pick_cluster(
    ordered: list[_PathRow],
    statuses: dict[int, UserClusterStatus],
) -> Tuple[Optional[Cluster], Optional[Phase], str]:
    """First-match-wins rule chain. Returns (cluster, phase, reason_code).

    On rule 5 (path complete), returns (None, None, "free_practice").
    Caller distinguishes from rule 6 (no_path, no enrollment) which
    short-circuits before this is called.

    Shared with P-241: the gate ticket will use the same picker but
    enforce hard re-routing on `regression` / `needs_revisit` rules.
    """
    # Rule 1 — regression. last_detection_result == "fail" wins even when
    # the lifecycle status is "absorbed" (a cluster the user thought was
    # solid that just regressed). Lowest position breaks ties.
    for phase, _pc, cluster in ordered:
        st = statuses.get(cluster.id)
        if st is not None and st.last_detection_result == "fail":
            return cluster, phase, "regression"

    # Rule 2 — needs_revisit lifecycle.
    for phase, _pc, cluster in ordered:
        st = statuses.get(cluster.id)
        if st is not None and st.status == "needs_revisit":
            return cluster, phase, "needs_revisit"

    # Rule 3 — in_progress. The user is mid-cluster; consistency wins
    # over advancing.
    for phase, _pc, cluster in ordered:
        st = statuses.get(cluster.id)
        if st is not None and st.status == "in_progress":
            return cluster, phase, "in_progress"

    # Rule 4 — next not_started cluster in path. A row with no
    # UserClusterStatus is treated as not_started (the snapshot table
    # is created lazily by P-200; absence == "never touched").
    for phase, _pc, cluster in ordered:
        st = statuses.get(cluster.id)
        if st is None or st.status == "not_started":
            return cluster, phase, "next_in_path"

    # Rule 5 — path complete. All clusters absorbed without active fail.
    return None, None, "free_practice"


# ── Public entry point ─────────────────────────────────────────


def _last_recording_at(db: Session, user_id: int):
    row = (
        db.query(Recording.created_at)
        .filter(Recording.user_id == user_id)
        .order_by(Recording.created_at.desc())
        .first()
    )
    return row[0] if row else None


def _clusters_remaining(
    ordered: list[_PathRow], statuses: dict[int, UserClusterStatus]
) -> int:
    """Non-absorbed clusters in the path — what the user still has to
    cover. Matches the FE's "you have N clusters left" display."""
    n = 0
    for _phase, _pc, cluster in ordered:
        st = statuses.get(cluster.id)
        if st is None or st.status != "absorbed":
            n += 1
    return n


def compute_today_action(db: Session, user: User) -> dict:
    """Return a dict matching `TodayActionResponse`'s shape. Read-only."""
    enrollment = (
        db.query(UserPathEnrollment)
        .filter(
            UserPathEnrollment.user_id == user.id,
            UserPathEnrollment.is_active.is_(True),
        )
        .first()
    )

    last_rec_at = _last_recording_at(db, user.id)

    if enrollment is None:
        # Rule 6 — no active enrollment. Mirrors /diagnostic/state's
        # no_path semantics so the FE can branch identically.
        return {
            "action": {
                "kind": "no_path",
                "cluster_id": None,
                "cluster_slug": None,
                "tache_application": None,
                "practice_prompt": None,
                "reason_code": "no_path",
            },
            "context": {
                "current_phase_id": None,
                "current_phase_position": None,
                "clusters_remaining_in_path": 0,
                "last_recording_at": last_rec_at,
            },
            "dialogue_box": None,
        }

    ordered = _ordered_path_clusters(db, enrollment.path_id)
    statuses = _statuses_by_cluster_id(db, user.id)

    cluster, phase, reason = _pick_cluster(ordered, statuses)
    remaining = _clusters_remaining(ordered, statuses)

    if cluster is None:
        # Rule 5 — free_practice. Path complete; no cluster pointer.
        # Phase 1 doesn't surface a "weakest Tâche" tiebreak yet (low-
        # signal bucket scoring at 13 clusters); FE can pick a default
        # Tâche or show a celebration card. Revisit if/when path
        # completion happens to a real user pre-Phase 2.
        return {
            "action": {
                "kind": "free_practice",
                "cluster_id": None,
                "cluster_slug": None,
                "tache_application": None,
                "practice_prompt": None,
                "reason_code": "free_practice",
            },
            "context": {
                "current_phase_id": None,
                "current_phase_position": None,
                "clusters_remaining_in_path": 0,
                "last_recording_at": last_rec_at,
            },
            "dialogue_box": None,
        }

    return {
        "action": {
            "kind": "cluster_practice",
            "cluster_id": cluster.id,
            "cluster_slug": cluster.slug,
            "tache_application": cluster.tache_application,
            "practice_prompt": (
                cluster.practice_prompt
                if isinstance(cluster.practice_prompt, dict)
                else {}
            ),
            "reason_code": reason,
        },
        "context": {
            "current_phase_id": phase.id if phase is not None else None,
            "current_phase_position": phase.position if phase is not None else None,
            "clusters_remaining_in_path": remaining,
            "last_recording_at": last_rec_at,
        },
        "dialogue_box": None,
    }
