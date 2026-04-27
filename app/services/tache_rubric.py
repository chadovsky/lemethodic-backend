"""F-083 — Tâche-specific pedagogical rubric layer.

Three deadpan-English prompts (one per Tâche) that produce a per-recording
pedagogical rubric distinct from:
  - the generic 4-couche diagnostic in ``analysis.py::SYSTEM_PROMPT_DIAGNOSTIC``
    (la_carte, le_goulet, ce_qui_marche, corrections, transcription_corrigee)
  - the existing per-Tâche specialty prompts (T2 Yarden Pyramide/Rebond/
    Ciblage in ``tache_2._YARDEN_SYSTEM``; T3 argumentation in
    ``tache_3._ARG_SYSTEM``)

This is a third prompt category. Its output drives the F-084 "basic vs
detailed feedback rendering" frontend (next sprint ticket): summary
prose, Tâche-specific dimension scores with per-dimension prose,
universal sidebars (conjugation / grammar_structure /
sentence_construction), retry recommendation with threshold logic,
next-action suggestion.

Architecture choice (additive, not replacement):
- ``SYSTEM_PROMPT_DIAGNOSTIC`` keeps producing what F-088 frontend +
  scoring_profiles + the diagnostic page already consume.
- The Tâche specialty prompts (Yarden / argumentation) keep producing
  what F-080c diagnostic page already renders.
- This module's prompts add a NEW pedagogical-rubric layer alongside.
- Each ``analyze_tache_*`` runs the new rubric call in parallel with
  the existing diagnostic call (``asyncio.gather``) so the second
  Claude call doesn't stack latency.

Persistence: the rubric block is serialized to JSON and stored on the
new ``Feedback.tache_rubric_data`` TEXT column (migration:
``scripts/add_tache_rubric_data_column.py``). The column is nullable;
legacy recordings render with the rubric absent.
"""
from __future__ import annotations

import json
import logging

from app.config import settings
from app.services.analysis import _call_claude

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# Tâche 1 — Entretien dirigé sans préparation (2 min)
# ═══════════════════════════════════════════════════════════════

