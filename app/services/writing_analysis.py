import json
import httpx
from app.config import settings
from app.services.exam_profiles import ExamProfile, get_profile

# ===================================================================
#  Writing Analysis Engine — La Methode en Couches (Written French)
#  Adapted from the oral analysis framework for written production.
#
#  4 Layers for writing:
#    1. Sentence Architecture   — English-style structure in French words
#    2. Grammatical Accuracy    — Conjugation, agreement, prepositions
#    3. Lexical Appropriateness — Register, word choice, collocations
#    4. L1 Interference         — English->French transfer errors
# ===================================================================

# ═══════════════════════════════════════════════════════════════
# DUAL-CHANNEL FEEDBACK BLOCK (F-032) — written skill mirror
# Duplicated from analysis.py per the services' "no cross-import"
# convention (writing and oral services are intentionally independent).
# Keep in sync with analysis.DUAL_CHANNEL_BLOCK.
# ═══════════════════════════════════════════════════════════════

DUAL_CHANNEL_BLOCK = """═══════════════════════════════════════════════════════════
DUAL-CHANNEL FEEDBACK — LES DEUX VOIX
═══════════════════════════════════════════════════════════
Pour chaque critère et pour la grille d'analyse, tu produis DEUX VOIX
DISTINCTES. Ne les mélange jamais. Elles ont des buts, des registres et
des destinataires différents.

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

═══════════════════════════════════════════════════════════
GRILLE D'ANALYSE — 4 DIMENSIONS (analyse_par_couche)
═══════════════════════════════════════════════════════════
Produis quatre observations distinctes sur la production, non redondantes
avec les critères. Chaque cellule = 2-4 phrases en français.

  what_works          — Ce qui marche dans cette production. Cite des
                        passages précis. Renforcement positif ciblé.
  what_doesnt_work    — La faiblesse principale. Une seule, la plus
                        importante. Cite un moment spécifique.
  english_habits      — Réflexes anglais détectés (calques, prépositions
                        transférées, ordre des mots anglais, faux-amis).
                        Liste 1-3 exemples concrets tirés du texte.
  structure_quality   — Architecture des phrases et organisation de
                        l'argument. Subordination ? Connecteurs logiques ?
                        Progression thèse-antithèse-synthèse ?

next_step — UNE SEULE directive d'action pour la prochaine rédaction,
            rédigée dans la langue de l'interface étudiant ({ui_language_name}).
            Pas de liste. Phrase courte, impérative, concrète."""


WRITING_GRILLES = {
    "B1": """GRILLE B1 : Tolerance ELEVEE.
LAYER 1: Simple sentence structures accepted. SVO order fine. Some variety expected.
LAYER 2: Present, passe compose, imparfait. Basic agreement. Common prepositions.
LAYER 3: Basic vocabulary sufficient. Informal register tolerated.
LAYER 4: Only flag major anglicisms and obvious calques.
SCORING: 10-12/20 = expected. 14+/20 = excellent.""",

    "B2": """GRILLE B2 : Tolerance MODEREE.
LAYER 1: Complex sentences expected. Subordination, relative clauses, participial phrases.
LAYER 2: All common tenses including subjonctif present. Agreement must be consistent. Preposition accuracy expected.
LAYER 3: Formal register expected for formal letters. Good collocation use. Varied vocabulary.
LAYER 4: Flag all anglicisms, calques, preposition transfers, false cognates.
SCORING: 12-14/20 = expected. 16+/20 = excellent.""",

    "C1": """GRILLE C1 : Tolerance TRES FAIBLE.
LAYER 1: Sophisticated sentence architecture. Inversion, nominalization, passive voice where appropriate, complex subordination.
LAYER 2: Near-perfect grammar. Subjonctif past, conditionnel passe, concordance des temps.
LAYER 3: Precise, nuanced vocabulary. Appropriate register throughout. Natural collocations.
LAYER 4: Flag EVERYTHING. Near-zero tolerance for L1 interference.
SCORING: 14-16/20 = expected. 18+/20 = excellent.""",
}


