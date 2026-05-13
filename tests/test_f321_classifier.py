"""F-321 — pytest coverage for the classifier's pre-API filters.

Tests the deterministic skip filters and dedup logic. Does NOT
hit the Haiku API — the runner-level integration is exercised by
scripts/classify_f321_docx.py end-to-end.
"""
from __future__ import annotations

import pytest

from app.services.f321_classifier import (
    collapse_duplicate_filenames,
    detect_duplicate_suffix,
    is_publisher_import_by_content,
    is_publisher_import_by_filename,
)


# ── publisher filename detection ─────────────────────────────────


@pytest.mark.parametrize("filename", [
    "Vocabulaire_v2.docx",
    "Vocabulaire_Progressif_CLEAN.docx",
    "Vocabulaire_Progressif_Niveau_Perfectionnement.docx",
    "Communication_Progressive_du_Francais.docx",
    "Niveau_B2_Hachette.docx",
    "vocabulaire_progressif.docx",  # case-insensitive
])
def test_publisher_filename_matches(filename):
    assert is_publisher_import_by_filename(filename) is True


@pytest.mark.parametrize("filename", [
    "Jack_French_Class_2.docx",
    "Le_Faire_Causatif.docx",
    "Andre_Exercices_Grammaire.docx",
    "Egor_Subjonctif_Complete.docx",
    "Les_Moules_Complete_Framework.docx",
    "homework_3_andre.docx",
    # "progress.docx" used to false-match on substring "progress";
    # current pattern uses word-bound or substring "progressif" so
    # bare "progress" should NOT match.
    "progress_report.docx",
])
def test_publisher_filename_negatives(filename):
    assert is_publisher_import_by_filename(filename) is False


# ── publisher content detection ──────────────────────────────────


def test_publisher_content_cle_international():
    text = "Le présent ouvrage est publié par CLE International en 2013."
    assert is_publisher_import_by_content(text) == "CLE International"


def test_publisher_content_claire_miquel():
    text = "Vocabulaire Progressif du Français\nClaire Miquel\n2e édition"
    # Either marker is acceptable — both are publisher signals. The
    # implementation returns the FIRST match in its scan order.
    result = is_publisher_import_by_content(text)
    assert result in ("Vocabulaire Progressif du Français", "Claire Miquel")


def test_publisher_content_isbn():
    text = "ISBN 978-2-09-035279-1\nDépôt légal : septembre 2013"
    result = is_publisher_import_by_content(text)
    assert result is not None and result.startswith("ISBN:")


def test_publisher_content_clean_chadi_text():
    text = ("Aujourd'hui, on travaille sur les pronoms. "
            "Voici les exercices que j'ai préparés pour vous.")
    assert is_publisher_import_by_content(text) is None


# ── duplicate-suffix detection ───────────────────────────────────


@pytest.mark.parametrize("filename,expected_stem", [
    ("Le_Faire_Causatif (1).docx", "Le_Faire_Causatif"),
    ("cours_articles (2).docx", "cours_articles"),
    ("homework_-_Copie.docx", "homework"),
    ("homework_-_Copie(1).docx", "homework"),
    ("homework - Copy.docx", "homework"),
    ("homework - Copy (2).docx", "homework"),
    ("notes(copie).docx", "notes"),
    ("notes_copy.docx", "notes"),
    ("notes_copy2.docx", "notes"),
])
def test_duplicate_suffix_detects(filename, expected_stem):
    assert detect_duplicate_suffix(filename) == expected_stem


@pytest.mark.parametrize("filename", [
    "homework.docx",
    "cours_articles_11_02_2026.docx",
    "Jack_French_Class_2.docx",  # "_2" is part of name, not a suffix
    "AUTANT.docx",
])
def test_duplicate_suffix_canonical(filename):
    assert detect_duplicate_suffix(filename) is None


def test_collapse_keeps_canonical_when_both_present():
    files = ["A.docx", "A (1).docx", "A (2).docx", "B.docx"]
    out = collapse_duplicate_filenames(files)
    assert out == ["A.docx", "B.docx"]


def test_collapse_picks_first_when_only_duplicates():
    files = ["A (1).docx", "A (2).docx", "A (3).docx"]
    out = collapse_duplicate_filenames(files)
    # All three share stem "A"; the alphabetically-first variant wins.
    assert out == ["A (1).docx"]


def test_collapse_mixed():
    files = [
        "Le_Faire_Causatif.docx",
        "Le_Faire_Causatif (1).docx",
        "cours_articles_11_02_2026.docx",
        "cours_articles_11_02_2026 (1).docx",
        "AUTANT.docx",
    ]
    out = collapse_duplicate_filenames(files)
    assert "Le_Faire_Causatif.docx" in out
    assert "Le_Faire_Causatif (1).docx" not in out
    assert "cours_articles_11_02_2026.docx" in out
    assert "cours_articles_11_02_2026 (1).docx" not in out
    assert "AUTANT.docx" in out
    assert len(out) == 3
