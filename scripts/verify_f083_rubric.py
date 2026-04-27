"""F-083 verification harness.

Exercises the F-083 pedagogical rubric layer in three passes:

1. Threshold logic (deterministic; no Claude call) — verifies retry
   recommendation fires correctly per Tâche threshold rule.
2. Coercion robustness — feeds malformed payloads through
   ``_coerce_rubric`` and confirms shape stability.
3. Live Claude call (skipped if ANTHROPIC_API_KEY missing) — fires
   ``apply_tache_rubric`` against a short synthetic transcript per
   Tâche, prints the structured response.

Run from project root:
    python -m scripts.verify_f083_rubric
"""
from __future__ import annotations

import asyncio
import json
import os

from app.services.tache_rubric import (
    _coerce_rubric,
    _enforce_threshold,
    apply_tache_rubric,
)


# ═══════════════════════════════════════════════════════════════
# Pass 1 — threshold logic
# ═══════════════════════════════════════════════════════════════

def _t1_strong():
    return [
        {"key": "premiere_impression", "score": 4},
        {"key": "presentation_de_soi", "score": 4},
        {"key": "lexique_identite",    "score": 3},
        {"key": "aisance_hesitations", "score": 3},
        {"key": "prononciation",       "score": 4},
    ]


def _t1_weak():
    return [
        {"key": "premiere_impression", "score": 1},  # below 2 -> trigger
        {"key": "presentation_de_soi", "score": 2},
        {"key": "lexique_identite",    "score": 2},
        {"key": "aisance_hesitations", "score": 2},
        {"key": "prononciation",       "score": 2},
    ]


def _t2_foundation_fail():
    return [
        {"key": "formation_questions",           "score": 2},  # below 2.5 -> trigger
        {"key": "registre_approprie",            "score": 4},
        {"key": "actes_de_parole",               "score": 4},
        {"key": "reactivite",                    "score": 4},
        {"key": "structuration_interactionnelle","score": 4},
    ]


def _t2_strong():
    return [
        {"key": "formation_questions",           "score": 4},
        {"key": "registre_approprie",            "score": 4},
        {"key": "actes_de_parole",               "score": 3},
        {"key": "reactivite",                    "score": 3},
        {"key": "structuration_interactionnelle","score": 3},
    ]


def _t3_no_structure():
    return [
        {"key": "position_claire",          "score": 3},
        {"key": "argumentation_structuree", "score": 1},  # below 2 -> trigger
        {"key": "connecteurs_logiques",     "score": 2},
        {"key": "developpement_thematique", "score": 3},
        {"key": "defense_calme",            "score": 3},
        {"key": "aisance_sous_pression",    "score": 3},
    ]


def _t3_strong():
    return [
        {"key": "position_claire",          "score": 4},
        {"key": "argumentation_structuree", "score": 4},
        {"key": "connecteurs_logiques",     "score": 3},
        {"key": "developpement_thematique", "score": 4},
        {"key": "defense_calme",            "score": 3},
        {"key": "aisance_sous_pression",    "score": 3},
    ]


def pass_1_threshold() -> int:
    cases = [
        ("T1 strong",            "tache_1", _t1_strong(),         False),
        ("T1 weak (dim<2)",      "tache_1", _t1_weak(),           True),
        ("T2 strong",            "tache_2", _t2_strong(),         False),
        ("T2 foundation fail",   "tache_2", _t2_foundation_fail(),True),
        ("T3 strong",            "tache_3", _t3_strong(),         False),
        ("T3 no-structure",      "tache_3", _t3_no_structure(),   True),
    ]
    failures = 0
    print("\n[Pass 1] Threshold logic")
    for label, mode, dims, expected_should_retry in cases:
        result = _enforce_threshold(mode, dims)
        ok = result["should_retry"] == expected_should_retry
        if not ok:
            failures += 1
        marker = "OK " if ok else "FAIL"
        print(f"  {marker}  {label:<24}  should_retry={result['should_retry']}  expected={expected_should_retry}  reason={result['reason']!r}")
    return failures


# ═══════════════════════════════════════════════════════════════
# Pass 2 — coercion robustness
# ═══════════════════════════════════════════════════════════════

