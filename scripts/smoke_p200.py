"""Smoke test for P-200 detection engine + persistence.

Coverage (per the 2026-05-02 plan-first agreement):
  Step 1 — schema columns present (commit 1's migration applied)
  Step 2 — Pydantic shape validation (valid + invalid)
  Step 3 — _format_cluster_rubrics_for_prompt produces non-empty text
  Step 4 — _fetch_active_clusters excludes placeholders (B1.4 / B1.5)
  Step 5 — _coerce_payload per-cluster best-effort (5 valid + 1 invalid)
  Step 6 — detect_clusters with no API key → empty payload, no exception
  Step 7 — persistence writes both tables; status (lifecycle) untouched
  Step 8 — CHECK constraint on last_detection_result rejects bad values

Doesn't hit the Claude API — exercises the demo-mode short-circuit and
direct _coerce_payload paths so the test runs offline.

Run: python -m scripts.smoke_p200
"""
from __future__ import annotations

import asyncio
import datetime
import sys

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal, engine
from app.models.models import (
    Cluster,
    Recording,
    User,
    UserClusterEvent,
    UserClusterStatus,
)
from app.schemas.detection import (
    ClusterFinding,
    DetectionPayload,
    MarkerFiring,
)
from app.services.cluster_status_persistence import persist_detection_result
from app.services.detection import (
    _coerce_payload,
    _fetch_active_clusters,
    _format_cluster_rubrics_for_prompt,
    detect_clusters,
)


errors: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    extra = f" -- {detail}" if detail else ""
    print(f"  [{status}] {name}{extra}")
    if not ok:
        errors.append(name)


def step_1_schema() -> None:
    print("\nStep 1: schema columns present")
    with engine.connect() as c:
        cols = {
            r[0]: r[1]
            for r in c.execute(
                text(
                    "SELECT column_name, data_type FROM information_schema.columns "
                    "WHERE (table_name='user_cluster_statuses' "
                    "       AND column_name='last_detection_result') "
                    "OR (table_name='user_cluster_events' AND column_name='findings_json')"
                )
            ).fetchall()
        }
    check("last_detection_result on user_cluster_statuses", "last_detection_result" in cols,
          cols.get("last_detection_result", "absent"))
    check("findings_json on user_cluster_events",
          cols.get("findings_json") == "jsonb",
          cols.get("findings_json", "absent"))


def step_2_pydantic() -> None:
    print("\nStep 2: Pydantic ClusterFinding shape validation")
    valid = {
        "cluster_slug": "B1.1.C1",
        "detection_result": "fail",
        "fired_markers": [
            {"marker_id": "B1.1.C1.a", "severity": "high",
             "evidence": "j'ai vu un film hier qui était très intéressant"}
        ],
        "silent_markers": ["B1.1.C1.b", "B1.1.C1.c"],
        "status_logic_path": "needs_revisit",
        "rubric_score": 0.0,
    }
    cf = ClusterFinding.model_validate(valid)
    check("valid finding accepted", cf.cluster_slug == "B1.1.C1")

    # not_observed: status_logic_path + rubric_score both null
    no_obs = {**valid,
              "detection_result": "not_observed",
              "status_logic_path": None,
              "rubric_score": None,
              "fired_markers": []}
    ClusterFinding.model_validate(no_obs)
    check("not_observed with null fields accepted", True)

    # invalid detection_result
    bad = {**valid, "detection_result": "exploded"}
    try:
        ClusterFinding.model_validate(bad)
        check("rejects invalid detection_result", False)
    except Exception:
        check("rejects invalid detection_result", True)

    # rubric_score out of range
    oor = {**valid, "rubric_score": 1.5}
    try:
        ClusterFinding.model_validate(oor)
        check("rejects rubric_score > 1.0", False)
    except Exception:
        check("rejects rubric_score > 1.0", True)

    # extra fields tolerated (extra="ignore")
    extra = {**valid, "confidence": 0.9, "notes": "LLM-added field"}
    cf2 = ClusterFinding.model_validate(extra)
    check("extra fields tolerated (ignored)", cf2.cluster_slug == "B1.1.C1")


def step_3_format_rubrics() -> None:
    print("\nStep 3: _format_cluster_rubrics_for_prompt output")
    db = SessionLocal()
    try:
        clusters = _fetch_active_clusters(db, "tache_3")
        blob = _format_cluster_rubrics_for_prompt(clusters)
    finally:
        db.close()
    check("blob non-empty for tache_3", len(blob) > 100)
    check("contains cluster slug B1.1.C1", "B1.1.C1" in blob)
    check("contains marker_id format", "B1.1.C1.a" in blob)
    check("contains status logic", "absorbed:" in blob and "needs_revisit:" in blob)


