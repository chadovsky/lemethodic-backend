"""F-047 — Per-Tâche scoring profiles.

Each mode of the TCF Expression Orale exam weights the 4 couches + fluency
differently. Tâche 3 (argumentative monologue) lives and dies on discourse
structure. Tâche 2 (role-play) rewards rhetorical shape of questions.
Tâche 1 (self-presentation) is lighter on structure, heavier on
sentence-level accuracy.

These weight sets are PLACEHOLDERS. Chadi calibrates them during sprint
week 1 day 7 against real student recordings. Do not tune them now — the
point of this module is to give the calibration a single place to land.

Legacy mode keeps equal 4-couche weights with fluency=0 so that recordings
predating F-038 don't gain a phantom fluency contribution.
"""
from __future__ import annotations

# Allowed tache_mode values. Kept here (not in models.py) so the router and
# analysis dispatcher can validate without pulling the ORM.
ALLOWED_TACHE_MODES: tuple[str, ...] = (
    "tache_1",
    "tache_2",
    "tache_3",
    "writing",
    "legacy",
)


SCORING_PROFILES: dict[str, dict[str, float]] = {
    "tache_1": {
        # Tâche 1 = self-presentation + examiner interaction.
        # CHADI: calibrate during sprint week 1 day 7
        "le_fond": 0.20,
        "les_moules_des_idees": 0.15,
        "les_moules": 0.25,
        "les_reflexes_anglais": 0.20,
        "fluency": 0.20,
    },
    "tache_2": {
        # Tâche 2 = role-play information exchange.
        # Rhetorical structure of questions matters.
        # CHADI: calibrate during sprint week 1 day 7
        "le_fond": 0.15,
        "les_moules_des_idees": 0.25,
        "les_moules": 0.20,
        "les_reflexes_anglais": 0.20,
        "fluency": 0.20,
    },
    "tache_3": {
        # Tâche 3 = argumentative monologue.
        # Discourse structure is the whole point.
        # CHADI: calibrate during sprint week 1 day 7
        "le_fond": 0.25,
        "les_moules_des_idees": 0.30,
        "les_moules": 0.20,
        "les_reflexes_anglais": 0.15,
        "fluency": 0.10,
    },
    "legacy": {
        # Equal-ish 4-couche weights with fluency=0 so legacy rows don't
        # retroactively change. Do not edit.
        # CHADI: calibrate during sprint week 1 day 7  (intentional no-op —
        # legacy weights are frozen by contract; see F-047 ticket)
        "le_fond": 0.25,
        "les_moules_des_idees": 0.25,
        "les_moules": 0.25,
        "les_reflexes_anglais": 0.25,
        "fluency": 0.0,
    },
    # Writing never runs through this path; included so the validator has a
    # complete map. Callers should not read these weights for writing — the
    # writing analysis engine owns its own scoring.
    "writing": {
        "le_fond": 0.0,
        "les_moules_des_idees": 0.0,
        "les_moules": 0.0,
        "les_reflexes_anglais": 0.0,
        "fluency": 0.0,
    },
}


def is_valid_mode(mode: str) -> bool:
    return mode in ALLOWED_TACHE_MODES


def get_profile(mode: str) -> dict[str, float]:
    """Return the weight dict for ``mode``. Unknown modes raise KeyError
    — callers should validate via ``is_valid_mode`` first."""
    return SCORING_PROFILES[mode]


def compute_weighted_note_globale(
    mode: str,
    carte: dict | None,
    fluency_score: float | None,
) -> float:
    """Weighted /20 overall from couche scores (each /5) + fluency (/20).

    Couche scores are normalised to /20 (×4) so they share a scale with
    fluency before the weighted sum. Missing layers contribute 0.
    Returns the current LLM-reported value unchanged for unknown modes so
    the caller never breaks on bad input — paired with ``is_valid_mode``
    at the validation boundary, this never fires in practice.
    """
    weights = SCORING_PROFILES.get(mode)
    if not weights:
        return 0.0

    carte = carte or {}

    def _as_float(v) -> float:
        try:
            return float(v or 0)
        except (TypeError, ValueError):
            return 0.0

    values_on_20: dict[str, float] = {
        "le_fond": _as_float(carte.get("le_fond")) * 4,
        "les_moules_des_idees": _as_float(carte.get("les_moules_des_idees")) * 4,
        "les_moules": _as_float(carte.get("les_moules")) * 4,
        "les_reflexes_anglais": _as_float(carte.get("les_reflexes_anglais")) * 4,
        "fluency": _as_float(fluency_score),
    }

    total = sum(weights[k] * values_on_20[k] for k in values_on_20)
    # Clamp to [0, 20] and round to 1 decimal — matches existing
    # note_globale format in the DB.
    clamped = max(0.0, min(20.0, total))
    return round(clamped, 1)
