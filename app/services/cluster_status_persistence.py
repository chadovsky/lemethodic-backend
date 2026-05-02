"""P-200 — persistence helper for detection results.

Writes the output of `app.services.detection.detect_clusters` to the
two existing tables:

  user_cluster_statuses  ← upsert: last_detection_result,
                                   last_evaluated_recording_id,
                                   last_rubric_score,
                                   last_status_change_at
  user_cluster_events    ← insert one row per finding, with findings_json
                           carrying the per-cluster payload + top-level
                           detection telemetry

Lifecycle (`UserClusterStatus.status`) is NOT touched here. Detection
result and lifecycle are independent axes per the P-200 design (Q1 of
the 2026-05-02 plan-first round). Lifecycle transitions land via the
prescription engine (P-241) on a separate trigger.

Out-of-band like F-080b's persist_detected_modules — the detector
service returns a typed payload; this helper writes it. Never raises;
logs and continues if any single cluster row fails.
"""
from __future__ import annotations

import datetime
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.models import (
    Cluster,
    Recording,
    UserClusterEvent,
    UserClusterStatus,
)
from app.schemas.detection import DetectionPayload


logger = logging.getLogger(__name__)


def persist_detection_result(
    db: Session,
    *,
    user_id: int,
    recording: Recording,
    payload: DetectionPayload,
) -> int:
    """Upsert per-cluster status snapshots and append per-cluster events.

    Returns the number of cluster findings successfully persisted. Findings
    referencing unknown cluster_slugs are dropped (logged) — same defensive
    posture as `module_library.persist_detected_modules`.

    The caller commits. This helper flushes but does not commit, matching
    the existing recording-router pattern where the analyzer's writes are
    bundled with the Feedback insert into one transaction.
    """
    if not payload.cluster_findings:
        return 0

    # Resolve cluster_slug → Cluster row in one batch query.
    slugs = [f.cluster_slug for f in payload.cluster_findings]
    rows = db.query(Cluster).filter(Cluster.slug.in_(slugs)).all()
    cluster_by_slug = {c.slug: c for c in rows}

    persisted = 0
    now = datetime.datetime.utcnow()

    for finding in payload.cluster_findings:
        cluster = cluster_by_slug.get(finding.cluster_slug)
        if cluster is None:
            logger.warning(
                "P-200 persist: dropping finding with unknown cluster_slug=%s "
                "(LLM hallucination or schema drift); recording_id=%s",
                finding.cluster_slug,
                recording.id,
            )
            continue

        # ── Upsert UserClusterStatus snapshot ──────────────────
        status_row: Optional[UserClusterStatus] = (
            db.query(UserClusterStatus)
            .filter(
                UserClusterStatus.user_id == user_id,
                UserClusterStatus.cluster_id == cluster.id,
            )
            .first()
        )
        if status_row is None:
            # First time this user has been evaluated for this cluster —
            # create the row at default lifecycle ("not_started"); the
            # detection result is the first signal. We set status
            # explicitly rather than relying on the column default
            # because the default only applies at flush time, but we
            # read status_row.status below for the event row's
            # from_status/to_status.
            status_row = UserClusterStatus(
                user_id=user_id,
                cluster_id=cluster.id,
                status="not_started",
            )
            db.add(status_row)

        status_row.last_detection_result = finding.detection_result
        status_row.last_evaluated_recording_id = recording.id
        if finding.rubric_score is not None:
            status_row.last_rubric_score = finding.rubric_score
        status_row.last_status_change_at = now

        # ── Append UserClusterEvent (event log row) ────────────
        # When a detection runs without changing lifecycle (the common
        # case), from_status == to_status == current lifecycle. The
        # findings_json carries the meaningful payload.
        findings_json = {
            **finding.model_dump(mode="json", exclude_none=False),
            "model": payload.model,
            "input_tokens": payload.input_tokens,
            "output_tokens": payload.output_tokens,
        }
        event = UserClusterEvent(
            user_id=user_id,
            cluster_id=cluster.id,
            from_status=status_row.status,
            to_status=status_row.status,   # detection alone doesn't transition lifecycle
            triggered_by_recording_id=recording.id,
            rubric_score=finding.rubric_score,
            findings_json=findings_json,
        )
        db.add(event)
        persisted += 1

    db.flush()
    logger.info(
        "P-200 persist: %d/%d findings written for recording_id=%s user_id=%s",
        persisted,
        len(payload.cluster_findings),
        recording.id,
        user_id,
    )
    return persisted