_RUBRIC_SYSTEM_T1 = """You are evaluating a TCF Tâche 1 — Entretien dirigé sans préparation. The candidate had 2 minutes to introduce themselves and answer the examiner's follow-ups.

The candidate's transcript is:
{TRANSCRIPT}

Examiner context (the questions the candidate was responding to):
{CONTEXT}

═══════════════════════════════════════════════════════════
PEDAGOGICAL LENS — read before scoring
═══════════════════════════════════════════════════════════
T1 is first-impression theatre. The examiner forms an auditory baseline in the first 30 seconds that anchors how they hear the next 11 minutes. Coverage matters: a student who only talks about work but never family or hobbies signals nervousness or limited range. Hesitations matter: T1 is short, and too many filler words make it impossible to cover the personal territory needed.

Voice: deadpan English. Honest. No false reassurance. Reads like a tutor who's seen this 7,000 hours of times before. Match the tone in the F-080d module copy already shipped.

═══════════════════════════════════════════════════════════
SCORE THESE FIVE T1 DIMENSIONS (0-5 each)
═══════════════════════════════════════════════════════════
1. premiere_impression — opening 30 seconds. Did the student greet, structure the intro, sound comfortable? Or did they freeze, ramble, or skip the salutation?
2. presentation_de_soi — coverage breadth across name / origin / profession / family / interests in 2 minutes. Did they give the examiner enough hooks for follow-up? A student who covers only work-and-name leaves the examiner with nothing to ask about.
3. lexique_identite — vocabulary range across personal domains. Repetition of "j'aime" + "je travaille" = A2 signal. Varied vocabulary across hobbies, work, life context = B1+. Cite specific phrases.
4. aisance_hesitations — pause count per 30 seconds, filler words ("euh", "ben", "comme"), self-corrections. Cite specific moments if you can hear them in the transcript.
5. prononciation — liaisons (les_amis vs les amis), vowel quality on tricky French sounds (u, é, è, eu), declarative vs interrogative intonation. Audible from the transcript only when the STT mistranscribed a specific word — flag those.

═══════════════════════════════════════════════════════════
RETRY THRESHOLD
═══════════════════════════════════════════════════════════
Recommend retry if ANY dimension scores below 2/5, OR overall T1 average < 2.5/5. Reason field cites the specific dimension(s) that triggered.

═══════════════════════════════════════════════════════════
NARRATIVE SUMMARY (F-084 — generated AFTER all dimensions are scored)
═══════════════════════════════════════════════════════════
After scoring all dimensions, generate a `narrative_summary` field: a single English sentence summarizing this performance. Voice: deadpan tutor for English speakers studying French. Format: "{CEFR band}, headed to {next band}. {What's holding them back, in plain words}."

Examples:
- "B1+, headed to B2. Connectors are holding you back."
- "B2, ready to push for C1. Argumentation is solid; tighten your subjunctive."
- "A2+, foundation work needed. Article use is the first thing to fix."

ONE sentence. No preamble. No quotation marks. Match the tone of the examples.

═══════════════════════════════════════════════════════════
OUTPUT — JSON only, no preamble
═══════════════════════════════════════════════════════════
{{
  "summary_prose": "<2-3 paragraphs of deadpan English. What they did, what landed, what didn't. No false reassurance.>",
  "tache_specific_dimensions": [
    {{"key": "premiere_impression",  "score": <0-5>, "prose": "<1-2 sentences with a specific quote or moment>"}},
    {{"key": "presentation_de_soi",  "score": <0-5>, "prose": "<1-2 sentences>"}},
    {{"key": "lexique_identite",     "score": <0-5>, "prose": "<1-2 sentences>"}},
    {{"key": "aisance_hesitations",  "score": <0-5>, "prose": "<1-2 sentences>"}},
    {{"key": "prononciation",        "score": <0-5>, "prose": "<1-2 sentences>"}}
  ],
  "universal_sidebars": {{
    "conjugation":          {{"score": <0-5>, "examples": ["<1-2 specific examples from transcript>"]}},
    "grammar_structure":    {{"score": <0-5>, "examples": ["<1-2 specific examples>"]}},
    "sentence_construction":{{"score": <0-5>, "examples": ["<1-2 specific examples>"]}}
  }},
  "retry_recommendation": {{"should_retry": <true|false>, "reason": "<short — names the dimension(s) below threshold, or empty when no retry>"}},
  "next_action_suggestion": "<one sentence — points to a specific L'École lesson number, a recurring module pattern they should practice, or 'ready for next Tâche'>",
  "narrative_summary": "<single sentence per the NARRATIVE SUMMARY block above>"
}}"""


# ═══════════════════════════════════════════════════════════════
# Tâche 2 — Exercice en interaction avec préparation (5'30, 2 min prep)
# ═══════════════════════════════════════════════════════════════

