"""P-234 — cluster lookup service.

Read-only joins over Cluster + VocabularyTheme + UserClusterStatus +
UserClusterEvent. No writes, no Claude calls. Backs the two
`GET /api/clusters/...` endpoints in `app/routers/clusters.py`.

Both lookups are slug-keyed (the cluster_slug). The 404 vs default
distinction:

  - Unknown slug                → caller raises 404. Cluster doesn't exist.
  - Slug exists, no UCS row     → UserClusterStateResponse with graceful
                                  defaults (Q3 lock-in). User just hasn't
                                  engaged with this cluster yet.

Recording history is sourced from UserClusterEvent rows, NOT from
Recording rows directly — Recording has no cluster_id FK. UCE.created_at
is functionally equivalent to Recording.created_at for our purposes
(events are appended right after the detection runs, which runs right
after the upload), and reading from UCE saves a join.
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.models import (
    Cluster,
    User,
    UserClusterEvent,
    UserClusterStatus,
    VocabularyTheme,
)


logger = logging.getLogger(__name__)


# Q2 lock-in — last 10 newest-first.
_RECORDING_HISTORY_LIMIT = 10


# ── Cluster content ────────────────────────────────────────────


def get_cluster_detail(db: Session, slug: str) -> Optional[dict]:
    """Returns a dict matching `ClusterDetailResponse` shape, or None
    when the slug doesn't resolve. Single LEFT JOIN against
    VocabularyTheme.

    `detection_rubric` is NOT included in the output (Q1 lock-in —
    internal scoring infrastructure stays server-side).
    """
    cluster = (
        db.query(Cluster)
        .filter(Cluster.slug == slug)
        .first()
    )
    if cluster is None:
        return None

    theme: Optional[VocabularyTheme] = None
    if cluster.vocabulary_theme_id is not None:
        theme = (
            db.query(VocabularyTheme)
            .filter(VocabularyTheme.id == cluster.vocabulary_theme_id)
            .first()
        )

    return {
        "id": cluster.id,
        "slug": cluster.slug,
        "labels": cluster.labels if isinstance(cluster.labels, dict) else {},
        "grammar_topic": cluster.grammar_topic,
        "vocabulary_theme": (
            {"slug": theme.slug, "labels": theme.labels if isinstance(theme.labels, dict) else {}}
            if theme is not None
            else None
        ),
        "tache_application": cluster.tache_application,
        "cefr_level": cluster.cefr_level,
        "lesson": {
            "format": cluster.lesson_format,
            "markdown": cluster.lesson_markdown or "",
            "asset_url": cluster.lesson_asset_url or "",
        },
        "practice_prompt": (
            cluster.practice_prompt
            if isinstance(cluster.practice_prompt, dict)
            else {}
        ),
        "exercise_set": (
            cluster.exercise_set
            if isinstance(cluster.exercise_set, list)
            else []
        ),
    }


# ── User-cluster state ─────────────────────────────────────────


def _default_state(slug: str) -> dict:
    """The graceful "not started" response (Q3 lock-in)."""
    return {
        "cluster_slug": slug,
        "status": "not_started",
        "last_rubric_score": None,
        "last_detection_result": None,
        "revisit_count": 0,
        "first_started_at": None,
        "last_status_change_at": None,
        "absorbed_at": None,
        "recording_history": [],
    }


def _recording_history_for(
    db: Session, user_id: int, cluster_id: int
) -> list[dict]:
    """Last N UserClusterEvent rows for (user_id, cluster_id), shaped
    as RecordingHistoryEntry dicts. Newest-first.

    `detection_result` is read from `findings_json["detection_result"]`
    (the persistence helper writes a ClusterFinding-shaped dict here —
    see app/services/cluster_status_persistence.py:116). Falls back to
    "not_observed" if missing — defensive against legacy rows; should
    not occur on rows written by the current code path.
    """
    rows = (
        db.query(UserClusterEvent)
        .filter(
            UserClusterEvent.user_id == user_id,
            UserClusterEvent.cluster_id == cluster_id,
            UserClusterEvent.triggered_by_recording_id.is_not(None),
        )
        .order_by(UserClusterEvent.created_at.desc())
        .limit(_RECORDING_HISTORY_LIMIT)
        .all()
    )
    out: list[dict] = []
    for r in rows:
        findings = r.findings_json if isinstance(r.findings_json, dict) else {}
        det = findings.get("detection_result")
        if det not in ("clean", "wobble", "fail", "not_observed"):
            det = "not_observed"
        out.append({
            "recording_id": r.triggered_by_recording_id,
            "created_at": r.created_at,
            "detection_result": det,
            "rubric_score": r.rubric_score,
        })
    return out


def get_user_cluster_state(
    db: Session, user: User, slug: str
) -> Optional[dict]:
    """Returns a dict matching `UserClusterStateResponse` shape, or
    None when the slug doesn't resolve to a Cluster.

    When the cluster exists but the user has no UCS row, returns the
    graceful default state (Q3 lock-in). 404 is reserved for unknown
    slugs (caller's responsibility).
    """
    cluster = (
        db.query(Cluster)
        .filter(Cluster.slug == slug)
        .first()
    )
    if cluster is None:
        return None

    status_row: Optional[UserClusterStatus] = (
        db.query(UserClusterStatus)
        .filter(
            UserClusterStatus.user_id == user.id,
            UserClusterStatus.cluster_id == cluster.id,
        )
        .first()
    )
    if status_row is None:
        return _default_state(slug)

    return {
        "cluster_slug": slug,
        "status": status_row.status,
        "last_rubric_score": status_row.last_rubric_score,
        "last_detection_result": status_row.last_detection_result,
        "revisit_count": status_row.revisit_count or 0,
        "first_started_at": status_row.first_started_at,
        "last_status_change_at": status_row.last_status_change_at,
        "absorbed_at": status_row.absorbed_at,
        "recording_history": _recording_history_for(db, user.id, cluster.id),
    }
