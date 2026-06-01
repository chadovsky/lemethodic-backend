# F-088 — TCF criteria display labels for the 4 couches.
#
# Backend dimensions (the internal pedagogical names used in models,
# scoring, and the LLM analysis contract) are unchanged. This module is
# a thin label layer applied at the API serialization boundary so the
# FluentPath frontend can read TCF criteria names while internal tools
# (admin dashboard, analytics) keep showing the pedagogical names.
#
# Honesty flag (see DECISIONS.md, 2026-04-27): "Réflexes Anglais →
# Aisance" is correlated but not faithful. The proper backend refactor
# with a true Aisance dimension based on F-038 fluency signals is
# deferred to F-090 (post-launch).

from __future__ import annotations

# Locked order: Étendue, Cohérence, Correction, Aisance, Voix — matches
# the internal couche order le_fond → les_moules_des_idees → les_moules →
# les_reflexes_anglais → la_voix. V-009.be (2026-06-01) adds la_voix as
# couche 5. Legacy Feedback rows without a la_voix score return 0 via the
# scores dict default in couches_array(); frontend renders this as 0/5.
COUCHE_ORDER: tuple[str, ...] = (
    "le_fond",
    "les_moules_des_idees",
    "les_moules",
    "les_reflexes_anglais",
    "la_voix",
)

# Display labels across en/fr/es. TCF uses the same French words across
# language tracks; la_voix student label follows the V-009 lock (2026-05-05).
COUCHE_DISPLAY_LABELS: dict[str, dict[str, str]] = {
    "le_fond":              {"en": "Étendue",   "fr": "Étendue"},
    "les_moules_des_idees": {"en": "Cohérence", "fr": "Cohérence"},
    "les_moules":           {"en": "Correction", "fr": "Correction"},
    "les_reflexes_anglais": {"en": "Aisance",   "fr": "Aisance"},
    "la_voix":              {"en": "Voix",      "fr": "Voix"},
}


def couches_array(scores: dict[str, float | int]) -> list[dict]:
    """Serialize a ``{<couche-internal-name>: score}`` mapping into the
    F-088 array shape: ``[{key, display_label_en, display_label_fr,
    score}, ...]``.

    Order follows COUCHE_ORDER. Missing scores default to 0 — keeps the
    response schema stable when a legacy row is missing a column.
    """
    return [
        {
            "key": key,
            "display_label_en": COUCHE_DISPLAY_LABELS[key]["en"],
            "display_label_fr": COUCHE_DISPLAY_LABELS[key]["fr"],
            "score": scores.get(key, 0) or 0,
        }
        for key in COUCHE_ORDER
    ]
