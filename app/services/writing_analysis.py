import json
import httpx
from app.config import settings
from app.services.exam_profiles import ExamProfile, get_profile

# ===================================================================
#  Writing Analysis Engine — La Méthode en Couches (Written French)
#
#  V-016a (2026-05-12): rewritten from a 4-LAYER descriptive frame to
#  the 5-COUCHE methodology locked V-009 (2026-05-05). The writing path
#  now emits the full methode_en_couches surface; oral analysis.py
#  catches up under V-009.be.
#
#  5 Couches (internal names → user-facing labels EN / FR):
#    1. le_fond              → Range     / Étendue
#    2. les_moules_des_idees → Coherence / Cohérence
#    3. les_moules           → Accuracy  / Correction
#    4. les_reflexes_anglais → Fluency   / Aisance
#    5. la_voix              → Voice     / Voix     (NEW — V-016a)
# ===================================================================

# ═══════════════════════════════════════════════════════════════
# DUAL-CHANNEL FEEDBACK BLOCK (F-032) — written skill mirror
# Duplicated from analysis.py per the services' "no cross-import"
# convention (writing and oral services are intentionally independent).
# Keep the dual-voice contract (examiner_remark_fr + teacher_coaching)
# in sync with analysis.DUAL_CHANNEL_BLOCK. The grille that follows is
# WRITING-SPECIFIC (5 couches) and is intentionally NOT mirrored — oral
# stays on the legacy 4-dimension shape until V-009.be.
# ═══════════════════════════════════════════════════════════════

DUAL_CHANNEL_BLOCK = """═══════════════════════════════════════════════════════════
DUAL-CHANNEL FEEDBACK — LES DEUX VOIX
═══════════════════════════════════════════════════════════
Pour chaque critère et pour chaque couche de la grille La Méthode en
Couches, tu produis DEUX VOIX DISTINCTES. Ne les mélange jamais. Elles
ont des buts, des registres et des destinataires différents.

▸ VOIX EXAMINATEUR (examiner_remark_fr)
  - Français UNIQUEMENT. Jamais de traduction, jamais de "|||".
  - Registre neutre-autoritaire d'un correcteur officiel.
  - 1 à 2 phrases maximum. Pure évaluation, aucun coaching.
  - Ne cite PAS le texte de l'étudiant. Ne propose PAS de transformation.

{examiner_voice_guide}

▸ VOIX PROFESSEUR (teacher_coaching)
  - coaching_en : TOUJOURS en anglais, quel que soit {ui_language_name}.
  - coaching_fr : TOUJOURS un exemple en français (matériel d'apprentissage pour
    l'étudiant, pas une traduction de coaching_en).
  - transformation : dans la langue de l'interface étudiant ({ui_language_name}).
    C'est l'action que l'étudiant doit exécuter ; il doit la comprendre.
  - Registre chaleureux, spécifique, coaching.
  - DOIT citer les mots EXACTS de l'étudiant (pas de paraphrase).
  - DOIT terminer sur une transformation concrète à appliquer au prochain essai.

{teacher_voice_guide}

EXEMPLES (montrent la différence tonale — à respecter strictement) :

Exemple 1 — critère grammatical_range, étudiant B2 :
  examiner_remark_fr : "Éventail grammatical limité. Usage correct du
    présent et du passé composé, mais absence de subordonnées complexes
    et recours systématique à la parataxe. Niveau B2 partiellement atteint."
  teacher_coaching :
    coaching_en : "You wrote 'Je pense la technologie est importante'
      three times — same flat pattern every time. In French you want to
      vary how you start opinion sentences, especially at B2 level."
    coaching_fr : "Au lieu de 'Je pense que...', essaie : 'Il me semble
      que...', 'Force est de constater que...', 'On peut soutenir que...'."
    transformation : "Prochaine rédaction : utilise au moins deux
      tournures d'opinion différentes."

Exemple 2 — critère lexical_range, étudiant B2 :
  examiner_remark_fr : "Lexique usuel correctement maîtrisé mais peu varié.
    Répétition de 'chose' et 'truc' là où un vocabulaire plus précis
    serait attendu au niveau B2."
  teacher_coaching :
    coaching_en : "You used 'chose' seven times and 'truc' four times.
      These are fine in casual writing but an examiner reads them as
      vocabulary you're missing."
    coaching_fr : "Remplace 'une chose importante' par 'un aspect important',
      'un enjeu', 'un élément clé'. Remplace 'ce truc' par 'ce phénomène',
      'cette pratique', 'cette question'."
    transformation : "Bannis 'chose' et 'truc' de la prochaine rédaction."

La même contrainte de double voix s'applique à chaque entrée de
methode_en_couches : examiner_remark_fr en français pur, teacher_coaching
en triple format (coaching_en / coaching_fr / transformation)."""


