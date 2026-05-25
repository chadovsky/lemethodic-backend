"""F-221 v3 — unit tests for OnboardingSubmitRequest schema validators.

Covers the new q0_specific_intended_exam + q0_accept_fallback fields and
the _specific_intended_exam_required_for_another_exam validator.

Pure Pydantic tests — no DB, no HTTP client, no fixtures. Fast and
isolated. Runs inside the same pytest suite via ``pytest tests/``.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.onboarding import OnboardingSubmitRequest


# ---------------------------------------------------------------------------
# Minimal valid payload factory
# ---------------------------------------------------------------------------

def _base_payload(**overrides) -> dict:
    """Return a minimal valid OnboardingSubmitRequest payload dict.

    Supplies every required field with sensible defaults so individual
    tests only need to override the field(s) under test.
    """
    payload = {
        "q0_target_exam": "tcf_canada",
        "q1_current_level": "b1",
        "q2_target_level": "b2",
        "q3_no_exam_scheduled": True,  # XOR: no exam date
        "q7_hours_per_week": "2_to_5",
        "q9_native_language": "english",
        "q10_prior_exam_history": "never",
        "q11_feedback_mode": "calm",
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# another_exam → q0_specific_intended_exam required
# ---------------------------------------------------------------------------

def test_another_exam_requires_specific_intended_exam_missing():
    """another_exam + q0_specific_intended_exam absent → ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        OnboardingSubmitRequest(**_base_payload(
            q0_target_exam="another_exam",
            # q0_specific_intended_exam omitted — should default to None
        ))
    errors = exc_info.value.errors()
    assert any(
        "q0_specific_intended_exam" in str(e["msg"]) or
        "q0_specific_intended_exam" in str(e.get("loc", ""))
        for e in errors
    ), f"Expected q0_specific_intended_exam error, got: {errors}"


def test_another_exam_requires_specific_intended_exam_none():
    """another_exam + q0_specific_intended_exam=None → ValidationError."""
    with pytest.raises(ValidationError):
        OnboardingSubmitRequest(**_base_payload(
            q0_target_exam="another_exam",
            q0_specific_intended_exam=None,
        ))


def test_another_exam_requires_specific_intended_exam_empty_string():
    """another_exam + q0_specific_intended_exam='' → ValidationError."""
    with pytest.raises(ValidationError):
        OnboardingSubmitRequest(**_base_payload(
            q0_target_exam="another_exam",
            q0_specific_intended_exam="",
        ))


def test_another_exam_requires_specific_intended_exam_whitespace_only():
    """another_exam + q0_specific_intended_exam='   ' → ValidationError.

    Whitespace-only strings are treated as absent; they would produce
    meaningless roadmap data.
    """
    with pytest.raises(ValidationError):
        OnboardingSubmitRequest(**_base_payload(
            q0_target_exam="another_exam",
            q0_specific_intended_exam="   ",
        ))


def test_another_exam_with_valid_specific_intended_exam_passes():
    """another_exam + valid non-empty string → no ValidationError."""
    req = OnboardingSubmitRequest(**_base_payload(
        q0_target_exam="another_exam",
        q0_specific_intended_exam="DALF C1",
    ))
    assert req.q0_target_exam == "another_exam"
    assert req.q0_specific_intended_exam == "DALF C1"


def test_another_exam_with_whitespace_padded_name_passes():
    """another_exam + '  FIDE  ' → passes (strip check is for empty-after-strip)."""
    req = OnboardingSubmitRequest(**_base_payload(
        q0_target_exam="another_exam",
        q0_specific_intended_exam="  FIDE  ",
    ))
    assert req.q0_specific_intended_exam == "  FIDE  "


# ---------------------------------------------------------------------------
# Non-another_exam → q0_specific_intended_exam not required
# ---------------------------------------------------------------------------

def test_tcf_canada_without_specific_intended_exam_passes():
    """Active exam slug + no q0_specific_intended_exam → no ValidationError."""
    req = OnboardingSubmitRequest(**_base_payload(
        q0_target_exam="tcf_canada",
    ))
    assert req.q0_specific_intended_exam is None


def test_tef_canada_without_specific_intended_exam_passes():
    req = OnboardingSubmitRequest(**_base_payload(
        q0_target_exam="tef_canada",
    ))
    assert req.q0_specific_intended_exam is None


def test_not_sure_without_specific_intended_exam_passes():
    req = OnboardingSubmitRequest(**_base_payload(
        q0_target_exam="not_sure",
    ))
    assert req.q0_specific_intended_exam is None


# ---------------------------------------------------------------------------
# q0_accept_fallback — default and explicit values
# ---------------------------------------------------------------------------

def test_accept_fallback_defaults_to_false():
    """q0_accept_fallback defaults to False when not provided."""
    req = OnboardingSubmitRequest(**_base_payload(
        q0_target_exam="another_exam",
        q0_specific_intended_exam="AP French",
    ))
    assert req.q0_accept_fallback is False


def test_accept_fallback_can_be_set_true():
    """q0_accept_fallback=True is accepted."""
    req = OnboardingSubmitRequest(**_base_payload(
        q0_target_exam="another_exam",
        q0_specific_intended_exam="AP French",
        q0_accept_fallback=True,
    ))
    assert req.q0_accept_fallback is True


def test_accept_fallback_on_active_exam_is_silently_ignored():
    """q0_accept_fallback=True on an active exam is accepted by the schema.

    The router silently ignores the flag for active exams (they don't
    enter the waitlist branch). The schema does not reject it — there
    is no reason to be strict here.
    """
    req = OnboardingSubmitRequest(**_base_payload(
        q0_target_exam="tcf_canada",
        q0_accept_fallback=True,
    ))
    assert req.q0_accept_fallback is True


# ---------------------------------------------------------------------------
# Regression: existing validators still fire
# ---------------------------------------------------------------------------

def test_exam_date_xor_no_exam_still_enforced():
    """Pre-existing XOR validator still raises when both fields are absent."""
    with pytest.raises(ValidationError):
        OnboardingSubmitRequest(**{
            "q0_target_exam": "tcf_canada",
            "q1_current_level": "b1",
            "q2_target_level": "b2",
            # neither q3_exam_date nor q3_no_exam_scheduled=True
            "q7_hours_per_week": "2_to_5",
            "q9_native_language": "english",
            "q10_prior_exam_history": "never",
            "q11_feedback_mode": "calm",
        })