def step_4_filter_placeholders() -> None:
    print("\nStep 4: cluster filter excludes placeholders")
    db = SessionLocal()
    try:
        all_t3 = (db.query(Cluster)
                  .filter(Cluster.tache_application == "tache_3")
                  .all())
        active_t3 = _fetch_active_clusters(db, "tache_3")
    finally:
        db.close()
    # All 9 placeholders are tache_3 default. Of those, only the 6
    # authored ones (B1.1-B1.3 with tache_3) should pass the filter.
    placeholder_count = sum(
        1 for c in all_t3
        if not (c.detection_rubric and c.detection_rubric.get("markers"))
    )
    check(f"tache_3 has {placeholder_count} placeholders excluded",
          placeholder_count > 0)
    check("active_t3 contains only rubric-bearing clusters",
          all(c.detection_rubric.get("markers") for c in active_t3))
    check("active_t3 has 6 clusters (B1.1.C1..C3, C9, B1.3.C11, C13)",
          len(active_t3) == 6, str(len(active_t3)))


def step_5_best_effort() -> None:
    print("\nStep 5: _coerce_payload per-cluster best-effort parsing")
    # 5 valid + 1 invalid (bad detection_result) — expect 5 to survive
    raw_envelope = {
        "cluster_findings": [
            {"cluster_slug": "B1.1.C1", "detection_result": "clean",
             "fired_markers": [], "silent_markers": ["B1.1.C1.a"],
             "status_logic_path": "absorbed", "rubric_score": 1.0},
            {"cluster_slug": "B1.1.C2", "detection_result": "wobble",
             "fired_markers": [{"marker_id": "B1.1.C2.a", "severity": "medium",
                                "evidence": "ce que j'ai compris"}],
             "silent_markers": [],
             "status_logic_path": "partial", "rubric_score": 0.5},
            # Invalid: detection_result="oops" not in Literal
            {"cluster_slug": "B1.1.C3", "detection_result": "oops",
             "fired_markers": [], "silent_markers": [],
             "status_logic_path": "absorbed", "rubric_score": 1.0},
            {"cluster_slug": "B1.2.C9", "detection_result": "fail",
             "fired_markers": [], "silent_markers": [],
             "status_logic_path": "needs_revisit", "rubric_score": 0.0},
            {"cluster_slug": "B1.3.C11", "detection_result": "not_observed",
             "fired_markers": [], "silent_markers": [],
             "status_logic_path": None, "rubric_score": None},
            {"cluster_slug": "B1.3.C13", "detection_result": "clean",
             "fired_markers": [], "silent_markers": [],
             "status_logic_path": "absorbed", "rubric_score": 1.0},
        ]
    }
    payload = _coerce_payload(raw_envelope, model="test-model")
    check("5 of 6 findings survived (best-effort)",
          len(payload.cluster_findings) == 5,
          f"got {len(payload.cluster_findings)}")
    surviving_slugs = {f.cluster_slug for f in payload.cluster_findings}
    check("the 1 invalid cluster (B1.1.C3) was skipped",
          "B1.1.C3" not in surviving_slugs)

    # Zero-survival case: all entries malformed → empty result
    raw_all_bad = {"cluster_findings": [
        {"cluster_slug": "X", "detection_result": "no"},
        {"cluster_slug": "Y", "detection_result": "no"},
    ]}
    empty_payload = _coerce_payload(raw_all_bad, model="test")
    check("zero valid → empty cluster_findings",
          len(empty_payload.cluster_findings) == 0)


def step_6_no_api_key() -> None:
    print("\nStep 6: detect_clusters in demo mode (no API key)")
    # Override settings.ANTHROPIC_API_KEY to empty for the duration of
    # this check so we exercise the demo-mode branch without hitting
    # the actual Claude API.
    from app.config import settings
    saved = settings.ANTHROPIC_API_KEY
    settings.ANTHROPIC_API_KEY = ""
    try:
        db = SessionLocal()
        try:
            payload = asyncio.run(
                detect_clusters("Hier j'ai mangé une pomme.", "tache_3", db)
            )
        finally:
            db.close()
        check("demo mode returns empty cluster_findings",
              len(payload.cluster_findings) == 0)
        check("demo mode does not raise", True)
    finally:
        settings.ANTHROPIC_API_KEY = saved