_RUBRIC_SYSTEM_T2 = """You are evaluating a TCF Tâche 2 — Exercice en interaction avec préparation. The candidate had 2 minutes to prepare, then 5'30 of role-play with the AI examiner-in-character.

The candidate's transcript (combined across turns) is:
{TRANSCRIPT}

Scenario context (who the examiner was playing, what the candidate had to achieve):
{CONTEXT}

═══════════════════════════════════════════════════════════
PEDAGOGICAL LENS — read before scoring
═══════════════════════════════════════════════════════════
T2 is structured interaction, not free conversation. The consigne specifies WHO the interlocutor is and WHAT the candidate must achieve. A student who memorizes 5 questions and reads them in order without listening to the examiner's answers fails reactivité — even if their grammar is perfect. Real T2 success looks like a chain: question → listen to answer → follow-up question that builds on the answer. Register matters because mismatching tu/vous in a hotel-manager scenario telegraphs A2 before the examiner hears anything else.

Voice: deadpan English. Honest. Match the F-080d module-copy tone.

═══════════════════════════════════════════════════════════
SCORE THESE FIVE T2 DIMENSIONS (0-5 each)
═══════════════════════════════════════════════════════════
1. formation_questions — inversion ("Pouvez-vous..."), est-ce que constructions, question words (qui / que / quoi / où / quand / comment / pourquoi / combien). T2 IS questions; this is the foundation skill.
2. registre_approprie — tu/vous appropriate to the scenario interlocutor (hotel manager = vous; neighbor = could be tu in informal scenarios). Formal markers (je voudrais, pourriez-vous, je me permets de) when context calls.
3. actes_de_parole — coverage of speech acts the scenario demands: requesting information, asking for clarification, suggesting alternatives, refusing politely, persuading.
4. reactivite — responding to examiner's answers vs robotically running through prepared questions. Did the student listen and follow up, or just plow through a script?
5. structuration_interactionnelle — opening politeness, body of question chain, closing thanks/conclusion.

═══════════════════════════════════════════════════════════
RETRY THRESHOLD
═══════════════════════════════════════════════════════════
Recommend retry if ANY dimension < 2/5, OR overall T2 average < 2.5/5, OR formation_questions specifically < 2.5/5 (without the foundation skill, T2 fails by definition). Reason field cites which.

═══════════════════════════════════════════════════════════
NARRATIVE SUMMARY (F-084 — generated AFTER all dimensions are scored)
═══════════════════════════════════════════════════════════
After scoring all dimensions, generate a `narrative_summary` field: a single English sentence summarizing this performance. Voice: deadpan tutor for English speakers studying French. Format: "{CEFR band}, headed to {next band}. {What's holding them back, in plain words}."

Examples:
- "B1+, headed to B2. Connectors are holding you back."
- "B2, ready to push for C1. Argumentation is solid; tighten your subjunctive."
- "A2+, foundation work needed. Article use is the first thing to fix."

ONE sentence. No preamble. No quotation marks. Match the tone of the examples.

═══════════════════════════════════════════════════════════
OUTPUT — JSON only, no preamble
═══════════════════════════════════════════════════════════
{{
  "summary_prose": "<2-3 paragraphs of deadpan English assessment.>",
  "tache_specific_dimensions": [
    {{"key": "formation_questions",          "score": <0-5>, "prose": "<1-2 sentences with a specific quote>"}},
    {{"key": "registre_approprie",           "score": <0-5>, "prose": "<1-2 sentences>"}},
    {{"key": "actes_de_parole",              "score": <0-5>, "prose": "<1-2 sentences>"}},
    {{"key": "reactivite",                   "score": <0-5>, "prose": "<1-2 sentences>"}},
    {{"key": "structuration_interactionnelle","score": <0-5>, "prose": "<1-2 sentences>"}}
  ],
  "universal_sidebars": {{
    "conjugation":          {{"score": <0-5>, "examples": ["<1-2 specific examples from transcript>"]}},
    "grammar_structure":    {{"score": <0-5>, "examples": ["<1-2 specific examples>"]}},
    "sentence_construction":{{"score": <0-5>, "examples": ["<1-2 specific examples>"]}}
  }},
  "retry_recommendation": {{"should_retry": <true|false>, "reason": "<short — names dimension(s) below threshold, or empty>"}},
  "next_action_suggestion": "<one sentence — specific L'École lesson, recurring module practice, or 'ready for next Tâche'>",
  "narrative_summary": "<single sentence per the NARRATIVE SUMMARY block above>"
}}"""


# ═══════════════════════════════════════════════════════════════
# Tâche 3 — Expression d'un point de vue sans préparation (4'30)
# ═══════════════════════════════════════════════════════════════

