"""F-BUGS-001-BE-A smoke — Tâche 2 agence_voyages scenario regression canary.

Bug context (resolved 2026-05-13):
    The F-049 seeder (scripts/seed_tache2_scenarios.py) was never run
    against production from launch until 2026-05-13. Result: every
    Tâche 2 conversation start request returned HTTP 404 "Unknown or
    inactive scenario_code". Chadi flagged via FE-side error trace;
    prod query confirmed `tache2_scenarios` was empty (0 rows). Fix:
    `python -m scripts.seed_tache2_scenarios` run via DO console.

This smoke is the regression canary so the next deploy doesn't
silently break the same way. It exercises:

  1. GET /api/conversations/scenarios — agence_voyages MUST appear
     in the response (A2_B1 difficulty, no above-A2 gate required).
  2. POST /api/conversations/start with scenario_code='agence_voyages'
     — MUST return 201/200 with a conversation object, NOT 404.

Runs against the live local docker-compose Postgres via FastAPI
TestClient. Self-cleaning fixture user. NEVER mutates the seeded
scenarios — read-only on tache2_scenarios.

Run from project root:
    python -m scripts.smoke_f_bugs_001_be_a
"""
from __future__ import annotations

import datetime
import sys

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.models import Conversation, ConversationTurn, Tache2Scenario, User
from app.services.jwt_tokens import mint_access_token
from main import app


_USER_EMAIL = "smoke_f_bugs_001_be_a@local"
_TARGET_SCENARIO_CODE = "agence_voyages"
# Mirror of the canonical seed file (scripts/seed_tache2_scenarios.py).
# If a future PR changes the canonical set, update this list so the
# smoke catches drift on the wrong side too.
_EXPECTED_SCENARIOS = {
    "ami_demenagement",
    "agence_voyages",
    "bibliotheque",
    "nouveau_collegue_quebecois",
    "agence_immobiliere_canada",
}
# A2_B1 scenarios that should be visible to any authenticated user
# without the above-A2 gate (which the F-053 stub returns False for).
_EXPECTED_A2_B1_VISIBLE = {
    "ami_demenagement",
    "agence_voyages",
    "bibliotheque",
}


errors: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    extra = f" -- {detail}" if detail else ""
    print(f"  [{status}] {name}{extra}")
    if not ok:
        errors.append(name)


def _cleanup(db: Session) -> None:
    """Drop the fixture user + any conversations the smoke started.
    Tache2Scenario rows are NEVER touched — those are production-
    canonical seed data."""
    user = db.query(User).filter_by(email=_USER_EMAIL).first()
    if user is None:
        return
    conv_ids = [
        c.id for c in db.query(Conversation).filter_by(user_id=user.id).all()
    ]
    if conv_ids:
        db.query(ConversationTurn).filter(
            ConversationTurn.conversation_id.in_(conv_ids)
        ).delete(synchronize_session=False)
        db.query(Conversation).filter(
            Conversation.id.in_(conv_ids)
        ).delete(synchronize_session=False)
    db.query(User).filter_by(email=_USER_EMAIL).delete()
    db.commit()


def main() -> int:
    db = SessionLocal()
    client = TestClient(app)
    try:
        _cleanup(db)

        # Step 0 — sanity check on the seed: tache2_scenarios must
        # contain agence_voyages with is_active=True. If this fails,
        # the local DB itself wasn't seeded — run
        # `python -m scripts.seed_tache2_scenarios` first.
        seed_row = (
            db.query(Tache2Scenario)
            .filter(Tache2Scenario.code == _TARGET_SCENARIO_CODE)
            .first()
        )
        check(
            f"seed row exists for {_TARGET_SCENARIO_CODE}",
            seed_row is not None,
            "run `python -m scripts.seed_tache2_scenarios` first"
            if seed_row is None
            else "",
        )
        if seed_row is not None:
            check(
                f"seed row is_active=True for {_TARGET_SCENARIO_CODE}",
                seed_row.is_active is True,
                f"is_active={seed_row.is_active}",
            )
            check(
                f"seed row difficulty=A2_B1 for {_TARGET_SCENARIO_CODE}",
                seed_row.difficulty == "A2_B1",
                f"difficulty={seed_row.difficulty}",
            )

        # Step 1 — fixture user (verified email so F-310 Phase B gate
        # passes; smoke is not testing auth here).
        user = User(
            email=_USER_EMAIL,
            hashed_password="x",
            full_name="F-BUGS-001-BE-A smoke",
            email_verified_at=datetime.datetime.utcnow(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        headers = {"Authorization": f"Bearer {mint_access_token(_USER_EMAIL)}"}

        # Step 2 — GET /api/conversations/scenarios includes
        # agence_voyages in the visible-to-user list.
        r = client.get("/api/conversations/scenarios", headers=headers)
        check(
            "GET /scenarios returns 200",
            r.status_code == 200,
            f"got {r.status_code}: {r.text[:200]}",
        )
        body = r.json() if r.status_code == 200 else {}
        codes = {s.get("code") for s in body.get("scenarios", [])}
        check(
            f"{_TARGET_SCENARIO_CODE} in /scenarios catalog",
            _TARGET_SCENARIO_CODE in codes,
            f"got codes: {sorted(codes)}",
        )
        check(
            "all A2_B1 scenarios surfaced (no above-A2 gate)",
            _EXPECTED_A2_B1_VISIBLE.issubset(codes),
            f"missing: {sorted(_EXPECTED_A2_B1_VISIBLE - codes)}",
        )

        # Step 3 — POST /api/conversations/start with agence_voyages.
        # Pre-fix: this returned HTTP 404. Post-fix: should return
        # 200 with a conversation object.
        r = client.post(
            "/api/conversations/start",
            headers=headers,
            json={
                "tache_mode": "tache_2",
                "scenario_code": _TARGET_SCENARIO_CODE,
                "target_level": "B2",
                "ui_language": "en",
            },
        )
        check(
            "POST /start with agence_voyages returns 2xx (not 404)",
            200 <= r.status_code < 300,
            f"got {r.status_code}: {r.text[:300]}",
        )
        if 200 <= r.status_code < 300:
            payload = r.json()
            check(
                "/start returns conversation_id",
                bool(payload.get("conversation_id") or payload.get("id")),
                f"got keys: {list(payload.keys())}",
            )
            check(
                "/start echoes tache_mode=tache_2",
                payload.get("tache_mode") == "tache_2",
                f"got tache_mode={payload.get('tache_mode')!r}",
            )

        # Step 4 — POST /start with an UNKNOWN code MUST still 404.
        # This proves the error path is intact; a regression where
        # every code resolves would also be a bug.
        r = client.post(
            "/api/conversations/start",
            headers=headers,
            json={
                "tache_mode": "tache_2",
                "scenario_code": "definitely_not_a_real_scenario_xyz",
                "target_level": "B2",
                "ui_language": "en",
            },
        )
        check(
            "POST /start with unknown code returns 404 (error path intact)",
            r.status_code == 404,
            f"got {r.status_code}",
        )

        print()
        if errors:
            print(f"FAILURES: {errors}")
            return 1
        print("ALL CHECKS PASSED")
        return 0
    finally:
        _cleanup(db)
        db.close()


if __name__ == "__main__":
    sys.exit(main())