# 5-couche per-level grilles. Tolerance bands by CEFR target level.
# Each LAYER 1-5 line maps directly to internal couche names so the
# scorer doesn't have to translate.
WRITING_GRILLES = {
    "B1": """GRILLE B1 — Tolérance ÉLEVÉE.
COUCHE 1 (le_fond):              Position simple acceptée. 1-2 exemples concrets suffisent. Hors-sujet pénalisé.
COUCHE 2 (les_moules_des_idees): Plan minimal accepté (intro courte, 1-2 paragraphes, conclusion). Connecteurs basiques (et, mais, parce que).
COUCHE 3 (les_moules):           Phrases simples acceptées. SVO standard. Présent, passé composé, imparfait. Accords majeurs corrects.
COUCHE 4 (les_reflexes_anglais): Ne signale que les anglicismes flagrants et les calques évidents.
COUCHE 5 (la_voix):              Voix anglophone tolérée tant que le sens passe. Registre informel accepté.
SCORING par couche : 10-12/20 = attendu. 14+/20 = excellent.""",

    "B2": """GRILLE B2 — Tolérance MODÉRÉE.
COUCHE 1 (le_fond):              Position argumentée attendue. Au moins 2-3 exemples développés. Profondeur exigée, surface pénalisée.
COUCHE 2 (les_moules_des_idees): Plan thèse-antithèse-synthèse ou équivalent attendu. Connecteurs logiques variés (cependant, en effet, par conséquent).
COUCHE 3 (les_moules):           Subordonnées, relatives, subjonctif présent attendus. Accords cohérents. Prépositions précises.
COUCHE 4 (les_reflexes_anglais): Signale tous les anglicismes, calques, transferts de prépositions, faux-amis.
COUCHE 5 (la_voix):              Registre adapté au genre attendu. Tournures idiomatiques françaises souhaitées. Phrasé "traduit" pénalisé.
SCORING par couche : 12-14/20 = attendu. 16+/20 = excellent.""",

    "C1": """GRILLE C1 — Tolérance TRÈS FAIBLE.
COUCHE 1 (le_fond):              Argumentation nuancée, contre-arguments anticipés, exemples précis et variés exigés.
COUCHE 2 (les_moules_des_idees): Architecture rhétorique française pleine (mise en relief, progression dialectique, transitions invisibles).
COUCHE 3 (les_moules):           Subjonctif passé, conditionnel passé, concordance des temps, nominalisation, voix passive idiomatique.
COUCHE 4 (les_reflexes_anglais): Tolérance quasi-nulle. Tout réflexe anglais est signalé.
COUCHE 5 (la_voix):              Voix native attendue. Registre, idiomatismes, rythme rhétorique français — un correcteur natif doit reconnaître "pensée en français".
SCORING par couche : 14-16/20 = attendu. 18+/20 = excellent.""",
}


