"""V-009.be — La Voix (5th couche) unit tests.

Covers:
  - couche_labels: la_voix in COUCHE_ORDER and COUCHE_DISPLAY_LABELS
  - couche_labels: couches_array returns 5 items with correct shape
  - scoring_profiles: all oral modes have la_voix key with weight 0.0
  - scoring_profiles: compute_weighted_note_globale unchanged when la_voix=0
  - analysis: LA_VOIX constant defined and non-empty
  - analysis: GRILLES include COUCHE 5 lines for all levels
  - recordings: _get_la_voix_score helper
  - recordings: _get_la_voix_score returns 0.0 for legacy/empty rows
"""
import json
import types
import pytest

from app.services.couche_labels import (
    COUCHE_ORDER,
    COUCHE_DISPLAY_LABELS,
    couches_array,
)
from app.services.scoring_profiles import (
    SCORING_PROFILES,
    compute_weighted_note_globale,
)
from app.services.analysis import LA_VOIX, GRILLES


# ─── couche_labels ────────────────────────────────────────────────────────────

def test_la_voix_in_couche_order():
    assert "la_voix" in COUCHE_ORDER


def test_la_voix_is_fifth():
    assert COUCHE_ORDER.index("la_voix") == 4


def test_la_voix_display_labels_present():
    assert "la_voix" in COUCHE_DISPLAY_LABELS
    labels = COUCHE_DISPLAY_LABELS["la_voix"]
    assert labels["en"]
    assert labels["fr"]


def test_couches_array_returns_five_items():
    scores = {
        "le_fond": 3,
        "les_moules_des_idees": 2,
        "les_moules": 4,
        "les_reflexes_anglais": 3,
        "la_voix": 2,
    }
    result = couches_array(scores)
    assert len(result) == 5


def test_couches_array_la_voix_entry_shape():
    scores = {
        "le_fond": 3,
        "les_moules_des_idees": 2,
        "les_moules": 4,
        "les_reflexes_anglais": 3,
        "la_voix": 2,
    }
    result = couches_array(scores)
    la_voix_entry = next(e for e in result if e["key"] == "la_voix")
    assert la_voix_entry["score"] == 2
    assert la_voix_entry["display_label_en"]
    assert la_voix_entry["display_label_fr"]


def test_couches_array_la_voix_defaults_to_zero():
    scores = {
        "le_fond": 3,
        "les_moules_des_idees": 2,
        "les_moules": 4,
        "les_reflexes_anglais": 3,
    }
    result = couches_array(scores)
    la_voix_entry = next(e for e in result if e["key"] == "la_voix")
    assert la_voix_entry["score"] == 0


# ─── scoring_profiles ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("mode", ["tache_1", "tache_2", "tache_3", "legacy"])
def test_scoring_profile_has_la_voix_key(mode):
    profile = SCORING_PROFILES[mode]
    assert "la_voix" in profile


@pytest.mark.parametrize("mode", ["tache_1", "tache_2", "tache_3", "legacy"])
def test_la_voix_weight_is_zero(mode):
    assert SCORING_PROFILES[mode]["la_voix"] == 0.0


def test_compute_weighted_note_globale_unchanged_with_la_voix_zero():
    carte_without = {
        "le_fond": 4,
        "les_moules_des_idees": 3,
        "les_moules": 3,
        "les_reflexes_anglais": 3,
    }
    carte_with = dict(carte_without, la_voix=5)
    score_without = compute_weighted_note_globale("tache_3", carte_without, None)
    score_with = compute_weighted_note_globale("tache_3", carte_with, None)
    assert score_without == score_with


# ─── analysis constants ───────────────────────────────────────────────────────

def test_la_voix_constant_non_empty():
    assert LA_VOIX
    assert len(LA_VOIX.strip()) > 50


def test_la_voix_constant_mentions_couche_5():
    assert "COUCHE 5" in LA_VOIX


@pytest.mark.parametrize("level", ["B1", "B2", "C1"])
def test_grille_mentions_couche_5(level):
    assert "COUCHE 5" in GRILLES[level]


# ─── recordings helper ────────────────────────────────────────────────────────

def _make_fake_feedback(raw_llm_response: str | None) -> object:
    """Return a minimal stand-in for a Feedback ORM row."""
    fb = types.SimpleNamespace()
    fb.raw_llm_response = raw_llm_response
    return fb


def test_get_la_voix_score_extracts_from_raw():
    from app.routers.recordings import _get_la_voix_score

    analysis_dict = {"la_carte": {"le_fond": 4, "la_voix": 3}}
    fb = _make_fake_feedback(json.dumps(analysis_dict))
    assert _get_la_voix_score(fb) == 3.0


def test_get_la_voix_score_legacy_row_returns_zero():
    from app.routers.recordings import _get_la_voix_score

    analysis_dict = {"la_carte": {"le_fond": 4}}
    fb = _make_fake_feedback(json.dumps(analysis_dict))
    assert _get_la_voix_score(fb) == 0.0


def test_get_la_voix_score_empty_raw_returns_zero():
    from app.routers.recordings import _get_la_voix_score

    fb = _make_fake_feedback(None)
    assert _get_la_voix_score(fb) == 0.0


def test_get_la_voix_score_malformed_json_returns_zero():
    from app.routers.recordings import _get_la_voix_score

    fb = _make_fake_feedback("not-json")
    assert _get_la_voix_score(fb) == 0.0


def test_get_la_voix_score_float_coercion():
    from app.routers.recordings import _get_la_voix_score

    analysis_dict = {"la_carte": {"la_voix": "4"}}
    fb = _make_fake_feedback(json.dumps(analysis_dict))
    assert _get_la_voix_score(fb) == 4.0
