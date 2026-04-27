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

# Locked order: Étendue, Cohérence, Correction, Aisance — matches the
# internal couche order le_fond → les_moules_des_idees → les_moules →
# les_reflexes_anglais. Frontend consumers can re-sort (the diagnostic
# page sorts worst-first to surface the bottleneck); this is the
# canonical authoring order.
COUCHE_ORDER: tuple[str, ...] = (
    "le_fond",
    "les_moules_des_idees",
    "les_moules",
    "les_reflexes_anglais",
)

# Display labels are identical across en/fr/es — TCF uses the same
# French words across language tracks. Kept as separate keys anyway so
# a future divergence (e.g. a market-specific localization) doesn't
# need a schema change.
COUCHE_DISPLAY_LABELS: dict[str, dict[str, str]] = {
    "le_fond":              {"en": "Étendue",   "fr": "Étendue"},
    "les_moules_des_idees": {"en": "Cohérence", "fr": "Cohérence"},
    "les_moules":           {"en": "Correction", "fr": "Correction"},
    "les_reflexes_anglais": {"en": "Aisance",   "fr": "Aisance"},
}


def couches_array(scores: dict[str, float | int]) -> list[dict]:
    """Serialize a {internal_key: score} dict into the F-088 array shape:
    [{internal_key, display_label_en, display_label_fr, score}, ...].

    Order follows COUCHE_ORDER. Missing scores default to 0 — keeps the
    response schema stable when a legacy row is missing a column.
    """
    return [
        {
            "internal_key": key,
            "display_label_en": COUCHE_DISPLAY_LABELS[key]["en"],
            "display_label_fr": COUCHE_DISPLAY_LABELS[key]["fr"],
            "score": scores.get(key, 0) or 0,
        }
        for key in COUCHE_ORDER
    ]
