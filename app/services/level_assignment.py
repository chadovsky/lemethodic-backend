"""P-201 — level assignment service.

Pure rule-based algorithm + DB orchestration. No Claude API call —
phase 1's 13-all-B1 cluster inventory makes LLM-based level assignment
overkill (per the 2026-05-02 plan-first decision Q1).

Trigger: `compute_and_persist_if_threshold` is called from the
recording-finalization paths (`recordings.py /upload` and
`conversations.py /end`) after `persist_detection_result`. Fires only
when the user has >=3 recordings; below threshold returns None.

Failure isolation: callers wrap in try/except (mirroring F-080b /
P-200's pattern). The service itself raises on real DB errors so the
caller can roll back; ordinary "no data" cases return None.

Algorithm shape (per the locked plan):
  - 5-cluster floor: <5 evaluated → "insufficient_data" + low confidence
  - clean_share >= 0.80 + high coverage + high agreement → "above_B1"
  - clean_share >= 0.80 → "B1_solid"
  - clean_share >= 0.50 → "B1_emerging"
  - fail_share >= 0.50 → "below_B1"
  - else → "B1_emerging" (mixed signal default)

  Confidence = coverage × top_bucket_share, bucketed:
    >=0.70 high, >=0.40 medium, else low.

P-250 calibrates these thresholds against real beta data.
"""
from __future__ import annotations

import logging
from typing import Iterable, Literal, Optional

from sqlalchemy.orm import Session

from app.models.models import (
    Cluster,
    PathCluster,
    Phase,
    Recording,
    UserClusterStatus,
    UserLevelAssessment,
    UserPathEnrollment,
)
from app.schemas.level import (
    Agreement,
    AssignedLevel,
    SelfReportedLevel,
)


logger = logging.getLogger(__name__)


# ── Pure algorithm ─────────────────────────────────────────────


_DetectionResult = Literal["clean", "wobble", "fail", "not_observed"]


def compute_level_assignment(
    detection_results: Iterable[_DetectionResult],
    total_clusters_in_path: int,
) -> dict:
    """Map a list of per-cluster detection results into a level + confidence
    + telemetry. Returns a dict matching the user_level_assessments columns
    so callers can pass it to `UserLevelAssessment(**result)`.

    `total_clusters_in_path` is the denominator for coverage — the count
    of authored, rubric-bearing clusters in the user's active path.
    Dynamic via _count_active_clusters_for_user_path; defaults to 13
    (Phase 1 b1_to_b2) when no path is resolvable.
    """
    results = list(detection_results)
    n_clean = sum(1 for r in results if r == "clean")
    n_wobble = sum(1 for r in results if r == "wobble")
    n_fail = sum(1 for r in results if r == "fail")
    n_evaluated = n_clean + n_wobble + n_fail

    coverage = (n_evaluated / total_clusters_in_path) if total_clusters_in_path else 0.0
    coverage = min(coverage, 1.0)  # defensive cap

    if n_evaluated < 5:
        # 5-cluster floor — too sparse to assign meaningfully.
        level: AssignedLevel = "insufficient_data"
        top_bucket_share = 0.0
    else:
        bucket_max = max(n_clean, n_wobble, n_fail)
        top_bucket_share = bucket_max / n_evaluated
        clean_share = n_clean / n_evaluated
        fail_share = n_fail / n_evaluated

        if clean_share >= 0.80 and coverage >= 0.95 and top_bucket_share >= 0.90:
            level = "above_B1"
        elif clean_share >= 0.80:
            level = "B1_solid"
        elif clean_share >= 0.50:
            level = "B1_emerging"
        elif fail_share >= 0.50:
            level = "below_B1"
        else:
            level = "B1_emerging"

    confidence_score = coverage * top_bucket_share
    if confidence_score >= 0.70:
        confidence = "high"
    elif confidence_score >= 0.40:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "assigned_level": level,
        "assigned_confidence": confidence,
        "coverage": coverage,
        "top_bucket_share": top_bucket_share,
        "confidence_score": confidence_score,
        "n_clusters_evaluated": n_evaluated,
        "n_clusters_clean": n_clean,
        "n_clusters_wobble": n_wobble,
        "n_clusters_fail": n_fail,
    }


# ── DB helpers ─────────────────────────────────────────────────


_DEFAULT_PHASE_1_CLUSTER_COUNT = 13   # Phase 1 b1_to_b2 fallback


