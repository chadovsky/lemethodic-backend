"""F-080b — Module detection via Claude API.

One Claude call per analyzer (T1/T2/T3). Runs after the existing
4-couche analysis and adds ``detected_modules`` + ``primary_module``
to the result dict. Same layered pattern as the Yarden call in T2 and
the argumentation call in T3 — keeps the heavy SYSTEM_PROMPT_DIAGNOSTIC
in analysis.py untouched and isolates the detection logic for testing.

Hard contract with the model:
- module_id values MUST come from the injected library
- empty detected_modules is a valid result (no hallucinated forced match)
- primary_module is null when detected_modules is empty
- a hallucinated module_id reaching the persistence layer is dropped
  there (see module_library.persist_detected_modules)
"""
from __future__ import annotations

import json
import logging
from typing import Literal

from sqlalchemy.orm import Session

from app.config import settings
from app.services.analysis import _call_claude
from app.services.module_library import fetch_active_modules_for_prompt

logger = logging.getLogger(__name__)


TacheModeForDetection = Literal["tache_1", "tache_2", "tache_3"]


# Per-Tâche category-priority instructions. Implemented as prompt
# guidance, NOT a hard filter — Claude should still detect modules from
# any category whose criteria match, just rank within the priority set
# when forming primary_module. Categories outside the priority set still
# surface in detected_modules with their natural confidence.
_CATEGORY_WEIGHTS: dict[str, str] = {
    "tache_1": (
        "Priority categories for ranking detections in this Tâche 1 "
        "(personal interview) session: discourse_structure, "
        "register_mismatch, vocab_calque. These categories surface most "
        "prominently in interview contexts. Modules from other "
        "categories (grammar_interference, pronunciation, word_order, "
        "verb_aspect, other) MUST still be detected when their criteria "
        "match — only the ranking of primary_module weighs categories."
    ),
    "tache_2": (
        "Priority categories for ranking detections in this Tâche 2 "
        "(role-play) session: register_mismatch, vocab_calque, "
        "grammar_interference. These categories surface most prominently "
        "in role-play contexts. Modules from other categories MUST still "
        "be detected when their criteria match — only the ranking of "
        "primary_module weighs categories."
    ),
    "tache_3": (
        "Priority categories for ranking detections in this Tâche 3 "
        "(argumentative monologue) session: discourse_structure, "
        "verb_aspect, word_order. These categories surface most "
        "prominently in monologue contexts. Modules from other "
        "categories MUST still be detected when their criteria match — "
        "only the ranking of primary_module weighs categories."
    ),
}


_DETECTION_SYSTEM = """You are a French-language L1-interference detector for FluentPath, a TCF Expression Orale prep app for English speakers learning French.

Your job: given a candidate's transcript and the active module library below, identify which modules' detection criteria match patterns observed in the candidate's speech.

═══════════════════════════════════════════════════════════
ACTIVE MODULE LIBRARY (the ONLY module_ids you may emit):
═══════════════════════════════════════════════════════════

{module_library}

═══════════════════════════════════════════════════════════
TÂCHE-SPECIFIC PRIORITY
═══════════════════════════════════════════════════════════

{category_weighting}

═══════════════════════════════════════════════════════════
DETECTION RULES
═══════════════════════════════════════════════════════════

1. For each module above, decide whether the candidate's transcript shows the patterns described in keywords_wrong, grammatical_signals, AND/OR contextual_triggers. A match on any one of those signal types is sufficient — you don't need all three.

2. For every match, emit a detection entry with:
   - module_id: the EXACT id from the library above (case-sensitive). NEVER invent an id. NEVER use a synonym or paraphrase of an id. If the candidate shows a pattern that doesn't fit any module above, omit it from output.
   - confidence: a float in [0, 1]. Use 0.85+ when keywords_wrong appear verbatim or grammatical_signals are unmistakable. Use 0.55–0.75 when the pattern is suggested but the supporting quote is short or ambiguous. Below 0.4: don't emit — false detections degrade student trust more than missed detections.
   - supporting_quote: an EXACT verbatim phrase from the candidate's transcript that triggered the detection. Do NOT paraphrase. Do NOT synthesize. If you cannot point to an exact phrase, do not emit the detection.

3. primary_module: among the detections you emit, pick the one with highest combined (priority-category-weight × severity × confidence) as primary_module. If you emit zero detections, primary_module MUST be null.

4. Empty result is valid and EXPECTED for clean speech. If no module from the library above matches the candidate's transcript, return:
   {{"detected_modules": [], "primary_module": null}}
   Do NOT force-match a module that doesn't fit. Do NOT invent module_ids.

═══════════════════════════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════════════════════════

Return ONLY a JSON object, no preamble, no code fences:

{{
  "detected_modules": [
    {{
      "module_id": "<exact id from library>",
      "confidence": <float 0..1>,
      "supporting_quote": "<exact phrase from candidate transcript>"
    }}
  ],
  "primary_module": "<module_id of the highest-priority detection, or null>"
}}
"""


