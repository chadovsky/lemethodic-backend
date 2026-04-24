"""
Exam profile registry.

Add a new profile by:
  1. Creating a module in this package that defines an ExamProfile instance.
  2. Registering it in _PROFILES below.

Callers use get_profile(profile_id) — they never import concrete profiles
directly. analysis.py, writing_analysis.py, and the routers all treat the
returned ExamProfile as opaque data.
"""
from app.services.exam_profiles.base import Criterion, ExamProfile
from app.services.exam_profiles.tcf_canada import TCF_CANADA


_PROFILES: dict[str, ExamProfile] = {
    TCF_CANADA.id: TCF_CANADA,
}

DEFAULT_PROFILE_ID = TCF_CANADA.id


def get_profile(profile_id: str | None = None) -> ExamProfile:
    """Look up an exam profile by id, falling back to the default."""
    if not profile_id:
        return _PROFILES[DEFAULT_PROFILE_ID]
    if profile_id not in _PROFILES:
        return _PROFILES[DEFAULT_PROFILE_ID]
    return _PROFILES[profile_id]


def list_profiles() -> list[dict]:
    """Metadata list for profile-picker UIs."""
    return [
        {"id": p.id, "display_name": p.display_name}
        for p in _PROFILES.values()
    ]


__all__ = [
    "Criterion",
    "ExamProfile",
    "get_profile",
    "list_profiles",
    "DEFAULT_PROFILE_ID",
]