def _count_active_clusters_for_user_path(db: Session, user_id: int) -> int:
    """Total authored, rubric-bearing clusters in the user's active path.
    Generalizes when other paths land (a2_to_b1, b2_to_c1) — no code
    change needed when curriculum content for those levels ships."""
    enrollment = (
        db.query(UserPathEnrollment)
        .filter(
            UserPathEnrollment.user_id == user_id,
            UserPathEnrollment.is_active.is_(True),
        )
        .first()
    )
    if enrollment is None:
        return _DEFAULT_PHASE_1_CLUSTER_COUNT
    # Python-side filter for the "rubric is non-empty" check — same
    # pattern as detection._fetch_active_clusters. SQL-side empty-JSONB
    # comparison via parameterized literal{} doesn't adapt cleanly under
    # psycopg, and at 13 rows the cost of a Python list-comp is trivial.
    matches = (
        db.query(Cluster)
        .join(PathCluster, PathCluster.cluster_id == Cluster.id)
        .join(Phase, Phase.id == PathCluster.phase_id)
        .filter(Phase.path_id == enrollment.path_id)
        .all()
    )
    n = sum(
        1
        for c in matches
        if isinstance(c.detection_rubric, dict)
        and c.detection_rubric.get("markers")
    )
    return n or _DEFAULT_PHASE_1_CLUSTER_COUNT


def _fetch_user_detection_results(db: Session, user_id: int) -> list[_DetectionResult]:
    """Latest detection result per cluster for this user. Reads the
    snapshot table user_cluster_statuses (one row per user-cluster pair)."""
    rows = (
        db.query(UserClusterStatus.last_detection_result)
        .filter(
            UserClusterStatus.user_id == user_id,
            UserClusterStatus.last_detection_result.is_not(None),
        )
        .all()
    )
    return [r[0] for r in rows]


def _user_recording_count(db: Session, user_id: int) -> int:
    return (
        db.query(Recording)
        .filter(Recording.user_id == user_id)
        .count()
    )


# ── Trigger orchestration ──────────────────────────────────────


_RECORDING_THRESHOLD = 3   # per Q4 — fire after 3rd recording


def compute_and_persist_if_threshold(
    db: Session,
    *,
    user_id: int,
    recording: Recording,
) -> Optional[int]:
    """Compute + persist a UserLevelAssessment if the user has >=3
    recordings. Returns the new row's id, or None if threshold not met
    or no detection results exist yet.

    Caller wraps in try/except (F-080b pattern). This function commits
    its own writes; on success the row is durably persisted before
    returning.
    """
    if _user_recording_count(db, user_id) < _RECORDING_THRESHOLD:
        return None

    results = _fetch_user_detection_results(db, user_id)
    if not results:
        # User has 3+ recordings but no detection results landed yet —
        # P-200 is best-effort; this is a defensive no-op.
        logger.info(
            "P-201 compute_and_persist: user_id=%s has %d recordings but "
            "zero detection results; skipping.",
            user_id,
            _user_recording_count(db, user_id),
        )
        return None

    total_clusters = _count_active_clusters_for_user_path(db, user_id)
    assignment = compute_level_assignment(results, total_clusters)

    row = UserLevelAssessment(
        user_id=user_id,
        triggered_by_recording_id=recording.id,
        **assignment,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    logger.info(
        "P-201 compute_and_persist: user_id=%s recording_id=%s -> "
        "level=%s confidence=%s coverage=%.2f (assessment_id=%s)",
        user_id,
        recording.id,
        row.assigned_level,
        row.assigned_confidence,
        row.coverage,
        row.id,
    )
    return row.id


# ── Agreement derivation ───────────────────────────────────────


_SELF_ZONE = {
    "a2": "below",
    "b1": "at",
    "b2": "above",
    "c1": "above",
    "not_sure": "unknown",
}
_ASSIGNED_ZONE = {
    "below_B1": "below",
    "B1_emerging": "at",
    "B1_solid": "at",
    "above_B1": "above",
    "insufficient_data": "unknown",
}


def compute_agreement(
    self_reported: Optional[SelfReportedLevel],
    assigned: Optional[AssignedLevel],
) -> Agreement:
    """Derive a single agreement label from the two axes for FE
    convenience. Maps both into a shared {below, at, above, unknown}
    zone before comparing — neither raw enum is directly comparable."""
    if self_reported is None and assigned is None:
        return "neither"
    if assigned is None:
        return "self_only"
    if self_reported is None:
        return "assigned_only"

    self_zone = _SELF_ZONE.get(self_reported, "unknown")
    assigned_zone = _ASSIGNED_ZONE.get(assigned, "unknown")
    return "matches" if self_zone == assigned_zone else "discrepancy"
