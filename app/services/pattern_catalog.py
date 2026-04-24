"""Pattern catalog — maps internal snake_case pattern keys to
human-readable French labels for student-facing display.

Keys flow unchanged through the DB and backend logic (matching, analytics).
Only the rendered label differs, per F-034.

Adding a new pattern: add one line to PATTERN_LABELS. The frontend picks
up the change automatically via GET /api/patterns/labels.
"""
from __future__ import annotations

import logging
from typing import Iterable

logger = logging.getLogger(__name__)


PATTERN_LABELS: dict[str, str] = {
    # ── Couche 2 — discourse patterns (prompt-defined) ──────────────
    "cadrage_contextuel":       "Cadrage du sujet",
    "reformulation_sujet":      "Reformuler la question",
    "mise_en_perspective":      "Mise en perspective",
    "problematisation":         "Problématisation",
    "exemple_ancre":            "Exemple concret",
    "these_antithese":          "Thèse-antithèse",
    "concession_prealable":     "Concession préalable",
    "concessions_prealables":   "Concessions préalables",
    "reformulation_interne":    "Reformulation interne",
    "montee_en_generalite":     "Montée en généralité",
    "question_rhetorique":      "Question rhétorique",
    "raisonnement_par_analogie":"Raisonnement par analogie",
    "certes_mais":              "Certes… mais",
    "accord_partiel":           "Accord partiel",
    "nuance_conditionnelle":    "Nuance conditionnelle",
    "auto_nuance":              "Auto-nuance",
    "prise_de_position":        "Prise de position",
    "synthese":                 "Synthèse finale",
    "synthese_nuancee":         "Synthèse nuancée",
    "ouverture_prospective":    "Ouverture prospective",
    "echo_introduction":        "Écho à l'introduction",
    "d_un_cote_de_l_autre":     "D'un côté… de l'autre",

    # ── Couche 4 — English habits (prompt-defined) ──────────────────
    # Faux-amis (French/English contrast: A ≠ B format)
    "realiser":                 "Faux-ami : réaliser ≠ realize",
    "actuellement":             "Faux-ami : actuellement ≠ actually",
    "supporter":                "Faux-ami : supporter ≠ support",
    "adresser":                 "Faux-ami : adresser ≠ address",
    "opportunite":              "Faux-ami : opportunité ≠ opportunity",
    # Prépositions (French/English contrast, standardized to A ≠ B)
    "dependre_sur":             "Préposition : dépendre de ≠ depend on",
    "consister_de":             "Préposition : consister à/en ≠ consist of",
    "interesse_dans":           "Préposition : intéressé par ≠ interested in",
    # Calques (French/English contrast where applicable)
    "passif_excessif":          "Passif excessif",
    "important_pour":           "Calque : il est important que ≠ it's important for",
    "il_y_a_excessif":          "« Il y a » excessif",
    "make_someone":             "Calque : faire quelqu'un faire ≠ make someone do",
    "in_order_to":              "Calque : afin de ≠ in order to",
    # Boucles (repetition, no English contrast)
    "boucle_je_pense":          "Boucle : « je pense » répété",
    "boucle_parce_que":         "Boucle : « parce que » répété",
    "boucle_mais":              "Boucle : « mais » répété",
    "boucle_par_exemple":       "Boucle : « par exemple » répété",
    # Éléments manquants
    "ne_manquant":              "Omission du « ne » négatif",
    "article_manquant":         "Article manquant",
    # Ordre
    "ordre_rigide":             "Ordre SVO rigide",

    # ── Observed in stored data (Claude-emitted, not in prompt) ─────
    "accord_genre_nombre":            "Accord en genre/nombre",
    "accord_sujet_verbe":             "Accord sujet-verbe",
    "accord_relatif":                 "Accord avec le relatif",
    "accumulation_sans_connecteurs":  "Phrases sans connecteurs",
    "adjectif_accord":                "Accord de l'adjectif",
    "calque_croire":                  "Calque : croire",
    "calque_lexical":                 "Calque lexical",
    "code_switching":                 "Mot anglais inséré",
    "coherence_lexicale":             "Cohérence lexicale",
    "coherence_logique":              "Cohérence logique",
    "connecteur_approprie":           "Connecteur approprié",
    "connecteur_base":                "Connecteurs basiques",
    "connecteur_fixe":                "Connecteur fixe",
    "connecteur_incorrect":           "Connecteur incorrect",
    "connecteurs_fixes":              "Connecteurs fixes",
    "connecteurs_logiques":           "Connecteurs logiques",
    "connecteurs_sophistiques":       "Connecteurs sophistiqués",
    "construction_inintelligible":    "Construction inintelligible",
    "construction_non_idiomatique":   "Tournure non-idiomatique",
    "construction_syntaxique_anglaise":"Construction anglaise",
    "faux_amis":                      "Faux-amis",
    "faux_amis_probable":             "Faux-ami possible",
    "lexique_specifique":             "Lexique spécifique",
    "liste_plate":                    "Liste plate",
    "parallelisme_prepositions":      "Parallélisme des prépositions",
    "phrase_incomplete":              "Phrase incomplète",
    "preposition_incorrecte":         "Préposition incorrecte",
    "prononciation_ciblee":           "Prononciation ciblée",
    "reconstruction_argumentative":   "Reconstruction argumentative",
    "reformulation_coherente":        "Reformulation cohérente",
    "reformulation_problematique":    "Reformulation problématique",
    "reformulation_problematisee":    "Problématisation approfondie",
    "registre_oral":                  "Registre oral",
    "repetition_sujet":               "Répétition du sujet",
    "restructuration_argumentative":  "Restructuration argumentative",
    "structuration_idees":            "Structuration des idées",
    "structure_argumentative":        "Structure argumentative",
    "transcription_error":            "Erreur de transcription",
    "vocabulaire_inapproprie":        "Vocabulaire inapproprié",
    "vocabulaire_precis":             "Vocabulaire précis",
}