def step_7_persistence() -> None:
    print("\nStep 7: persist_detection_result writes both tables")
    db = SessionLocal()
    try:
        # Setup: ensure user + recording fixtures.
        u = db.query(User).filter_by(email="smoke@p200.local").first()
        if u is None:
            u = User(email="smoke@p200.local", hashed_password="x",
                     full_name="P-200 Smoke")
            db.add(u)
            db.commit()
            db.refresh(u)
        rec = (db.query(Recording).filter_by(user_id=u.id).first())
        if rec is None:
            rec = Recording(user_id=u.id, audio_path="smoke/p200.wav",
                            target_level="B1", tache_mode="tache_3")
            db.add(rec)
            db.commit()
            db.refresh(rec)

        cl = db.query(Cluster).filter_by(slug="B1.1.C1").first()
        prev_lifecycle = (db.query(UserClusterStatus)
                          .filter_by(user_id=u.id, cluster_id=cl.id)
                          .first())
        prev_status = prev_lifecycle.status if prev_lifecycle else "not_started"

        payload = DetectionPayload(
            cluster_findings=[
                ClusterFinding(
                    cluster_slug="B1.1.C1",
                    detection_result="fail",
                    fired_markers=[MarkerFiring(
                        marker_id="B1.1.C1.a",
                        severity="high",
                        evidence="hier j'ai mangé une pomme c'était bon",
                    )],
                    silent_markers=["B1.1.C1.b", "B1.1.C1.c", "B1.1.C1.d", "B1.1.C1.e"],
                    status_logic_path="needs_revisit",
                    rubric_score=0.0,
                ),
            ],
            model="claude-sonnet-4-20250514",
            input_tokens=5500,
            output_tokens=180,
        )

        persist_detection_result(db, user_id=u.id, recording=rec, payload=payload)
        db.commit()

        # Assertions on UserClusterStatus
        status_row = (db.query(UserClusterStatus)
                      .filter_by(user_id=u.id, cluster_id=cl.id)
                      .first())
        check("UserClusterStatus row exists", status_row is not None)
        check("last_detection_result = 'fail'",
              status_row.last_detection_result == "fail",
              str(status_row.last_detection_result))
        check("last_evaluated_recording_id matches",
              status_row.last_evaluated_recording_id == rec.id)
        check("last_rubric_score = 0.0", status_row.last_rubric_score == 0.0)
        # Lifecycle status should NOT have changed
        check("lifecycle status untouched (still %r)" % prev_status,
              status_row.status == prev_status,
              str(status_row.status))

        # Assertions on UserClusterEvent
        evt = (db.query(UserClusterEvent)
               .filter_by(user_id=u.id, cluster_id=cl.id,
                          triggered_by_recording_id=rec.id)
               .order_by(UserClusterEvent.id.desc())
               .first())
        check("UserClusterEvent row exists for this recording", evt is not None)
        check("event.findings_json populated",
              isinstance(evt.findings_json, dict)
              and "fired_markers" in evt.findings_json)
        check("event.findings_json includes telemetry",
              evt.findings_json.get("model") == "claude-sonnet-4-20250514")
        check("event.from_status == event.to_status (no lifecycle change)",
              evt.from_status == evt.to_status)
        check("event.rubric_score = 0.0", evt.rubric_score == 0.0)
    finally:
        db.close()


def step_8_check_constraint() -> None:
    print("\nStep 8: CHECK constraint rejects invalid last_detection_result")
    db = SessionLocal()
    try:
        u = db.query(User).filter_by(email="smoke@p200.local").first()
        cl = db.query(Cluster).filter_by(slug="B1.1.C2").first()
        # Use INSERT to a separate cluster_id to avoid hitting uq_user_cluster
        try:
            db.execute(
                text(
                    "INSERT INTO user_cluster_statuses "
                    "(user_id, cluster_id, status, last_detection_result) "
                    "VALUES (:u, :c, 'in_progress', 'banana')"
                ),
                {"u": u.id, "c": cl.id},
            )
            db.commit()
            check("CHECK rejects 'banana'", False, "INSERT succeeded")
        except IntegrityError as e:
            check("CHECK rejects 'banana'",
                  "ck_user_cluster_statuses_last_detection_result" in str(e.orig))
            db.rollback()
    finally:
        db.close()