_RUBRIC_SYSTEM_T3 = """You are evaluating a TCF Tâche 3 — Expression d'un point de vue sans préparation. The candidate had 4'30 of spontaneous argumentation against examiner pushback.

The candidate's transcript is:
{TRANSCRIPT}

Prompt the candidate was responding to:
{CONTEXT}

═══════════════════════════════════════════════════════════
PEDAGOGICAL LENS — read before scoring
═══════════════════════════════════════════════════════════
T3 is the level-revealer. T1 can be coached with memorized self-presentation; T2 can survive on prepared questions; T3 cannot be faked. 4'30 of spontaneous argumentation under examiner pushback exposes whatever level the student actually has. The examiner is listening for: did they take a position, did they structure it, did they defend it without panicking when challenged. Length is its own diagnostic — minute 4 hesitation patterns reveal what minute 1 hides.

Voice: deadpan English. Honest. Match the F-080d module-copy tone.

═══════════════════════════════════════════════════════════
SCORE THESE SIX T3 DIMENSIONS (0-5 each)
═══════════════════════════════════════════════════════════
1. position_claire — clear pour/contre/nuancé statement in opening. Wandering openings = examiner can't anchor the argument.
2. argumentation_structuree — intro / 2-3 arguments developed / conclusion. THE T3 criterion examiners weight most.
3. connecteurs_logiques — d'une part / d'autre part, cependant, néanmoins, par conséquent, en revanche. Bare "et" repeated = low score.
4. developpement_thematique — each argument with example or justification, not bare assertion.
5. defense_calme — when the examiner pushes back, student holds position with nuance vs panic-flips. CEFR B2/C1 marker.
6. aisance_sous_pression — 4'30 spontaneous reveals real fatigue point. Hesitation patterns at minute 3-4 vs minute 1 show actual level.

═══════════════════════════════════════════════════════════
RETRY THRESHOLD
═══════════════════════════════════════════════════════════
Recommend retry if ANY dimension < 2/5, OR overall T3 average < 2.5/5, OR argumentation_structuree specifically < 2/5 (T3 without structure is just talking). Reason field cites which.

═══════════════════════════════════════════════════════════
NARRATIVE SUMMARY (F-084 — generated AFTER all dimensions are scored)
═══════════════════════════════════════════════════════════
After scoring all dimensions, generate a `narrative_summary` field: a single English sentence summarizing this performance. Voice: deadpan tutor for English speakers studying French. Format: "{CEFR band}, headed to {next band}. {What's holding them back, in plain words}."

Examples:
- "B1+, headed to B2. Connectors are holding you back."
- "B2, ready to push for C1. Argumentation is solid; tighten your subjunctive."
- "A2+, foundation work needed. Article use is the first thing to fix."

ONE sentence. No preamble. No quotation marks. Match the tone of the examples.

═══════════════════════════════════════════════════════════
OUTPUT — JSON only, no preamble
═══════════════════════════════════════════════════════════
{{
  "summary_prose": "<2-3 paragraphs of deadpan English assessment.>",
  "tache_specific_dimensions": [
    {{"key": "position_claire",          "score": <0-5>, "prose": "<1-2 sentences with a specific quote>"}},
    {{"key": "argumentation_structuree", "score": <0-5>, "prose": "<1-2 sentences>"}},
    {{"key": "connecteurs_logiques",     "score": <0-5>, "prose": "<1-2 sentences>"}},
    {{"key": "developpement_thematique", "score": <0-5>, "prose": "<1-2 sentences>"}},
    {{"key": "defense_calme",            "score": <0-5>, "prose": "<1-2 sentences>"}},
    {{"key": "aisance_sous_pression",    "score": <0-5>, "prose": "<1-2 sentences>"}}
  ],
  "universal_sidebars": {{
    "conjugation":          {{"score": <0-5>, "examples": ["<1-2 specific examples from transcript>"]}},
    "grammar_structure":    {{"score": <0-5>, "examples": ["<1-2 specific examples>"]}},
    "sentence_construction":{{"score": <0-5>, "examples": ["<1-2 specific examples>"]}}
  }},
  "retry_recommendation": {{"should_retry": <true|false>, "reason": "<short — names dimension(s) below threshold, or empty>"}},
  "next_action_suggestion": "<one sentence — specific L'École lesson, recurring module practice, or 'ready for next Tâche'>",
  "narrative_summary": "<single sentence per the NARRATIVE SUMMARY block above>"
}}"""


# ═══════════════════════════════════════════════════════════════
# Dimension keys per Tâche (canonical order; mirrors prompt output)
# ═══════════════════════════════════════════════════════════════

