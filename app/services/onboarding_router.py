"""P-220 — onboarding routing logic.

Pure functions: turn answer slugs into a path slug + persona + capacity
signal. No I/O, no DB access.

Phase 1 scope: only Q1 + Q2 (path resolution) and Q3 (persona) drive
routing. Q4-Q10 are stored on User but routing is deferred to P-220.x.
Q11 (feedback_mode) is propagated into the response by the router but
the column is read FE-side; this service treats it as identity.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional


# Phase 1: only b1_to_b2 is is_active=True in the DB.
ACTIVE_PATH_SLUGS = frozenset({"b1_to_b2"})

# Default fallback when the level pair is unresolvable
# ("not_sure" -> b1_to_b2 per Q1 decision).
DEFAULT_PATH_SLUG = "b1_to_b2"

# Persona thresholds (days from today to exam_date).
PERSONA_CRAM_MAX_DAYS = 42         # ~6 weeks
PERSONA_ACCELERATION_MAX_DAYS = 183  # ~6 months

# Capacity warning thresholds.
CAPACITY_WARNING_LOW_HOURS = frozenset({"less_than_2", "2_to_5"})
CAPACITY_WARNING_RECOMMENDED = "5_to_10"


# (current_level, target_level) -> path_slug. "not_sure" handled separately.
_PATH_RESOLUTION = {
    ("a2", "b1"): "a2_to_b1",
    ("a2", "b2"): "a2_to_b1",
    ("a2", "c1"): "a2_to_b1",
    ("a2", "c2"): "a2_to_b1",
    ("b1", "b2"): "b1_to_b2",
    ("b1", "c1"): "b1_to_b2",
    ("b1", "c2"): "b1_to_b2",
    ("b2", "c1"): "b2_to_c1",
    ("b2", "c2"): "b2_to_c1",
    ("c1", "c2"): "c1_to_c2",
}


def resolve_path_slug(current_level: str, target_level: str) -> str:
    """Return path slug for a (current, target) pair.

    Q1 "not_sure" or unknown combinations default to ``b1_to_b2``
    (per the P-220 micro-decision: the standard 3-recording diagnostic
    is the placement mechanism, not a separate "extended" diagnostic).
    """
    if current_level == "not_sure" or target_level == "not_sure":
        return DEFAULT_PATH_SLUG
    return _PATH_RESOLUTION.get((current_level, target_level), DEFAULT_PATH_SLUG)


def is_path_active(path_slug: str) -> bool:
    """Phase 1: only b1_to_b2 is shippable; others route to waitlist UX."""
    return path_slug in ACTIVE_PATH_SLUGS


def should_offer_b1_to_b2_fallback(current_level: str, target_level: str) -> bool:
    """Waitlist screen offers b1_to_b2 fallback only when it's pedagogically
    plausible — start_level is B1 OR target_level is B2 (per copy doc)."""
    return current_level == "b1" or target_level == "b2"


def derive_persona(
    exam_date: Optional[date],
    no_exam_scheduled: bool,
    today: Optional[date] = None,
) -> str:
    """Persona derivation per docs/P-220-onboarding-questionnaire-copy.md Q3:

    - exam_date <= 6 weeks from today -> 'cram'
    - exam_date 6 weeks to 6 months   -> 'acceleration'
    - exam_date > 6 months OR no exam -> 'foundation'

    Past exam_date is treated as 'foundation' (degenerate case; the FE
    date picker enforces min=today, so this only fires for stale records).
    """
    if no_exam_scheduled or exam_date is None:
        return "foundation"
    today = today or date.today()
    delta = (exam_date - today).days
    if delta < 0:
        return "foundation"
    if delta <= PERSONA_CRAM_MAX_DAYS:
        return "cram"
    if delta <= PERSONA_ACCELERATION_MAX_DAYS:
        return "acceleration"
    return "foundation"


def derive_capacity_warning(
    exam_date: Optional[date],
    no_exam_scheduled: bool,
    hours_per_week: str,
    today: Optional[date] = None,
) -> Optional[dict]:
    """Returns dict matching CapacityWarning schema, or None if no warning.

    Triggers only when exam is < 6 weeks AND hours_per_week is in the
    low-capacity bucket. Surfacing tension is helpful; blocking is
    patronizing — the user decides.
    """
    if no_exam_scheduled or exam_date is None:
        return None
    if hours_per_week not in CAPACITY_WARNING_LOW_HOURS:
        return None
    today = today or date.today()
    delta_days = (exam_date - today).days
    if delta_days < 0 or delta_days > PERSONA_CRAM_MAX_DAYS:
        return None
    return {
        "weeks_to_exam": max(0, delta_days // 7),
        "hours_per_week_selected": hours_per_week,
        "recommended_minimum_hours": CAPACITY_WARNING_RECOMMENDED,
    }


def derive_feedback_mode_default(feedback_mode: str) -> str:
    """Identity in Phase 1 — Q11 maps directly to UI mode (calm/method).
    Kept as a function so the indirection layer is in place when FE needs
    server-side default-mode resolution (P-220.x)."""
    return feedback_mode