def step_9_analyzer_wiring() -> None:
    """Commit-3 wiring test: monkey-patch detect_clusters → canned
    DetectionPayload → call analyze_tache_3 → assert
    cluster_findings_payload threaded through to result dict.

    Lighter than a full _run_analysis_and_persist round-trip — exercises
    the analyzer-side wiring (the new code path) without depending on
    Claude API / STT / audio uploads. Persistence path is covered by
    Step 7 already.
    """
    print("\nStep 9: analyzer wiring (commit-3 integration)")
    import asyncio
    from unittest.mock import patch

    from app.config import settings as app_settings
    from app.services import tache_3 as tache_3_module
    from app.schemas.detection import (
        ClusterFinding,
        DetectionPayload,
        MarkerFiring,
    )

    # Canned payload the monkey-patched detect_clusters returns.
    canned = DetectionPayload(
        cluster_findings=[
            ClusterFinding(
                cluster_slug="B1.1.C1",
                detection_result="fail",
                fired_markers=[MarkerFiring(
                    marker_id="B1.1.C1.a",
                    severity="high",
                    evidence="hier j'ai mangé",
                )],
                silent_markers=["B1.1.C1.b"],
                status_logic_path="needs_revisit",
                rubric_score=0.0,
            ),
            ClusterFinding(
                cluster_slug="B1.1.C2",
                detection_result="clean",
                fired_markers=[],
                silent_markers=["B1.1.C2.a", "B1.1.C2.b"],
                status_logic_path="absorbed",
                rubric_score=1.0,
            ),
        ],
        model="canned-test-model",
        input_tokens=100,
        output_tokens=50,
    )

    async def fake_detect_clusters(transcript, tache_mode, db):
        return canned

    db = SessionLocal()
    saved_key = app_settings.ANTHROPIC_API_KEY
    app_settings.ANTHROPIC_API_KEY = ""  # demo mode for the 4-couche call
    try:
        # Patch the symbol the analyzer imported (tache_3_module.detect_clusters
        # is the name resolved at call-time — patch the module's binding).
        with patch.object(tache_3_module, "detect_clusters", fake_detect_clusters):
            result = asyncio.run(
                tache_3_module.analyze_tache_3(
                    transcript="Hier j'ai mangé une pomme c'était bon.",
                    topic="Une expérience récente",
                    target_level="B1",
                    ui_language="en",
                    low_confidence_words=[],
                    exam_profile="tcf_canada",
                    tache_3_prompt="Racontez une expérience récente.",
                    db=db,
                )
            )
    finally:
        app_settings.ANTHROPIC_API_KEY = saved_key
        db.close()

    check("analyze_tache_3 returns dict", isinstance(result, dict))
    check("result has cluster_findings_payload key",
          "cluster_findings_payload" in result)
    payload_in_result = result.get("cluster_findings_payload")
    check("cluster_findings_payload is a DetectionPayload",
          isinstance(payload_in_result, DetectionPayload),
          type(payload_in_result).__name__)
    if isinstance(payload_in_result, DetectionPayload):
        check("payload has 2 findings (canned)",
              len(payload_in_result.cluster_findings) == 2,
              str(len(payload_in_result.cluster_findings)))
        slugs = {f.cluster_slug for f in payload_in_result.cluster_findings}
        check("payload findings reference B1.1.C1 + B1.1.C2",
              slugs == {"B1.1.C1", "B1.1.C2"}, str(slugs))
        check("payload model = 'canned-test-model'",
              payload_in_result.model == "canned-test-model",
              payload_in_result.model or "")


def cleanup() -> None:
    print("\nCleanup")
    db = SessionLocal()
    try:
        u = db.query(User).filter_by(email="smoke@p200.local").first()
        if u:
            db.query(UserClusterEvent).filter_by(user_id=u.id).delete()
            db.query(UserClusterStatus).filter_by(user_id=u.id).delete()
            db.query(Recording).filter_by(user_id=u.id).delete()
            db.delete(u)
            db.commit()
            print("  test rows removed")
    finally:
        db.close()


def main() -> int:
    # Force UTF-8 stdout so the arrow + accented French in test output
    # render on Windows consoles (default cp1252 chokes on them).
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    try:
        step_1_schema()
        step_2_pydantic()
        step_3_format_rubrics()
        step_4_filter_placeholders()
        step_5_best_effort()
        step_6_no_api_key()
        step_7_persistence()
        step_8_check_constraint()
        step_9_analyzer_wiring()
    finally:
        cleanup()

    print()
    if errors:
        print(f"FAILURES ({len(errors)}): {errors}")
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
