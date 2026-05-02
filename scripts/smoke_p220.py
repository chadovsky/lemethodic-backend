"""Smoke test for P-220 onboarding-questionnaire schema + endpoints.

Verifies:
1. Migration applied (8 new columns + 7 CHECK constraints exist on prod tables).
2. CHECK constraints reject invalid values for each enum column.
3. CHECK constraint rejects topics_tested_on as non-array AND with bad slugs.
4. ORM round-trip on User new fields + UserPathEnrollment.persona.
5. Routing service: derive_persona buckets + resolve_path_slug coverage +
   derive_capacity_warning fires/skips correctly.
6. Pydantic OnboardingSubmitRequest accepts a valid payload + rejects the
   3 invariant-breaking shapes (exam-date XOR no-exam, "other" without
   freetext, extra fields).
7. POST /onboarding/submit end-to-end (TestClient): valid payload writes
   user fields, creates enrollment with right persona; waitlist branch
   for inactive paths; capacity_warning populated when conditions met.
8. GET /onboarding/questions returns 11 questions with FR + EN copy.
9. Old POST /api/users/onboarding still works AND emits Deprecation header.

Run: python -m scripts.smoke_p220
"""
from __future__ import annotations

import datetime
import sys
from datetime import date, timedelta

from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal, engine
from app.models.models import (
    Path as PathModel,
    User,
    UserPathEnrollment,
)
from app.schemas.onboarding import OnboardingSubmitRequest
from app.services.auth import create_access_token, hash_password
from app.services.onboarding_router import (
    derive_capacity_warning,
    derive_persona,
    is_path_active,
    resolve_path_slug,
)


errors: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    extra = f" -- {detail}" if detail else ""
    print(f"  [{status}] {name}{extra}")
    if not ok:
        errors.append(name)


# ── Step 1: schema ────────────────────────────────────────────────


def step_1_schema() -> None:
    print("\nStep 1: new columns + CHECK constraints exist")
    with engine.connect() as c:
        # New columns on users
        cols = {
            r[0]
            for r in c.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name='users'"
                )
            ).fetchall()
        }
    expected_user_cols = {
        "strongest_skill", "weakest_skill", "hours_per_week",
        "topics_tested_on", "native_language", "prior_french_exam",
        "feedback_mode_preference",
    }
    check("7 new user columns", expected_user_cols.issubset(cols),
          f"missing: {expected_user_cols - cols}" if expected_user_cols - cols else "")

    with engine.connect() as c:
        ucols = {
            r[0]
            for r in c.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema='public' "
                    "AND table_name='user_path_enrollments'"
                )
            ).fetchall()
        }
    check("user_path_enrollments.persona present", "persona" in ucols)

    with engine.connect() as c:
        constraints = {
            r[0]
            for r in c.execute(
                text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE conname LIKE 'ck_users_%' "
                    "OR conname = 'ck_user_path_enrollments_persona'"
                )
            ).fetchall()
        }
    expected_checks = {
        "ck_users_strongest_skill", "ck_users_weakest_skill",
        "ck_users_hours_per_week", "ck_users_prior_french_exam",
        "ck_users_feedback_mode_preference", "ck_users_topics_tested_on",
        "ck_user_path_enrollments_persona",
    }
    check("7 CHECK constraints exist", expected_checks.issubset(constraints),
          f"missing: {expected_checks - constraints}" if expected_checks - constraints else "")


# ── Step 2: CHECK rejection cases ─────────────────────────────────