SYSTEM_PROMPT_WRITING = """You are an expert French writing evaluator specializing in anglophone learners preparing for TCF / TEF / DELF / DALF written exams. You use the 5-couche diagnostic framework "La Méthode en Couches" to analyze written French production.

═══════════════════════════════════════════════════════════
LA MÉTHODE EN COUCHES — 5 DIAGNOSTIC LAYERS
═══════════════════════════════════════════════════════════
Each couche is scored 0-20 INDEPENDENTLY. The overall score is the
arithmetic mean of the five couches, rounded to one decimal.

──────────────────────────────────────
COUCHE 1 — LE FOND  (display: Range / Étendue)
──────────────────────────────────────
Substance and span of the text. Ideas, arguments, examples, evidence,
relevance to the prompt. Does the candidate develop a position with
adequate depth and breadth, with concrete supporting material?
LIFTS:  precise examples, varied angles, clear position, on-prompt focus, adequate length.
SINKS:  paraphrasing the prompt, surface-only ideas, off-topic drift, hollow generalities, missing development.

──────────────────────────────────────
COUCHE 2 — LES MOULES DES IDÉES  (display: Coherence / Cohérence)
──────────────────────────────────────
Macro-organization of thought. Does the text progress like a French
speaker thinks (context-first, thèse-antithèse-synthèse, signposted
turns) or like an anglophone bullet-list (point-first, evidence after,
flat enumeration)?
LIFTS:  French rhetorical scaffolding (intro posing a question → developed argument → conclusion), logical connectors (cependant, en effet, par conséquent), context-first paragraph openings.
SINKS:  thesis-led-then-evidence (English shape), bullet-style flat lists, missing transitions, stitched fragments.

──────────────────────────────────────
COUCHE 3 — LES MOULES  (display: Accuracy / Correction)
──────────────────────────────────────
Sentence-level architecture and grammatical accuracy. Conjugation,
agreement, prepositions, articles, tense choice, subordination,
relative pronouns, impersonal constructions, nominalization. Does each
sentence sound French-built or English-translated?
LIFTS:  correct subjonctif after triggers, concordance des temps, native preposition logic, varied subordination, impersonal "il est ... que" patterns where appropriate, accurate gender/number agreement.
SINKS:  agreement errors (gender, number), wrong prepositions, missing/wrong articles, calqued English sentence shapes in French words, choppy parataxis, missing or misused relative pronouns.

──────────────────────────────────────
COUCHE 4 — LES RÉFLEXES ANGLAIS  (display: Fluency / Aisance)
──────────────────────────────────────
L1 interference patterns — English habits bleeding through. Faux-amis,
calques, missing or misplaced "ne", anglicized question forms, "il y a"
vs "there is" overuse, English preposition transfer, English tense
logic on habitual actions, zero-article transfer.
LIFTS:  idiomatic French where the English temptation existed (faire face à vs "face up to", avoir du sens vs "make sense"), correct ne placement, French question shapes, preposition independence from English logic.
SINKS:  faux-amis used wrong (réaliser, supporter, actuellement, éventuellement), calques (faire sens, avoir du fun, prendre une décision pour "make a decision"), preposition transfers (dépendre sur, chercher pour), English tense logic ("hier j'ai mangé" for habitual past).

──────────────────────────────────────
COUCHE 5 — LA VOIX  (display: Voice / Voix)
──────────────────────────────────────
Native-French read vs translated-English read. Register fit, idiomatic
patterns, French rhetorical flow, cultural-fit phrasing, voice
consistency across paragraphs. Detects whether a native French writer
would recognize the text as "thinking in French" vs "translating from
English."
LIFTS:  idiomatic phrasing in service of the argument, register matched to the genre (formal letter vs opinion essay vs journalistic style), rhetorical patterns native readers expect (mise en relief, focus by left-dislocation, rhetorical questions where French uses them), consistent voice across paragraphs.
SINKS:  register clash (slang in formal letter, stiff in casual opinion), translated phrasing that's grammatically correct but reads anglophone, voice shifts paragraph-to-paragraph, French words deployed in English rhetorical molds.

{grille}

═══════════════════════════════════════════════════════════
SCORING DIRECTIVES
═══════════════════════════════════════════════════════════
- Score each of the 5 couches 0-20 INDEPENDENTLY using the level grid above.
- overall_score = arithmetic mean of the 5 couches, rounded to 1 decimal.
- For each error found, quote the EXACT student text, classify by couche
  (internal name), provide the correction, and explain WHY in {ui_language_name}.
  The quoted French text and French corrections stay in French — only the
  explanation prose follows {ui_language_name}.
- Severity: "minor" (no comprehension impact) | "moderate" (causes confusion)
  | "major" (breaks meaning).
- Strengths cite SPECIFIC examples from the student's text.
- next_step is ONE imperative directive in {ui_language_name}, concrete and
  actionable for the next attempt.

{exam_profile_block}

{dual_channel_block}

═══════════════════════════════════════════════════════════
RESPONSE — JSON ONLY
═══════════════════════════════════════════════════════════
{{
  "overall_score": <float 0-20, mean of methode_en_couches scores>,
  "word_count": <integer>,
  "summary": "<2-3 sentence overall assessment in {ui_language_name}>",
  "errors": [
    {{
      "couche": "<le_fond | les_moules_des_idees | les_moules | les_reflexes_anglais | la_voix>",
      "original_text": "<exact text from student>",
      "corrected_text": "<corrected French>",
      "explanation": "<in {ui_language_name} — why this is wrong and how to fix it>",
      "severity": "<minor|moderate|major>"
    }}
  ],
  "strengths": ["<specific things the student did well, citing their text>"],
  "next_steps": ["<legacy alias of next_step — keep populated for backward compat>"],
  "methode_en_couches": {{
    "le_fond": {{
      "score": <0-20>,
      "examiner_remark_fr": "<FR uniquement, 1-2 phrases, évaluation pure — jamais de citation>",
      "teacher_coaching": {{
        "coaching_en": "<ALWAYS in English, cites student's EXACT words>",
        "coaching_fr": "<ALWAYS a French example (learning material)>",
        "transformation": "<in {ui_language_name} — one concrete action for the next attempt>"
      }}
    }},
    "les_moules_des_idees": {{
      "score": <0-20>,
      "examiner_remark_fr": "<FR uniquement>",
      "teacher_coaching": {{"coaching_en": "...", "coaching_fr": "...", "transformation": "..."}}
    }},
    "les_moules": {{
      "score": <0-20>,
      "examiner_remark_fr": "<FR uniquement>",
      "teacher_coaching": {{"coaching_en": "...", "coaching_fr": "...", "transformation": "..."}}
    }},
    "les_reflexes_anglais": {{
      "score": <0-20>,
      "examiner_remark_fr": "<FR uniquement>",
      "teacher_coaching": {{"coaching_en": "...", "coaching_fr": "...", "transformation": "..."}}
    }},
    "la_voix": {{
      "score": <0-20>,
      "examiner_remark_fr": "<FR uniquement>",
      "teacher_coaching": {{"coaching_en": "...", "coaching_fr": "...", "transformation": "..."}}
    }}
  }},
  "next_step": "<in {ui_language_name} — UNE seule directive impérative et concrète pour la prochaine rédaction>",
  "{exam_profile_namespace}": {{
    "overall_score": <float 0-20 — mean of the criteria, rounded to 1 decimal>,
    "criteria": [
      {{
        "criterion_key": "<key from the profile criteria list above>",
        "score": <0-20>,
        "examiner_remark_fr": "<FR uniquement, 1-2 phrases, évaluation pure>",
        "teacher_coaching": {{
          "coaching_en": "<ALWAYS in English, cites student's EXACT words>",
          "coaching_fr": "<ALWAYS a French example (learning material)>",
          "transformation": "<in {ui_language_name} — one concrete action for the next attempt>"
        }}
      }}
    ]
  }}
}}"""