# Per-process dedup so a missing key only logs once even if emitted
# across many recordings. Keeps the signal high in review passes.
_seen_unknown: set[str] = set()


def label_for(key: str | None) -> str:
    """Return the student-facing label for a pattern key.

    Unknown keys get a humanized fallback (underscores → spaces, first
    letter capitalized) and log a one-shot warning so gaps in the
    catalog can be reviewed periodically.
    """
    if not key:
        return ""
    if key in PATTERN_LABELS:
        return PATTERN_LABELS[key]
    if "_" not in key:
        # Already human-looking (e.g. "antithèse", "conjugaison") — no log,
        # no humanize, pass through unchanged.
        return key
    # Snake_case key without a catalog entry: humanize + one-shot warn.
    if key not in _seen_unknown:
        _seen_unknown.add(key)
        logger.warning(
            f"Pattern key '{key}' has no catalog entry, using humanized fallback"
        )
    humanized = key.replace("_", " ")
    return humanized[:1].upper() + humanized[1:]


def log_unknown_pattern_keys(analysis: dict) -> None:
    """Walk an analysis response dict and trigger a one-shot warning for
    every pattern key that would fall through to the humanized fallback.

    Called once per recording at write time so new keys emitted by Claude
    appear in logs immediately — not on every subsequent read.
    """
    if not isinstance(analysis, dict):
        return
    arrays: Iterable[Iterable[str]] = (
        analysis.get("patterns_detectes") or [],
        analysis.get("patterns_manquants") or [],
        analysis.get("reflexes_detectes") or [],
    )
    for arr in arrays:
        if isinstance(arr, list):
            for k in arr:
                if isinstance(k, str):
                    label_for(k)
    # Ordonnance exercises also carry keys in ex.type
    ordo = analysis.get("ordonnance") or {}
    if isinstance(ordo, dict):
        for ex in ordo.get("exercices", []) or []:
            if isinstance(ex, dict):
                label_for(ex.get("type"))