def step_2_check_rejections() -> None:
    print("\nStep 2: CHECK constraints reject invalid values")
    db = SessionLocal()
    user = db.query(User).filter_by(email="smoke@p220.local").first()
    if user is None:
        user = User(
            email="smoke@p220.local",
            hashed_password=hash_password("smoke"),
            full_name="P-220 Smoke",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    db.close()

    cases = [
        ("strongest_skill",          "wrong_value",                   "ck_users_strongest_skill"),
        ("weakest_skill",            "speaking",                      "ck_users_weakest_skill"),  # raw skill, not blocker
        ("hours_per_week",           "<2",                            "ck_users_hours_per_week"),  # display label, not slug
        ("prior_french_exam",        "yesterday",                     "ck_users_prior_french_exam"),
        ("feedback_mode_preference", "verbose",                       "ck_users_feedback_mode_preference"),
    ]
    for col, bad_val, expected_constraint in cases:
        d = SessionLocal()
        try:
            d.execute(
                text(f"UPDATE users SET {col}=:v WHERE id=:i"),
                {"v": bad_val, "i": user.id},
            )
            d.commit()
            check(f"CHECK rejects {col}={bad_val!r}", False, "UPDATE succeeded")
        except IntegrityError as e:
            ok = expected_constraint in str(e.orig)
            check(f"CHECK rejects {col}={bad_val!r}", ok,
                  expected_constraint if ok else f"wrong constraint fired: {e.orig}")
            d.rollback()
        finally:
            d.close()

    # topics_tested_on: bad slug. CAST(... AS jsonb) instead of ::jsonb to
    # avoid clashing with SQLAlchemy's :param syntax.
    d = SessionLocal()
    try:
        d.execute(
            text("UPDATE users SET topics_tested_on=CAST(:v AS jsonb) WHERE id=:i"),
            {"v": '["bad_theme"]', "i": user.id},
        )
        d.commit()
        check("CHECK rejects topics_tested_on=['bad_theme']", False, "UPDATE succeeded")
    except IntegrityError as e:
        check("CHECK rejects topics_tested_on=['bad_theme']",
              "ck_users_topics_tested_on" in str(e.orig))
        d.rollback()
    finally:
        d.close()

    # topics_tested_on: scalar (not array)
    d = SessionLocal()
    try:
        d.execute(
            text("UPDATE users SET topics_tested_on=CAST(:v AS jsonb) WHERE id=:i"),
            {"v": '"societe"', "i": user.id},
        )
        d.commit()
        check("CHECK rejects topics_tested_on as scalar string", False, "UPDATE succeeded")
    except IntegrityError as e:
        check("CHECK rejects topics_tested_on as scalar string",
              "ck_users_topics_tested_on" in str(e.orig))
        d.rollback()
    finally:
        d.close()


# ── Step 3: Pydantic edge cases ───────────────────────────────────


def step_3_pydantic() -> None:
    print("\nStep 3: Pydantic OnboardingSubmitRequest validators")
    valid = {
        "q1_current_level": "b1",
        "q2_target_level": "b2",
        "q3_exam_date": (date.today() + timedelta(days=60)).isoformat(),
        "q3_no_exam_scheduled": False,
        "q4_motivation": "immigration",
        "q5_strongest_skill": "reading",
        "q6_weakest_skill": "speaking_under_pressure",
        "q7_hours_per_week": "5_to_10",
        "q8_topics_tested_on": ["vie_quotidienne", "societe"],
        "q9_native_language": "english",
        "q9_native_language_other": None,
        "q10_prior_exam_history": "never",
        "q11_feedback_mode": "calm",
    }
    OnboardingSubmitRequest.model_validate(valid)
    check("valid payload accepted", True)

    # Both date AND no-exam set
    bad1 = dict(valid, q3_no_exam_scheduled=True)
    try:
        OnboardingSubmitRequest.model_validate(bad1)
        check("rejects exam_date + no_exam=true", False)
    except ValidationError:
        check("rejects exam_date + no_exam=true", True)

    # Neither date NOR no-exam set
    bad2 = dict(valid)
    bad2["q3_exam_date"] = None
    bad2["q3_no_exam_scheduled"] = False
    try:
        OnboardingSubmitRequest.model_validate(bad2)
        check("rejects no exam_date and no_exam=false", False)
    except ValidationError:
        check("rejects no exam_date and no_exam=false", True)

    # other-language without freetext
    bad3 = dict(valid, q9_native_language="other", q9_native_language_other=None)
    try:
        OnboardingSubmitRequest.model_validate(bad3)
        check("rejects q9='other' without freetext", False)
    except ValidationError:
        check("rejects q9='other' without freetext", True)

    # Extra field
    bad4 = dict(valid, mystery_field="x")
    try:
        OnboardingSubmitRequest.model_validate(bad4)
        check("rejects extra unknown field", False)
    except ValidationError:
        check("rejects extra unknown field", True)


# ── Step 4: routing service unit tests ────────────────────────────


def step_4_routing() -> None:
    print("\nStep 4: routing service derivations")

    # resolve_path_slug coverage
    cases_path = {
        ("a2", "b1"): "a2_to_b1",
        ("b1", "b2"): "b1_to_b2",
        ("b2", "c1"): "b2_to_c1",
        ("c1", "c2"): "c1_to_c2",
        ("not_sure", "b2"): "b1_to_b2",     # default
        ("b1", "not_sure"): "b1_to_b2",     # default
    }
    for (cur, tgt), expected_slug in cases_path.items():
        got = resolve_path_slug(cur, tgt)
        check(f"resolve_path_slug({cur},{tgt})={expected_slug}", got == expected_slug, got)

    # is_path_active
    check("b1_to_b2 is active", is_path_active("b1_to_b2"))
    check("a2_to_b1 NOT active", not is_path_active("a2_to_b1"))

    # derive_persona buckets
    today = date.today()
    persona_cases = [
        (today + timedelta(days=14), False, "cram"),
        (today + timedelta(days=42), False, "cram"),
        (today + timedelta(days=43), False, "acceleration"),
        (today + timedelta(days=180), False, "acceleration"),
        (today + timedelta(days=200), False, "foundation"),
        (None, True, "foundation"),
        (None, False, "foundation"),
        (today - timedelta(days=5), False, "foundation"),  # past date degenerate
    ]
    for d, no_exam, expected in persona_cases:
        got = derive_persona(d, no_exam, today=today)
        check(f"derive_persona({d}, no_exam={no_exam})={expected}",
              got == expected, got)

    # capacity warning
    check("capacity_warning fires: <6w + 2_to_5",
          derive_capacity_warning(today + timedelta(days=21), False, "2_to_5",
                                  today=today) is not None)
    check("capacity_warning skips: >6w",
          derive_capacity_warning(today + timedelta(days=90), False, "less_than_2",
                                  today=today) is None)
    check("capacity_warning skips: 5_to_10 hours",
          derive_capacity_warning(today + timedelta(days=14), False, "5_to_10",
                                  today=today) is None)
    check("capacity_warning skips: no_exam",
          derive_capacity_warning(None, True, "less_than_2",
                                  today=today) is None)


# ── Step 5: HTTP endpoints via TestClient ─────────────────────────


def step_5_endpoints() -> None:
    print("\nStep 5: HTTP endpoints via TestClient")
    from main import app
    client = TestClient(app)

    # GET /onboarding/questions — public
    r = client.get("/onboarding/questions")
    check("GET /onboarding/questions 200", r.status_code == 200, str(r.status_code))
    body = r.json()
    check("returns 11 questions", len(body["questions"]) == 11,
          str(len(body["questions"])))
    q1 = body["questions"][0]
    check("q1 slug correct", q1["id"] == "q1_current_level", q1["id"])
    check("q1 has FR + EN heading",
          "fr" in q1["heading"] and "en" in q1["heading"])

    # Mint a JWT for a test user. The "sub" claim is the user's email
    # (see app/services/auth.py:get_current_user line 49).
    db = SessionLocal()
    user = db.query(User).filter_by(email="smoke@p220.local").first()
    user_id = user.id
    user_email = user.email
    db.close()
    token = create_access_token({"sub": user_email})
    auth_headers = {"Authorization": f"Bearer {token}"}

    # POST /onboarding/submit — valid payload, b1_to_b2 active path
    payload_b1b2 = {
        "q1_current_level": "b1",
        "q2_target_level": "b2",
        "q3_exam_date": (date.today() + timedelta(days=60)).isoformat(),
        "q3_no_exam_scheduled": False,
        "q4_motivation": "immigration",
        "q5_strongest_skill": "reading",
        "q6_weakest_skill": "speaking_under_pressure",
        "q7_hours_per_week": "5_to_10",
        "q8_topics_tested_on": ["vie_quotidienne", "societe"],
        "q9_native_language": "english",
        "q9_native_language_other": None,
        "q10_prior_exam_history": "never",
        "q11_feedback_mode": "calm",
    }
    r = client.post("/onboarding/submit", json=payload_b1b2, headers=auth_headers)
    check("POST /onboarding/submit 200", r.status_code == 200,
          f"{r.status_code} {r.text[:200]}")
    body = r.json()
    check("response.path_slug=b1_to_b2", body["path_slug"] == "b1_to_b2",
          body.get("path_slug"))
    check("response.persona=acceleration", body["persona"] == "acceleration",
          body.get("persona"))
    check("redirect_to_diagnostic=true", body["redirect_to_diagnostic"] is True)
    check("waitlist=false", body["waitlist"] is False)
    check("user_path_enrollment_id present", body["user_path_enrollment_id"] is not None)

    # Verify DB side-effects
    db = SessionLocal()
    u = db.query(User).filter_by(id=user_id).first()
    check("User.strongest_skill persisted", u.strongest_skill == "reading")
    check("User.weakest_skill persisted",
          u.weakest_skill == "speaking_under_pressure")
    check("User.hours_per_week persisted", u.hours_per_week == "5_to_10")
    check("User.topics_tested_on persisted",
          u.topics_tested_on == ["vie_quotidienne", "societe"])
    check("User.native_language persisted", u.native_language == "english")
    check("User.feedback_mode_preference persisted",
          u.feedback_mode_preference == "calm")

    enrollment = (
        db.query(UserPathEnrollment)
        .filter(UserPathEnrollment.user_id == user_id,
                UserPathEnrollment.is_active.is_(True))
        .first()
    )
    check("active enrollment created", enrollment is not None)
    if enrollment:
        check("enrollment.persona=acceleration", enrollment.persona == "acceleration",
              enrollment.persona)
    db.close()

    # POST /onboarding/submit — waitlist (B2 -> C1 path, not active)
    payload_waitlist = dict(payload_b1b2,
                            q1_current_level="b2", q2_target_level="c1")
    r = client.post("/onboarding/submit", json=payload_waitlist, headers=auth_headers)
    check("waitlist POST 200", r.status_code == 200, str(r.status_code))
    body = r.json()
    check("waitlist=true", body["waitlist"] is True)
    check("waitlist path_slug=null", body["path_slug"] is None)
    check("waitlist persona=null", body["persona"] is None)
    check("waitlist_reason=path_not_active",
          body.get("waitlist_reason") == "path_not_active")

    # POST /onboarding/submit — capacity warning (3-week exam + low hours)
    payload_warn = dict(payload_b1b2,
                        q3_exam_date=(date.today() + timedelta(days=21)).isoformat(),
                        q7_hours_per_week="less_than_2")
    r = client.post("/onboarding/submit", json=payload_warn, headers=auth_headers)
    check("capacity-warning POST 200", r.status_code == 200, str(r.status_code))
    body = r.json()
    check("capacity_warning populated", body["capacity_warning"] is not None,
          str(body.get("capacity_warning")))
    if body["capacity_warning"]:
        check("warning hours selected = less_than_2",
              body["capacity_warning"]["hours_per_week_selected"] == "less_than_2")
        check("warning recommended = 5_to_10",
              body["capacity_warning"]["recommended_minimum_hours"] == "5_to_10")
    check("persona=cram for 3-week exam", body["persona"] == "cram", body.get("persona"))

    # Old endpoint still works + emits deprecation header
    legacy_payload = {
        "target_level": "B2",
        "exam_profile": "tcf_canada",
        "exam_date": None,
        "goal": "immigration",
        "current_level": "B1",
        "interface_language": "en",
    }
    r = client.post("/api/users/onboarding", json=legacy_payload, headers=auth_headers)
    check("legacy POST /api/users/onboarding still 200", r.status_code == 200,
          str(r.status_code))
    check("legacy emits Deprecation: true",
          r.headers.get("deprecation") == "true",
          r.headers.get("deprecation"))
    check("legacy emits Link rel=successor-version",
          'rel="successor-version"' in (r.headers.get("link") or ""),
          r.headers.get("link"))


# ── Cleanup ───────────────────────────────────────────────────────


def cleanup() -> None:
    db = SessionLocal()
    user = db.query(User).filter_by(email="smoke@p220.local").first()
    if user:
        db.query(UserPathEnrollment).filter_by(user_id=user.id).delete()
        db.delete(user)
        db.commit()
    db.close()


def main() -> int:
    try:
        step_1_schema()
        step_2_check_rejections()
        step_3_pydantic()
        step_4_routing()
        step_5_endpoints()
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
