"""Smoke test for P-240 today's-recommended-action service + endpoint.

Coverage (per the 2026-05-02 plan-first lock-in):
  Step 1 — Schema imports: TodayActionResponse + ActionBlock + ContextBlock
           + Kind/ReasonCode enums register correctly
  Step 2 — Rule chain (6 cases, one per rule):
           (1) regression       — fail on absorbed cluster wins
           (2) needs_revisit    — without a fail in play
           (3) in_progress      — without higher-priority signals
           (4) next_in_path     — fresh user, first cluster in path
           (5) free_practice    — all clusters absorbed (path complete)
           (6) no_path          — no active enrollment
  Step 3 — Endpoint contract: GET /api/users/me/today — 200 + shape
  Step 4 — extra="forbid" enforcement on response schemas

Runs offline (no Claude API). Creates a single throwaway user
(`smoke@p240.local`); cleans up at the end.

Run: python -m scripts.smoke_p240
"""
from __future__ import annotations

import sys

from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import text

from app.database import SessionLocal
from app.models.models import (
    Cluster,
    PathCluster,
    Phase,
    Recording,
    User,
    UserClusterStatus,
    UserPathEnrollment,
)
from app.schemas.today import (
    ActionBlock,
    ContextBlock,
    TodayActionResponse,
)
from app.services.auth import create_access_token, hash_password
from app.services.recommendation import (
    _ordered_path_clusters,
    _pick_cluster,
    _statuses_by_cluster_id,
    compute_today_action,
)


SMOKE_EMAIL = "smoke@p240.local"

errors: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    extra = f" -- {detail}" if detail else ""
    print(f"  [{status}] {name}{extra}")
    if not ok:
        errors.append(name)


# ── Step 1: schema ─────────────────────────────────────────────


def step_1_schema() -> None:
    print("\nStep 1: schemas import + expected fields")
    afields = ActionBlock.model_fields
    check("ActionBlock has kind", "kind" in afields)
    check("ActionBlock has cluster_id/slug/tache/practice_prompt/reason_code",
          {"cluster_id", "cluster_slug", "tache_application",
           "practice_prompt", "reason_code"}.issubset(set(afields.keys())))

    cfields = ContextBlock.model_fields
    check("ContextBlock has 4 fields",
          set(cfields.keys()) == {
              "current_phase_id", "current_phase_position",
              "clusters_remaining_in_path", "last_recording_at",
          },
          str(set(cfields.keys())))

    rfields = TodayActionResponse.model_fields
    check("TodayActionResponse has action/context/dialogue_box",
          set(rfields.keys()) == {"action", "context", "dialogue_box"},
          str(set(rfields.keys())))


# ── Helpers ────────────────────────────────────────────────────


def _ensure_user(db) -> User:
    u = db.query(User).filter_by(email=SMOKE_EMAIL).first()
    if u is None:
        u = User(
            email=SMOKE_EMAIL,
            hashed_password=hash_password("smoke"),
            full_name="P-240 Smoke",
        )
        db.add(u)
        db.commit()
        db.refresh(u)
    return u


def _wipe_user_state(db, user_id: int) -> None:
    db.query(UserClusterStatus).filter_by(user_id=user_id).delete()
    db.query(UserPathEnrollment).filter_by(user_id=user_id).delete()
    db.query(Recording).filter_by(user_id=user_id).delete()
    db.commit()


def _seed_enrollment(db, user_id: int) -> UserPathEnrollment:
    path_row = db.execute(text("SELECT id FROM paths WHERE slug='b1_to_b2'")).first()
    if path_row is None:
        raise RuntimeError("smoke_p240: b1_to_b2 path missing — run ingest_b1_b2_cluster_content first")
    en = UserPathEnrollment(
        user_id=user_id,
        path_id=path_row[0],
        enrolled_at_level="b1",
        enrolled_at_confidence="medium",
        is_active=True,
    )
    db.add(en)
    db.commit()
    db.refresh(en)
    return en


def _set_status(
    db, user_id: int, cluster_id: int,
    status: str, last_detection_result: str | None = None,
) -> None:
    """Upsert helper for UserClusterStatus rows in the smoke."""
    existing = (
        db.query(UserClusterStatus)
        .filter_by(user_id=user_id, cluster_id=cluster_id)
        .first()
    )
    if existing is None:
        db.add(UserClusterStatus(
            user_id=user_id,
            cluster_id=cluster_id,
            status=status,
            last_detection_result=last_detection_result,
        ))
    else:
        existing.status = status
        existing.last_detection_result = last_detection_result
    db.commit()