_T1_DIMENSIONS = (
    "premiere_impression",
    "presentation_de_soi",
    "lexique_identite",
    "aisance_hesitations",
    "prononciation",
)
_T2_DIMENSIONS = (
    "formation_questions",
    "registre_approprie",
    "actes_de_parole",
    "reactivite",
    "structuration_interactionnelle",
)
_T3_DIMENSIONS = (
    "position_claire",
    "argumentation_structuree",
    "connecteurs_logiques",
    "developpement_thematique",
    "defense_calme",
    "aisance_sous_pression",
)

_DIMENSIONS_BY_MODE = {
    "tache_1": _T1_DIMENSIONS,
    "tache_2": _T2_DIMENSIONS,
    "tache_3": _T3_DIMENSIONS,
}

_PROMPT_BY_MODE = {
    "tache_1": _RUBRIC_SYSTEM_T1,
    "tache_2": _RUBRIC_SYSTEM_T2,
    "tache_3": _RUBRIC_SYSTEM_T3,
}

_SIDEBAR_KEYS = ("conjugation", "grammar_structure", "sentence_construction")


# ═══════════════════════════════════════════════════════════════
# Threshold logic — independent from the LLM's self-reported retry flag
# so the backend has a deterministic check the LLM can't drift on.
# ═══════════════════════════════════════════════════════════════

def _enforce_threshold(tache_mode: str, dimensions: list[dict]) -> dict:
    """Compute the deterministic retry recommendation from dimension
    scores. Used to verify and override the LLM's self-reported flag —
    the LLM is asked to set the flag, but we recompute here so a noisy
    response can't ship a "should_retry: false" when the scores say
    otherwise. Returns ``{"should_retry": bool, "reason": str}``.
    """
    scores = {d.get("key"): d.get("score", 0) for d in dimensions if isinstance(d, dict)}
    if not scores:
        return {"should_retry": False, "reason": ""}

    avg = sum(scores.values()) / len(scores)
    below_2 = [k for k, v in scores.items() if v < 2]

    triggers: list[str] = []
    if below_2:
        triggers.append(f"dimension(s) below 2/5: {', '.join(below_2)}")
    if avg < 2.5:
        triggers.append(f"average {avg:.1f}/5 below 2.5/5")

    # Per-Tâche foundation-dimension overrides
    if tache_mode == "tache_2" and scores.get("formation_questions", 5) < 2.5:
        triggers.append("formation_questions below 2.5/5 — foundation skill failure")
    if tache_mode == "tache_3" and scores.get("argumentation_structuree", 5) < 2:
        triggers.append("argumentation_structuree below 2/5 — T3 without structure")

    if triggers:
        return {"should_retry": True, "reason": "; ".join(triggers)}
    return {"should_retry": False, "reason": ""}


# ═══════════════════════════════════════════════════════════════
# Defensive coercion + fallback (mirrors the F-051 / F-049 patterns)
# ═══════════════════════════════════════════════════════════════

def _coerce_dimension(raw, expected_key: str) -> dict:
    if not isinstance(raw, dict):
        raw = {}
    try:
        s = int(raw.get("score", 0))
    except (TypeError, ValueError):
        s = 0
    s = max(0, min(5, s))
    return {
        "key": expected_key,
        "score": s,
        "prose": str(raw.get("prose", ""))[:600],
    }


def _coerce_sidebar(raw) -> dict:
    if not isinstance(raw, dict):
        raw = {}
    try:
        s = int(raw.get("score", 0))
    except (TypeError, ValueError):
        s = 0
    s = max(0, min(5, s))
    examples = raw.get("examples") or []
    if not isinstance(examples, list):
        examples = []
    return {
        "score": s,
        "examples": [str(e)[:240] for e in examples[:3]],
    }