# Canonical 5-couche order + display labels — locked V-009 2026-05-05;
# La Voix added V-016a 2026-05-12. Mirrors couche_labels.COUCHE_ORDER /
# COUCHE_DISPLAY_LABELS in shape, but writing-side stays independent
# (no cross-import oral↔writing). V-009.be will unify the helper.
COUCHE_ORDER: tuple[str, ...] = (
    "le_fond",
    "les_moules_des_idees",
    "les_moules",
    "les_reflexes_anglais",
    "la_voix",
)

COUCHE_DISPLAY_LABELS: dict[str, dict[str, str]] = {
    "le_fond":              {"en": "Range",     "fr": "Étendue"},
    "les_moules_des_idees": {"en": "Coherence", "fr": "Cohérence"},
    "les_moules":           {"en": "Accuracy",  "fr": "Correction"},
    "les_reflexes_anglais": {"en": "Fluency",   "fr": "Aisance"},
    "la_voix":              {"en": "Voice",     "fr": "Voix"},
}


def _extract_couches(feedback: dict | None) -> list[dict]:
    """Flatten methode_en_couches into the FE-consumable shape:
    [{key, display_label_en, display_label_fr, score}, ...] in canonical
    order. Defensive: missing couches default to score=0 so the FE
    surface stays stable when Claude omits a key or the parse fails.
    """
    block = (feedback or {}).get("methode_en_couches") if isinstance(feedback, dict) else None
    if not isinstance(block, dict):
        block = {}
    rows = []
    for key in COUCHE_ORDER:
        cell = block.get(key) if isinstance(block.get(key), dict) else {}
        raw = cell.get("score") if isinstance(cell, dict) else None
        try:
            score = float(raw) if raw is not None else 0.0
        except (TypeError, ValueError):
            score = 0.0
        rows.append({
            "key": key,
            "display_label_en": COUCHE_DISPLAY_LABELS[key]["en"],
            "display_label_fr": COUCHE_DISPLAY_LABELS[key]["fr"],
            "score": score,
        })
    return rows