# ── Step 2: rule chain ─────────────────────────────────────────


def step_2_rule_chain() -> None:
    print("\nStep 2: rule-chain — 6 cases")
    db = SessionLocal()
    try:
        u = _ensure_user(db)
        _wipe_user_state(db, u.id)

        # (6) no_path — no enrollment
        out = compute_today_action(db, u)
        check("(6) no enrollment → kind=no_path",
              out["action"]["kind"] == "no_path", str(out["action"]["kind"]))
        check("(6) reason_code=no_path",
              out["action"]["reason_code"] == "no_path")

        # Set up enrollment for the remaining cases
        en = _seed_enrollment(db, u.id)
        ordered = _ordered_path_clusters(db, en.path_id)
        check("path has clusters", len(ordered) > 0, f"len={len(ordered)}")
        if len(ordered) < 4:
            check("path has >=4 clusters for rule isolation", False,
                  f"only {len(ordered)} — cannot isolate rules")
            return
        first_cluster = ordered[0][2]
        second_cluster = ordered[1][2]
        third_cluster = ordered[2][2]
        fourth_cluster = ordered[3][2]

        # (4) next_in_path — fresh enrollment, no statuses → first cluster
        out = compute_today_action(db, u)
        check("(4) fresh enrollment → kind=cluster_practice",
              out["action"]["kind"] == "cluster_practice", str(out["action"]["kind"]))
        check("(4) reason_code=next_in_path",
              out["action"]["reason_code"] == "next_in_path",
              str(out["action"]["reason_code"]))
        check("(4) cluster_id matches first in path",
              out["action"]["cluster_id"] == first_cluster.id,
              f"got {out['action']['cluster_id']} expected {first_cluster.id}")

        # (3) in_progress on second cluster (with first absorbed) → second
        _set_status(db, u.id, first_cluster.id, "absorbed", "clean")
        _set_status(db, u.id, second_cluster.id, "in_progress", "wobble")
        out = compute_today_action(db, u)
        check("(3) in_progress wins over next_in_path",
              out["action"]["reason_code"] == "in_progress",
              str(out["action"]["reason_code"]))
        check("(3) cluster_id = second_cluster",
              out["action"]["cluster_id"] == second_cluster.id)

        # (2) needs_revisit on third (with first absorbed, second absorbed)
        # → third (and beats remaining "next_in_path" candidates).
        _set_status(db, u.id, second_cluster.id, "absorbed", "clean")
        _set_status(db, u.id, third_cluster.id, "needs_revisit", "wobble")
        out = compute_today_action(db, u)
        check("(2) needs_revisit wins",
              out["action"]["reason_code"] == "needs_revisit",
              str(out["action"]["reason_code"]))
        check("(2) cluster_id = third_cluster",
              out["action"]["cluster_id"] == third_cluster.id)

        # (1) regression — first_cluster absorbed AND last fail
        # Should beat needs_revisit on third and route back to first.
        _set_status(db, u.id, first_cluster.id, "absorbed", "fail")
        out = compute_today_action(db, u)
        check("(1) regression on absorbed cluster wins over needs_revisit",
              out["action"]["reason_code"] == "regression",
              str(out["action"]["reason_code"]))
        check("(1) cluster_id = first_cluster (the regressed one)",
              out["action"]["cluster_id"] == first_cluster.id,
              f"got {out['action']['cluster_id']} expected {first_cluster.id}")
        check("(1) phase_id populated",
              out["context"]["current_phase_id"] is not None)

        # (5) free_practice — wipe all and set every cluster absorbed/clean
        db.query(UserClusterStatus).filter_by(user_id=u.id).delete()
        db.commit()
        for _phase, _pc, cl in ordered:
            _set_status(db, u.id, cl.id, "absorbed", "clean")
        out = compute_today_action(db, u)
        check("(5) all absorbed → kind=free_practice",
              out["action"]["kind"] == "free_practice",
              str(out["action"]["kind"]))
        check("(5) reason_code=free_practice",
              out["action"]["reason_code"] == "free_practice")
        check("(5) cluster_id is None",
              out["action"]["cluster_id"] is None)
        check("(5) clusters_remaining = 0",
              out["context"]["clusters_remaining_in_path"] == 0,
              str(out["context"]["clusters_remaining_in_path"]))

        # _pick_cluster directly — sanity check the helper for P-241 reuse
        statuses = _statuses_by_cluster_id(db, u.id)
        cluster, phase, reason = _pick_cluster(ordered, statuses)
        check("_pick_cluster returns (None, None, free_practice) on path complete",
              cluster is None and phase is None and reason == "free_practice")
    finally:
        db.close()