SYSTEM_PROMPT_WRITING = """You are an expert French writing evaluator specializing in anglophone learners preparing for TCF/DELF written exams. You use a 4-layer diagnostic framework to analyze written French production.

LAYER 1 — SENTENCE ARCHITECTURE
Does the student write sentences that sound French, or are they English sentences dressed in French words?
Look for:
- English word order transferred to French (adjective placement, adverb position)
- Lack of subordination (too many short, choppy sentences)
- Missing or incorrect use of relative pronouns (qui, que, dont, ou)
- Failure to use impersonal constructions ("Il est important que..." vs "C'est important pour...")
- Missing nominalization where French prefers it
- Passive voice overuse (English pattern) vs active/pronominal French alternatives

LAYER 2 — GRAMMATICAL ACCURACY
Concrete grammar errors:
- Verb conjugation (wrong tense, wrong form)
- Subject-verb agreement
- Noun-adjective agreement (gender, number)
- Preposition errors (a/de/en/dans/par/pour)
- Article errors (missing, wrong gender, wrong type)
- Pronoun errors (wrong pronoun, missing "en"/"y")
- Subjonctif missing after required triggers
- Concordance des temps

LAYER 3 — LEXICAL APPROPRIATENESS
- Wrong register (too informal for formal letter, too formal for opinion essay)
- False cognates used incorrectly (realiser, supporter, actuellement, etc.)
- Poor collocations (direct English translation instead of natural French pairing)
- Repetitive vocabulary (same word used 3+ times when alternatives exist)
- Missing or wrong connectors

LAYER 4 — L1 INTERFERENCE PATTERNS
Specific English-to-French transfer errors:
- Calques: direct translations of English expressions ("faire sens" instead of "avoir du sens")
- Preposition transfer: using English preposition logic ("dependre sur" instead of "dependre de")
- Tense transfer: using passe compose where imparfait is needed (habitual actions)
- Article transfer: zero article from English where French requires one
- Structure transfer: "it is + adj + to" patterns, "there is" overuse
- Question formation: English syntax in indirect questions

{grille}

INSTRUCTIONS:
- Evaluate STRICTLY according to the target level grid.
- For each error found, quote the EXACT student text, provide the correction, and explain WHY in {ui_language_name}. The quoted French text and French corrections stay in French — only the explanation prose follows {ui_language_name}.
- Classify severity: "minor" (doesn't impede understanding), "moderate" (causes confusion), "major" (fundamentally wrong or incomprehensible).
- Be specific in explanations — don't just say "wrong preposition", say which preposition and why.
- In the summary, be encouraging but honest.
- Strengths should cite SPECIFIC examples from the student's text.
- Next steps should be actionable and prioritized.

{exam_profile_block}

{dual_channel_block}

Respond ONLY in valid JSON:
{{
  "overall_score": <0-20>,
  "word_count": <integer>,
  "summary": "<2-3 sentence overall assessment in {ui_language_name}>",
  "errors": [
    {{
      "layer": <1-4>,
      "layer_name": "<Sentence Architecture | Grammatical Accuracy | Lexical Appropriateness | L1 Interference>",
      "original_text": "<exact text from student>",
      "corrected_text": "<corrected French>",
      "explanation": "<in {ui_language_name} — why this is wrong and how to fix it>",
      "severity": "<minor|moderate|major>"
    }}
  ],
  "strengths": ["<specific things the student did well, citing their text>"],
  "next_steps": ["<legacy — kept for backward compat, can mirror next_step>"],
  "analyse_par_couche": {{
    "what_works":        {{"title_fr": "Ce qui marche",              "content_fr": "<2-4 phrases FR, cite des passages>"}},
    "what_doesnt_work":  {{"title_fr": "Ce qui ne marche pas",       "content_fr": "<2-4 phrases FR, LA faiblesse principale>"}},
    "english_habits":    {{"title_fr": "Habitudes anglaises",        "content_fr": "<2-4 phrases FR, 1-3 exemples concrets>"}},
    "structure_quality": {{"title_fr": "Structure et construction",  "content_fr": "<2-4 phrases FR, architecture + organisation>"}}
  }},
  "next_step": "<in {ui_language_name} — UNE seule directive impérative et concrète pour la prochaine rédaction>",
  "{exam_profile_namespace}": {{
    "overall_score": <float 0-20 — mean of the criteria, rounded to 1 decimal>,
    "criteria": [
      {{
        "criterion_key": "<key from the profile criteria list above>",
        "score": <0-20>,
        "examiner_remark_fr": "<FR uniquement, 1-2 phrases, évaluation pure — jamais de citation ou de transformation>",
        "teacher_coaching": {{
          "coaching_en": "<ALWAYS in English, cites student's EXACT words>",
          "coaching_fr": "<ALWAYS a French example (learning material)>",
          "transformation": "<in {ui_language_name} — one concrete action for the next attempt>"
        }}
      }}
    ]
  }}
}}"""


async def analyze_writing(
    student_text: str,
    prompt_text: str,
    prompt_type: str,
    target_level: str = "B2",
    ui_language: str = "en",
    exam_profile: str | ExamProfile = "tcf_canada",
) -> dict:
    """Analyze a student's written French production using the 4-layer framework
    plus the selected exam profile's official criteria (default: TCF Canada).
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
    result = {
        "overall_score": 12.0,
        "word_count": wc,
        "summary": f"[DEMO] Received {wc} words. Configure ANTHROPIC_API_KEY for real analysis.",
        "errors": [
            {
                "layer": 1,
                "layer_name": "Sentence Architecture",
                "original_text": "[DEMO] Example error",
                "corrected_text": "[DEMO] Corrected version",
                "explanation_english": "[DEMO] Configure API key for real feedback.",
                "severity": "moderate",
            }
        ],
        "strengths": ["[DEMO] Text was submitted successfully."],
        "next_steps": ["[DEMO] Configure ANTHROPIC_API_KEY in .env for real analysis."],
        profile.namespace: {"overall_score": 12.0, "criteria": demo_criteria},
    }
    result["exam_profile"] = _normalize_writing_profile(result, profile)
    return result
