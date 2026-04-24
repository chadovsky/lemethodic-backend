"""
Framework-agnostic score-to-level mapping helpers.

Exam profiles may reference these directly or supply their own mapping callables
(e.g. DELF-specific curves, interview-prep rubrics). Nothing in this module is
hardcoded to TCF Canada — profile modules import and wire them up.
"""

_CEFR_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"]

_CEFR_TO_CLB_LOWER_BOUND = {
    "A1": 2,
    "A2": 4,
    "B1": 5,
    "B2": 7,
    "C1": 9,
    "C2": 11,
}

_CEFR_COLORS = {
    "A1 not achieved": "#b91c1c",
    "A1": "#dc2626",
    "A2": "#ea580c",
    "B1": "#ca8a04",
    "B2": "#16a34a",
    "C1": "#2563eb",
    "C2": "#7c3aed",
}


def cefr_from_score(score: float) -> str:
    """Map a /20 score to a CEFR level per TCF Canada thresholds.

    0 → "A1 not achieved", 1 → A1, 2-5 → A2, 6-9 → B1,
    10-13 → B2, 14-17 → C1, 18-20 → C2.
    """
    if score is None:
        return "A1 not achieved"
    s = float(score)
    if s < 1:
        return "A1 not achieved"
    if s < 2:
        return "A1"
    if s < 6:
        return "A2"
    if s < 10:
        return "B1"
    if s < 14:
        return "B2"
    if s < 18:
        return "C1"
    return "C2"


def clb_from_cefr(cefr_level: str) -> int | None:
    """Return the lower-bound CLB level for a CEFR level.

    Used for IRCC immigration minimums — e.g. B2 → CLB 7. Returns None for
    "A1 not achieved" since no CLB equivalent applies.
    """
    if not cefr_level or cefr_level == "A1 not achieved":
        return None
    return _CEFR_TO_CLB_LOWER_BOUND.get(cefr_level)


def cefr_color(level: str) -> str:
    """Hex color for a CEFR level badge."""
    return _CEFR_COLORS.get(level, "#606d85")


def score_color(score: float) -> str:
    """Hex color for a raw /20 score, aligned with CEFR bands."""
    return cefr_color(cefr_from_score(score))