async def analyze_writing(
    student_text: str,
    prompt_text: str,
    prompt_type: str,
    target_level: str = "B2",
    ui_language: str = "en",
    exam_profile: str | ExamProfile = "tcf_canada",
) -> dict:
    """Analyze a student's written French production using the 5-couche
    framework (La Méthode en Couches) plus the selected exam profile's
    official criteria (default: TCF Canada).
    """
    profile = exam_profile if isinstance(exam_profile, ExamProfile) else get_profile(exam_profile)

    if not settings.ANTHROPIC_API_KEY:
        return _demo_writing_feedback(student_text, profile)

    grille = WRITING_GRILLES.get(target_level, WRITING_GRILLES["B2"])

    criteria_block = profile.build_criteria_prompt_block("writing")
    lang_name = {"en": "English", "fr": "French", "es": "Spanish"}.get(ui_language, "English")
    exam_profile_block = profile.system_prompt_preamble.replace(
        "{criteria_block}", criteria_block
    ).replace(
        "{ui_language_name}", lang_name
    )

    dual_channel_block = DUAL_CHANNEL_BLOCK.replace(
        "{examiner_voice_guide}", profile.examiner_voice_guide
    ).replace(
        "{teacher_voice_guide}", profile.teacher_voice_guide
    )

    system = SYSTEM_PROMPT_WRITING.replace(
        "{grille}", grille
    ).replace(
        "{exam_profile_block}", exam_profile_block
    ).replace(
        "{dual_channel_block}", dual_channel_block
    ).replace(
        "{exam_profile_namespace}", profile.namespace
    ).replace(
        "{ui_language_name}", lang_name
    )

    user_msg = (
        f"Target level: {target_level}\n"
        f"Prompt type: {prompt_type}\n"
        f"Writing prompt: {prompt_text}\n\n"
        f"Student's text:\n\"\"\"\n{student_text}\n\"\"\""
    )

    result = await _call_claude(system, user_msg)

    if isinstance(result, dict):
        result["word_count"] = len(student_text.split())
        result["exam_profile"] = _normalize_writing_profile(result, profile)
        return result

    # Fallback if parsing failed
    return {
        "overall_score": 0,
        "word_count": len(student_text.split()),
        "summary": "Analysis could not be parsed. Please try again.",
        "errors": [],
        "strengths": [],
        "next_steps": [],
        "methode_en_couches": {},
        "exam_profile": _normalize_writing_profile({}, profile),
        "raw_response": str(result),
    }


