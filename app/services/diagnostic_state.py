"""P-221 — diagnostic state service.

Pure read-only orchestration over UserPathEnrollment + Recording +
UserLevelAssessment. No writes, no mutation, no Claude calls.

The state machine (per the 2026-05-02 lock-in):

  no enrollment           → "no_path"
  enrollment, no assess   → "in_progress"
  enrollment + assessment → "complete"

The "complete" signal is derived from `latest UserLevelAssessment
exists` rather than an explicit `diagnostic_completed_at` column. P-201
creates that row at the moment recording_count crosses 3, so the two
signals converge — see schemas/diagnostic.py docstring for the full
rationale.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.models import (
    Recording,
    User,
    UserLevelAssessment,
    UserPathEnrollment,
)


_NO_PATH_STATE = {
    "stage": "no_path",
    "recordings_done": 0,
    "tache_coverage": {"tache_1": False, "tache_2": False, "tache_3": False},
    "next_recommended_tache": None,
    "latest_assessment_id": None,
}


def _next_recommended_tache(coverage: dict) -> Optional[int]:
    """Lowest Tâche (1..3) the user hasn't recorded yet, or None when
    all three are covered. Foundation users completing in 1, 2, 3 order
    follow the natural progression; ad-hoc orderings still get the
    next-missing-Tâche pointer."""
    for n in (1, 2, 3):
        if not coverage[f"tache_{n}"]:
            return n
    return None


def get_diagnostic_state(db: Session, user: User) -> dict:
    """Returns a dict matching DiagnosticStateResponse's shape.

    Read-only. Safe to call on every page load — three single-row /
    aggregate queries, all hitting indexed columns.
    """
    enrollment = (
        db.query(UserPathEnrollment)
        .filter(
            UserPathEnrollment.user_id == user.id,
            UserPathEnrollment.is_active.is_(True),
        )
        .first()
    )
    if enrollment is None:
        # Defensive copy — _NO_PATH_STATE is module-level, callers
        # shouldn't be able to mutate it.
        return {**_NO_PATH_STATE, "tache_coverage": dict(_NO_PATH_STATE["tache_coverage"])}

    # One pass over the user's recordings — count + per-Tâche coverage
    # in a single query. Counts every Recording row regardless of
    # status, mirroring P-201's recording_count rule so the two
    # endpoints can't disagree on "how many recordings does this user
    # have."
    rows = (
        db.query(Recording.tache_mode)
        .filter(Recording.user_id == user.id)
        .all()
    )
    recordings_done = len(rows)
    modes_seen = {r[0] for r in rows if r[0]}
    coverage = {
        "tache_1": "tache_1" in modes_seen,
        "tache_2": "tache_2" in modes_seen,
        "tache_3": "tache_3" in modes_seen,
    }

    latest = (
        db.query(UserLevelAssessment)
        .filter(UserLevelAssessment.user_id == user.id)
        .order_by(UserLevelAssessment.computed_at.desc())
        .first()
    )
    if latest is not None:
        stage = "complete"
        latest_assessment_id: Optional[int] = latest.id
    else:
        stage = "in_progress"
        latest_assessment_id = None

    return {
        "stage": stage,
        "recordings_done": recordings_done,
        "tache_coverage": coverage,
        "next_recommended_tache": _next_recommended_tache(coverage),
        "latest_assessment_id": latest_assessment_id,
    }