def pass_2_coercion() -> int:
    print("\n[Pass 2] Coercion robustness")
    failures = 0

    # Empty input
    out = _coerce_rubric({}, "tache_1")
    assert len(out["tache_specific_dimensions"]) == 5, "T1 should have 5 dimensions"
    assert all(d["score"] == 0 for d in out["tache_specific_dimensions"]), "missing dims should default 0"
    assert set(out["universal_sidebars"].keys()) == {"conjugation", "grammar_structure", "sentence_construction"}
    print("  OK   empty payload -> canonical shape")

    # Garbage types
    out = _coerce_rubric({
        "summary_prose": 123,  # not str
        "tache_specific_dimensions": "not a list",
        "universal_sidebars": "not a dict",
        "retry_recommendation": "not a dict",
        "next_action_suggestion": ["not", "a", "string"],
    }, "tache_2")
    assert len(out["tache_specific_dimensions"]) == 5, "T2 should still have 5 dims"
    assert isinstance(out["summary_prose"], str)
    assert isinstance(out["next_action_suggestion"], str)
    print("  OK   garbage types -> coerced to canonical")

    # LLM-flagged retry, but threshold says no — coerce should preserve LLM signal
    out = _coerce_rubric({
        "tache_specific_dimensions": _t3_strong(),
        "retry_recommendation": {"should_retry": True, "reason": "LLM noticed something subtle"},
    }, "tache_3")
    if not out["retry_recommendation"]["should_retry"]:
        failures += 1
        print(f"  FAIL LLM-only retry signal not preserved: {out['retry_recommendation']}")
    elif "LLM-flagged" not in out["retry_recommendation"]["reason"]:
        failures += 1
        print(f"  FAIL LLM-only retry reason not prefixed: {out['retry_recommendation']}")
    else:
        print("  OK   LLM-only retry signal preserved with prefix")

    # Score over-range clamps
    out = _coerce_rubric({
        "tache_specific_dimensions": [{"key": "premiere_impression", "score": 99}],
    }, "tache_1")
    assert out["tache_specific_dimensions"][0]["score"] == 5, "score 99 should clamp to 5"
    out = _coerce_rubric({
        "tache_specific_dimensions": [{"key": "premiere_impression", "score": -3}],
    }, "tache_1")
    assert out["tache_specific_dimensions"][0]["score"] == 0, "score -3 should clamp to 0"
    print("  OK   out-of-range scores clamp")

    return failures


# ═══════════════════════════════════════════════════════════════
# Pass 3 — live Claude call (one per Tâche)
# ═══════════════════════════════════════════════════════════════

_T1_TRANSCRIPT = (
    "Bonjour, je m'appelle Marc. Je suis ingénieur. J'habite à Toronto. "
    "J'aime le sport et... euh... j'aime la cuisine aussi. Je travaille "
    "dans une grande entreprise. Voilà."
)

_T2_TRANSCRIPT = (
    "Bonjour madame. Je voudrais réserver une chambre. Pouvez-vous me dire "
    "le prix par nuit ? Est-ce qu'il y a un petit-déjeuner inclus ? "
    "Et le wifi est-il gratuit dans la chambre ? Pourriez-vous m'envoyer "
    "la confirmation par email ? Merci beaucoup."
)

_T3_TRANSCRIPT = (
    "À mon avis, les réseaux sociaux ont un impact négatif sur la jeunesse. "
    "D'une part, ils créent une dépendance — les jeunes passent des heures "
    "sur leur téléphone au lieu de lire ou de faire du sport. D'autre part, "
    "ils favorisent la comparaison sociale, ce qui nuit à l'estime de soi. "
    "Cependant, on pourrait dire qu'ils permettent de garder le contact "
    "avec des amis lointains. Néanmoins, les inconvénients dépassent les "
    "avantages. Par conséquent, il faut limiter leur usage."
)


async def pass_3_live() -> int:
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("\n[Pass 3] Live Claude — SKIPPED (no ANTHROPIC_API_KEY in env)")
        return 0
    print("\n[Pass 3] Live Claude")
    failures = 0
    for mode, transcript, context in [
        ("tache_1", _T1_TRANSCRIPT, "Tâche 1 — Présentation de soi."),
        ("tache_2", _T2_TRANSCRIPT, "Tâche 2 — Réservation hôtel."),
        ("tache_3", _T3_TRANSCRIPT, "Les réseaux sociaux ont-ils un impact négatif sur la jeunesse ?"),
    ]:
        result = await apply_tache_rubric(mode, transcript, context)
        dims = result["tache_specific_dimensions"]
        sidebars = result["universal_sidebars"]
        retry = result["retry_recommendation"]
        expected_dim_count = {"tache_1": 5, "tache_2": 5, "tache_3": 6}[mode]
        ok_dims = len(dims) == expected_dim_count and all(d.get("score") is not None for d in dims)
        ok_sidebars = set(sidebars.keys()) == {"conjugation", "grammar_structure", "sentence_construction"}
        ok_retry = isinstance(retry.get("should_retry"), bool)
        ok = ok_dims and ok_sidebars and ok_retry
        if not ok:
            failures += 1
        marker = "OK " if ok else "FAIL"
        print(f"  {marker}  {mode}  dims={len(dims)} (expected {expected_dim_count})  sidebars={list(sidebars.keys())}  retry={retry}")
        if not ok or os.getenv("F083_VERBOSE"):
            print("       summary_prose:", (result.get("summary_prose") or "")[:200].replace("\n", " "))
            print("       next_action:", (result.get("next_action_suggestion") or "")[:160])
    return failures


# ═══════════════════════════════════════════════════════════════
# Entry
# ═══════════════════════════════════════════════════════════════

async def main() -> int:
    failures = 0
    failures += pass_1_threshold()
    failures += pass_2_coercion()
    failures += await pass_3_live()
    print(f"\n[F-083] failures: {failures}")
    return failures


if __name__ == "__main__":
    rc = asyncio.run(main())
    raise SystemExit(0 if rc == 0 else 1)
