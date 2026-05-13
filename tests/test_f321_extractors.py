"""F-321 — pytest coverage for the extractor regex + table heuristics.

Tests pure-logic functions: line-level gloss patterns and column-
polarity heuristics for tables. Does NOT touch the Haiku-assisted
extractor (covered by the Phase C 5-file validation pass instead).
"""
from __future__ import annotations

import pytest

from app.services.f321_extractors import (
    _fr_score,
    _is_likely_english,
    _looks_french,
    extract_gloss_from_line,
    parse_haiku_extractor_response,
)


# ── French / English scoring heuristics ──────────────────────────


def test_fr_score_diacritic_text():
    assert _fr_score("être ou ne pas être") > 0.05


def test_fr_score_ascii_text():
    assert _fr_score("to be or not to be") == 0.0


def test_looks_french_diacritic():
    assert _looks_french("Il fait beau aujourd'hui.") is True


def test_looks_french_function_words_only():
    # No diacritics but plenty of FR function words.
    assert _looks_french("le chat est dans la maison") is True


def test_looks_french_negative_english():
    assert _looks_french("the cat is in the house") is False


def test_likely_english_basic():
    assert _is_likely_english("the cat is in the house") is True


def test_likely_english_rejects_diacritic():
    assert _is_likely_english("être ou ne pas être") is False


# ── regex gloss patterns ─────────────────────────────────────────


def test_gloss_parens():
    line = "faire la grasse matinée (to sleep in)"
    chunk = extract_gloss_from_line(line)
    assert chunk is not None
    assert chunk["chunk_fr"] == "faire la grasse matinée"
    assert chunk["chunk_en"] == "to sleep in"
    assert chunk["extractor"] == "regex"


def test_gloss_em_dash():
    line = "carte d'identité — ID card"
    chunk = extract_gloss_from_line(line)
    assert chunk is not None
    assert chunk["chunk_fr"] == "carte d'identité"
    assert chunk["chunk_en"] == "ID card"


def test_gloss_en_dash():
    line = "rendez-vous – appointment"
    chunk = extract_gloss_from_line(line)
    assert chunk is not None
    assert chunk["chunk_fr"] == "rendez-vous"
    assert chunk["chunk_en"] == "appointment"


def test_gloss_colon():
    line = "boulot : work (informal)"
    # Colon pattern matches; the parenthesized "(informal)" is part of
    # the EN side because there's no FR/EN ambiguity at the colon.
    chunk = extract_gloss_from_line(line)
    assert chunk is not None
    assert chunk["chunk_fr"] == "boulot"


def test_gloss_polarity_reversed_rejected():
    """If the parentheses contain French and the prefix is English,
    we should NOT extract — polarity is wrong."""
    line = "the bakery (la boulangerie)"
    chunk = extract_gloss_from_line(line)
    # EN side detection rejects French-diacritic content.
    assert chunk is None


def test_gloss_skips_instruction_line():
    chunk = extract_gloss_from_line(
        "Exercice 3 : Complete the sentences below."
    )
    assert chunk is None


def test_gloss_skips_empty_or_short():
    assert extract_gloss_from_line("") is None
    assert extract_gloss_from_line("X (Y)") is None  # both too short


def test_gloss_skips_no_pattern():
    """A normal French sentence with no gloss structure returns None."""
    chunk = extract_gloss_from_line(
        "Aujourd'hui je vais au marché pour acheter des pommes."
    )
    assert chunk is None


# ── Haiku response parser ────────────────────────────────────────


def test_parse_haiku_array_shape():
    response = [
        {"chunk_fr": "prendre un verre", "chunk_en": "to grab a drink"},
        {"chunk_fr": "faire la fête", "chunk_en": "to party", "register": "informel"},
    ]
    chunks = parse_haiku_extractor_response(response, "test.docx")
    assert len(chunks) == 2
    assert chunks[0]["chunk_fr"] == "prendre un verre"
    assert chunks[0]["source_file"] == "test.docx"
    assert chunks[1]["register_hint"] == "informel"


def test_parse_haiku_dict_wrapper():
    """Some Haiku responses wrap the array in a dict — accept common
    keys."""
    response = {"chunks": [
        {"chunk_fr": "à propos de", "chunk_en": "about"},
    ]}
    chunks = parse_haiku_extractor_response(response, "test.docx")
    assert len(chunks) == 1
    assert chunks[0]["chunk_fr"] == "à propos de"


def test_parse_haiku_drops_malformed():
    response = [
        {"chunk_fr": "valid one", "chunk_en": "fine"},
        {"chunk_fr": "", "chunk_en": "missing fr"},          # drop
        {"chunk_en": "no fr key"},                            # drop
        "not a dict",                                          # drop
        {"chunk_fr": "x", "chunk_en": "too short fr"},       # drop (fr<2)
        {"chunk_fr": "ok one", "chunk_en": None},             # keep (en optional)
    ]
    chunks = parse_haiku_extractor_response(response, "f.docx")
    assert [c["chunk_fr"] for c in chunks] == ["valid one", "ok one"]


def test_parse_haiku_unknown_register_nulled():
    response = [
        {"chunk_fr": "test", "chunk_en": "test", "register": "garbage"},
    ]
    chunks = parse_haiku_extractor_response(response, "f.docx")
    assert chunks[0].get("register_hint") is None


def test_parse_haiku_empty_response():
    assert parse_haiku_extractor_response([], "f.docx") == []
    assert parse_haiku_extractor_response("not even a list", "f.docx") == []
    assert parse_haiku_extractor_response(None, "f.docx") == []