_EMPTY_RESULT: dict = {"detected_modules": [], "primary_module": None}


async def detect_modules(
    transcript: str,
    tache_mode: TacheModeForDetection,
    db: Session,
) -> dict:
    """Call Claude with the active module library + transcript; return
    a normalized ``{"detected_modules": [...], "primary_module": ...}``
    dict. Never raises — degrades to ``_EMPTY_RESULT`` on any failure.

    Called from each analyzer (analyze_tache_1/2/3) AFTER the existing
    4-couche analysis. The result is merged into the analyzer's output
    dict and persisted by ``module_library.persist_detected_modules``
    in the finalize path.
    """
    transcript = (transcript or "").strip()
    if not transcript:
        logger.info(
            "F-080b detect_modules: empty transcript for tache_mode=%s; "
            "returning empty result.",
            tache_mode,
        )
        return dict(_EMPTY_RESULT)

    if tache_mode not in _CATEGORY_WEIGHTS:
        logger.warning(
            "F-080b detect_modules: unknown tache_mode=%r; returning empty.",
            tache_mode,
        )
        return dict(_EMPTY_RESULT)

    module_library = fetch_active_modules_for_prompt(db)
    if not module_library:
        # No active modules → no detection possible. Empty result is
        # honest here — F-080a's seeds should always populate at least
        # the two starter modules, so this branch only fires on a
        # broken/empty DB.
        logger.info(
            "F-080b detect_modules: empty module library; returning empty result."
        )
        return dict(_EMPTY_RESULT)

    if not settings.ANTHROPIC_API_KEY:
        # Demo mode: no fake detections. Empty result is the honest
        # answer when we can't actually run the model.
        logger.info(
            "F-080b detect_modules: ANTHROPIC_API_KEY absent; returning "
            "empty result (demo mode)."
        )
        return dict(_EMPTY_RESULT)

    system_prompt = _DETECTION_SYSTEM.replace(
        "{module_library}", module_library
    ).replace(
        "{category_weighting}", _CATEGORY_WEIGHTS[tache_mode]
    )
    user_msg = (
        f"Tâche: {tache_mode}\n\n"
        f"Candidate transcript:\n\"\"\"\n{transcript}\n\"\"\""
    )

    try:
        raw = await _call_claude(system_prompt, user_msg)
    except Exception as exc:
        logger.warning(
            "F-080b detect_modules: Claude call failed for tache_mode=%s "
            "(%s); returning empty result.",
            tache_mode,
            exc,
        )
        return dict(_EMPTY_RESULT)

    return _coerce_detection_payload(raw, tache_mode)


def _coerce_detection_payload(raw, tache_mode: str) -> dict:
    """Normalize whatever Claude returned into the documented shape.
    Hallucinated module_ids are NOT filtered here — that's the
    persistence layer's job. We just shape the payload."""
    if isinstance(raw, str):
        # _call_claude returns str when JSON parsing failed. Try one
        # more loose extraction (sometimes the model wraps in prose).
        try:
            raw = json.loads(raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip())
        except json.JSONDecodeError:
            logger.warning(
                "F-080b detect_modules: Claude returned non-JSON for "
                "tache_mode=%s (preview: %r); returning empty.",
                tache_mode,
                str(raw)[:120],
            )
            return dict(_EMPTY_RESULT)

    if not isinstance(raw, dict):
        logger.warning(
            "F-080b detect_modules: unexpected payload shape (%s) for "
            "tache_mode=%s; returning empty.",
            type(raw).__name__,
            tache_mode,
        )
        return dict(_EMPTY_RESULT)

    detections_raw = raw.get("detected_modules", [])
    if not isinstance(detections_raw, list):
        logger.warning(
            "F-080b detect_modules: detected_modules is not a list "
            "(%s) for tache_mode=%s; coercing to empty.",
            type(detections_raw).__name__,
            tache_mode,
        )
        detections_raw = []

    primary = raw.get("primary_module")
    if primary is not None and not isinstance(primary, str):
        logger.warning(
            "F-080b detect_modules: primary_module has non-string type "
            "(%s) for tache_mode=%s; nulling.",
            type(primary).__name__,
            tache_mode,
        )
        primary = None
    if isinstance(primary, str):
        primary = primary.strip() or None

    # Shape-guard each detection — we keep the row even if confidence is
    # missing/nonsense; the persistence helper handles those edge cases
    # and writes NULL where needed.
    cleaned: list[dict] = []
    for entry in detections_raw:
        if not isinstance(entry, dict):
            continue
        cleaned.append({
            "module_id": entry.get("module_id"),
            "confidence": entry.get("confidence"),
            "supporting_quote": entry.get("supporting_quote"),
        })

    if not cleaned:
        # Empty detections + non-null primary is incoherent — null it.
        primary = None

    return {"detected_modules": cleaned, "primary_module": primary}