# ── Step 3: endpoint contract ──────────────────────────────────


def step_3_endpoint() -> None:
    print("\nStep 3: GET /api/users/me/today — endpoint contract")
    from main import app
    client = TestClient(app)

    db = SessionLocal()
    try:
        u = _ensure_user(db)
        # Reset to a clean enrollment + first-recording-pending state
        _wipe_user_state(db, u.id)
        _seed_enrollment(db, u.id)
        token = create_access_token({"sub": u.email})
    finally:
        db.close()
    auth = {"Authorization": f"Bearer {token}"}

    r = client.get("/api/users/me/today", headers=auth)
    check("200 OK", r.status_code == 200, str(r.status_code))
    body = r.json()
    check("body has action/context/dialogue_box",
          set(body.keys()) == {"action", "context", "dialogue_box"},
          str(set(body.keys())))
    check("dialogue_box null in P-240",
          body.get("dialogue_box") is None)
    check("action.kind = cluster_practice",
          body["action"]["kind"] == "cluster_practice",
          str(body["action"]["kind"]))
    check("action.reason_code = next_in_path",
          body["action"]["reason_code"] == "next_in_path",
          str(body["action"]["reason_code"]))
    check("action.cluster_id is int",
          isinstance(body["action"]["cluster_id"], int))
    check("action.tache_application is one of T1/T2/T3",
          body["action"]["tache_application"] in {"tache_1", "tache_2", "tache_3"},
          str(body["action"]["tache_application"]))
    check("context.clusters_remaining_in_path > 0",
          body["context"]["clusters_remaining_in_path"] > 0)

    # Unauthenticated → 401
    r2 = client.get("/api/users/me/today")
    check("unauth → 401", r2.status_code == 401, str(r2.status_code))


# ── Step 4: extra="forbid" enforcement ─────────────────────────


def step_4_forbid_extra() -> None:
    print("\nStep 4: extra='forbid' enforcement on response schemas")
    base = {
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
            "last_recording_at": None,
        },
        "dialogue_box": None,
    }
    try:
        TodayActionResponse(**base)
        check("valid input parses", True)
    except ValidationError as e:
        check("valid input parses", False, str(e))

    try:
        TodayActionResponse(**base, surprise="bad")
        check("extra top-level field rejected", False, "no ValidationError")
    except ValidationError:
        check("extra top-level field rejected", True)

    try:
        bad = {**base, "action": {**base["action"], "kind": "lol"}}
        TodayActionResponse(**bad)
        check("invalid kind rejected", False, "no ValidationError")
    except ValidationError:
        check("invalid kind rejected", True)

    try:
        bad = {**base, "action": {**base["action"], "reason_code": "wat"}}
        TodayActionResponse(**bad)
        check("invalid reason_code rejected", False, "no ValidationError")
    except ValidationError:
        check("invalid reason_code rejected", True)

    try:
        bad = {**base, "action": {**base["action"], "tache_application": "tache_4"}}
        TodayActionResponse(**bad)
        check("invalid tache_application rejected", False, "no ValidationError")
    except ValidationError:
        check("invalid tache_application rejected", True)


# ── Cleanup ────────────────────────────────────────────────────


def cleanup() -> None:
    print("\nCleanup")
    db = SessionLocal()
    try:
        u = db.query(User).filter_by(email=SMOKE_EMAIL).first()
        if u:
            _wipe_user_state(db, u.id)
            db.delete(u)
            db.commit()
            print("  test rows removed")
    finally:
        db.close()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        step_1_schema()
        step_2_rule_chain()
        step_3_endpoint()
        step_4_forbid_extra()
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