def _coerce_rubric(raw, tache_mode: str) -> dict:
    expected_dims = _DIMENSIONS_BY_MODE.get(tache_mode, ())
    if not isinstance(raw, dict):
        raw = {}

    raw_dims = raw.get("tache_specific_dimensions")
    if not isinstance(raw_dims, list):
        raw_dims = []
    by_key = {d.get("key"): d for d in raw_dims if isinstance(d, dict)}
    dimensions = [_coerce_dimension(by_key.get(k), k) for k in expected_dims]

    raw_sidebars = raw.get("universal_sidebars")
    if not isinstance(raw_sidebars, dict):
        raw_sidebars = {}
    sidebars = {k: _coerce_sidebar(raw_sidebars.get(k)) for k in _SIDEBAR_KEYS}

    raw_retry = raw.get("retry_recommendation")
    llm_retry = (
        {"should_retry": bool(raw_retry.get("should_retry")), "reason": str(raw_retry.get("reason", ""))[:240]}
        if isinstance(raw_retry, dict)
        else {"should_retry": False, "reason": ""}
    )
    deterministic_retry = _enforce_threshold(tache_mode, dimensions)

    # Override the LLM flag with the deterministic check, but preserve
    # the LLM's reason as a secondary note when it disagrees in the
    # "should retry" direction (sometimes the model spots something the
    # threshold logic doesn't).
    final_retry = dict(deterministic_retry)
    if llm_retry["should_retry"] and not deterministic_retry["should_retry"] and llm_retry["reason"]:
        final_retry = {
            "should_retry": True,
            "reason": f"LLM-flagged: {llm_retry['reason']}",
        }

    return {
        "tache_mode": tache_mode,
        "summary_prose": str(raw.get("summary_prose", ""))[:2400],
        "tache_specific_dimensions": dimensions,
        "universal_sidebars": sidebars,
        "retry_recommendation": final_retry,
        "next_action_suggestion": str(raw.get("next_action_suggestion", ""))[:400],
        # F-084 — single-sentence diagnostic hero. Cap at 240 chars: the
        # spec asks for one sentence and the LLM occasionally drifts
        # into two; trim hard rather than ship a wall of text into the
        # hero slot.
        "narrative_summary": str(raw.get("narrative_summary", ""))[:240],
    }


def _rubric_fallback(tache_mode: str) -> dict:
    """Returned on no-key / timeout / malformed response. Keeps the
    response shape stable so the frontend renders gracefully rather
    than guarding every field. Marks `should_retry=False` since we
    have no signal."""
    expected_dims = _DIMENSIONS_BY_MODE.get(tache_mode, ())
    return {
        "tache_mode": tache_mode,
        "summary_prose": "",
        "tache_specific_dimensions": [
            {"key": k, "score": 0, "prose": ""} for k in expected_dims
        ],
        "universal_sidebars": {k: {"score": 0, "examples": []} for k in _SIDEBAR_KEYS},
        "retry_recommendation": {"should_retry": False, "reason": ""},
        "next_action_suggestion": "",
        # F-084 — empty narrative on fallback. Frontend treats empty
        # string the same as missing field and falls back to the
        # cefr-band default heading.
        "narrative_summary": "",
    }


# ═══════════════════════════════════════════════════════════════
# Public entry point — called from each analyze_tache_*
# ═══════════════════════════════════════════════════════════════

async def apply_tache_rubric(
    tache_mode: str,
    transcript: str,
    context: str = "",
) -> dict:
    """Run the F-083 pedagogical rubric prompt for the given Tâche.

    Always returns the canonical rubric shape — never raises. Falls
    back to ``_rubric_fallback`` on any error so the caller can merge
    unconditionally.
    """
    if tache_mode not in _PROMPT_BY_MODE:
        logger.warning("F-083 apply_tache_rubric: unknown tache_mode %r", tache_mode)
        return _rubric_fallback(tache_mode or "tache_3")

    if not (transcript or "").strip():
        return _rubric_fallback(tache_mode)

    if not settings.ANTHROPIC_API_KEY:
        return _rubric_fallback(tache_mode)

    system = _PROMPT_BY_MODE[tache_mode].replace(
        "{TRANSCRIPT}", transcript.strip()
    ).replace(
        "{CONTEXT}", (context or "").strip() or "(no additional context)"
    )
    user_msg = (
        "Return the JSON object only. Transcript and context are embedded "
        "in the system message above."
    )

    try:
        raw = await _call_claude(system, user_msg)
    except Exception as exc:
        logger.warning("F-083 rubric call failed (%s): %s", tache_mode, exc)
        return _rubric_fallback(tache_mode)

    return _coerce_rubric(raw, tache_mode)