def _normalize_writing_profile(result: dict, profile: ExamProfile) -> dict:
    """Mirror of analysis._normalize_profile_evaluation for the writing skill.

    Kept local rather than shared so the oral and writing services remain
    independent — neither imports from the other.
    """
    raw = result.get(profile.namespace, {}) if isinstance(result, dict) else {}
    claude_criteria = raw.get("criteria", []) if isinstance(raw, dict) else []
    by_key = {c.get("criterion_key"): c for c in claude_criteria if isinstance(c, dict)}

    rows = []
    scores: list[float] = []
    for criterion in profile.criteria_for("writing"):
        src = by_key.get(criterion.key, {})
        try:
            score = float(src.get("score")) if src.get("score") is not None else None
        except (TypeError, ValueError):
            score = None
        if score is not None:
            scores.append(score)
        tc = src.get("teacher_coaching") or {}
        if not isinstance(tc, dict):
            tc = {}
        rows.append({
            "criterion_key": criterion.key,
            "label_fr_technical": criterion.label_fr_technical,
            "label_fr_student": criterion.label_fr_student,
            "label_en_student": criterion.label_en_student,
            "label_es_student": criterion.label_es_student,
            "max_score": criterion.max_score,
            "score": score if score is not None else 0,
            "feedback": src.get("feedback", ""),
            "examiner_remark_fr": src.get("examiner_remark_fr", ""),
            "teacher_coaching": {
                "coaching_en": tc.get("coaching_en", ""),
                "coaching_fr": tc.get("coaching_fr", ""),
                "transformation": tc.get("transformation", ""),
            },
        })

    overall = round(sum(scores) / len(scores), 1) if scores else 0.0
    cefr = profile.score_to_cefr(overall)
    secondary = profile.cefr_to_secondary(cefr) if profile.cefr_to_secondary else None

    return {
        "profile_id": profile.id,
        "display_name": profile.display_name,
        "frameworks_shown": list(profile.frameworks_shown),
        "overall_score": overall,
        "cefr_level": cefr,
        "secondary_framework_label": profile.secondary_framework_label,
        "secondary_framework_value": secondary,
        "criteria_breakdown": rows,
    }


async def _call_claude(system_prompt: str, user_message: str) -> dict | str:
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                # V-016a triage (2026-05-07): tested Haiku 4.5
                # fallback locally — 42.2s on a 55-word B1 sample,
                # LONGER than Sonnet 4's 36.0s on a 97-word sample.
                # Refutes the "Sonnet-specific latency" hypothesis.
                # Bottleneck is the prompt (3000+ token system) +
                # large max_tokens output, not the model. Reverted
                # to Sonnet. Diagnostic logging in writing_jobs.py
                # is the path to identify the actual prod stall.
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 8192,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_message}],
            },
        )
        resp.raise_for_status()
        data = resp.json()

    raw = data["content"][0]["text"]
    try:
        return json.loads(
            raw.strip()
            .removeprefix("```json").removeprefix("```")
            .removesuffix("```").strip()
        )
    except json.JSONDecodeError:
        return raw


def _demo_writing_feedback(student_text: str, profile: ExamProfile | None = None) -> dict:
    wc = len(student_text.split())
    if profile is None:
        profile = get_profile()
    demo_criteria = [
        {"criterion_key": c.key, "score": 12, "feedback": "[DEMO]|||[DEMO]"}
        for c in profile.criteria_for("writing")
    ]
    demo_couches = {
        key: {
            "score": 12,
            "examiner_remark_fr": "[DEMO] Configurez ANTHROPIC_API_KEY pour une vraie évaluation.",
            "teacher_coaching": {
                "coaching_en": "[DEMO] Configure ANTHROPIC_API_KEY for real coaching.",
                "coaching_fr": "[DEMO] Exemple en français à venir.",
                "transformation": "[DEMO] Action concrète à venir.",
            },
        }
        for key in COUCHE_ORDER
    }
    result = {
        "overall_score": 12.0,
        "word_count": wc,
        "summary": f"[DEMO] Received {wc} words. Configure ANTHROPIC_API_KEY for real analysis.",
        "errors": [
            {
                "couche": "les_moules",
                "original_text": "[DEMO] Example error",
                "corrected_text": "[DEMO] Corrected version",
                "explanation": "[DEMO] Configure API key for real feedback.",
                "severity": "moderate",
            }
        ],
        "strengths": ["[DEMO] Text was submitted successfully."],
        "next_steps": ["[DEMO] Configure ANTHROPIC_API_KEY in .env for real analysis."],
        "methode_en_couches": demo_couches,
        "next_step": "[DEMO] Configure ANTHROPIC_API_KEY in .env for real analysis.",
        profile.namespace: {"overall_score": 12.0, "criteria": demo_criteria},
    }
    result["exam_profile"] = _normalize_writing_profile(result, profile)
    return result
