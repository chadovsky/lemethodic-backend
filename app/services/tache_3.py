"""Tâche 3 analysis engine — F-051.

Tâche 3 of the TCF Expression Orale is the argumentative monologue —
single recording, no interaction, opinion + justification + structure.
This module:

- Exposes ``analyze_tache_3`` as the dispatcher-facing entry point.
  Signature accepts the legacy ``transcript`` kwarg so the F-047 router
  already in production keeps working.
- Runs the standard 4-couche analysis via ``analyze_transcript`` with
  Tâche-3-specific prompt framing (the candidate's prompt is passed in
  via ``topic`` so the grader knows what was asked).
- Adds a dedicated Tâche-3 "argumentation" scoring pass via Sonnet: 5
  sub-scores (Structure, Argumentation, Nuance, Connectors, Personal
  Position), a ``tache_3_argumentation_total`` out of 25, plus a list
  of missing connectors and a one-paragraph "weakest argument"
  diagnostic.

The scoring weights for the overall /20 are owned by F-047's
``SCORING_PROFILES["tache_3"]`` and applied at persistence time by the
recordings router; this module does not compute the weighted overall.
"""
from __future__ import annotations

import asyncio
import json
import logging

from app.config import settings
from app.services.analysis import analyze_transcript, _call_claude
from app.services.tache_rubric import apply_tache_rubric
from app.services.module_detector import detect_modules
from app.services.detection import detect_clusters
from app.schemas.detection import empty_payload

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# Argumentation scoring prompt
# ═══════════════════════════════════════════════════════════════

_ARG_SYSTEM = """You are evaluating a TCF Tâche 3 argumentative monologue. The candidate was asked: {PROMPT}. They responded: {TRANSCRIPT}.

Score these specific Tâche 3 dimensions (0-5 each):

1. STRUCTURE — Did the response have a clear introduction, 2-3 arguments, and a conclusion? Or was it a stream-of-consciousness?

2. ARGUMENTATION — Did each argument have a claim + a justification (example, evidence, reasoning)? Or were they bare assertions?

3. NUANCE — Did the candidate acknowledge the opposing view at any point ("Certes... mais...", "On pourrait penser que..., cependant...")? TCF Tâche 3 rewards intellectual maturity over confident one-sidedness.

4. CONNECTORS — Did they use varied discourse markers (D'abord / Ensuite / Enfin; D'une part / D'autre part; Néanmoins; Toutefois; Par conséquent)? Or just "et" repeated?

5. PERSONAL POSITION — Did they take a clear personal stance, or hedge throughout?

Return JSON:
{{
  "structure":        {{"score": int, "verdict_fr": "...", "verdict_en": "...", "verdict_es": "..."}},
  "argumentation":    {{"score": int, "verdict_fr": "...", "verdict_en": "...", "verdict_es": "..."}},
  "nuance":           {{"score": int, "verdict_fr": "...", "verdict_en": "...", "verdict_es": "..."}},
  "connectors":       {{"score": int, "verdict_fr": "...", "verdict_en": "...", "verdict_es": "..."}},
  "personal_position":{{"score": int, "verdict_fr": "...", "verdict_en": "...", "verdict_es": "..."}},
  "missing_connectors": ["d'une part / d'autre part", ...],
  "weakest_argument": "<one short paragraph diagnosing the weakest argument in the response>"
}}

Return ONLY JSON, no preamble."""


_DIMENSIONS = ("structure", "argumentation", "nuance", "connectors", "personal_position")


def _argumentation_fallback() -> dict:
    """Returned when the Sonnet call can't run (no key, timeout,
    malformed response). Keeps the feedback page populated and signals
    to the UI that a re-run may help."""
    none_fr = "Analyse de l'argumentation indisponible — essayez une nouvelle analyse."
    none_en = "Argumentation analysis unavailable — try re-analyzing."
    none_es = "Análisis de argumentación no disponible — intenta reanalizar."
    def _stub():
        return {"score": 0, "verdict_fr": none_fr, "verdict_en": none_en, "verdict_es": none_es}
    return {
        "structure": _stub(),
        "argumentation": _stub(),
        "nuance": _stub(),
        "connectors": _stub(),
        "personal_position": _stub(),
        "missing_connectors": [],
        "weakest_argument": "",
    }


def _coerce_argumentation(raw) -> dict:
    if not isinstance(raw, dict):
        return _argumentation_fallback()

    def _clean_dim(block):
        if not isinstance(block, dict):
            block = {}
        try:
            s = int(block.get("score", 0))
        except (TypeError, ValueError):
            s = 0
        s = max(0, min(5, s))
        return {
            "score": s,
            "verdict_fr": str(block.get("verdict_fr", ""))[:400],
            "verdict_en": str(block.get("verdict_en", ""))[:400],
            "verdict_es": str(block.get("verdict_es", ""))[:400],
        }

    out = {d: _clean_dim(raw.get(d)) for d in _DIMENSIONS}
    missing = raw.get("missing_connectors") or []
    if not isinstance(missing, list):
        missing = []
    out["missing_connectors"] = [str(x) for x in missing][:10]
    out["weakest_argument"] = str(raw.get("weakest_argument") or "")[:800]
    return out


async def _run_argumentation_analysis(prompt: str, transcript: str) -> dict:
    """One Sonnet call. Returns the coerced 5-dimension + extras block.
    Never raises — falls back to a safe placeholder on error."""
    if not settings.ANTHROPIC_API_KEY:
        return _argumentation_fallback()
    if not (transcript or "").strip():
        return _argumentation_fallback()

    # The system prompt is a format-string template on purpose so we can
    # ship the candidate's answer + prompt as the "system" payload.
    # _call_claude expects ready-to-send strings, so we interpolate here.
    system = _ARG_SYSTEM.replace("{PROMPT}", prompt.strip() or "(prompt manquant)").replace(
        "{TRANSCRIPT}", transcript.strip()
    )
    user_msg = (
        "Return the JSON object only. The prompt and transcript are already "
        "embedded in the system message above."
    )
    try:
        raw = await _call_claude(system, user_msg)
    except Exception as exc:
        logger.warning("F-051 argumentation analysis failed: %s", exc)
        return _argumentation_fallback()
    return _coerce_argumentation(raw)


# ═══════════════════════════════════════════════════════════════
# Public entry point
# ═══════════════════════════════════════════════════════════════

async def analyze_tache_3(
    *,
    # Dispatcher-facing kwargs — kept loose because the F-047 router
    # forwards whatever the recording-upload path collected. Unknown
    # extras (e.g. ``conversation``) are ignored.
    transcript: str | None = None,
    topic: str = "",
    target_level: str = "B2",
    ui_language: str = "en",
    low_confidence_words: list | None = None,
    exam_profile: str = "tcf_canada",
    # F-051: the router passes the Tâche 3 prompt here so the
    # argumentation analyzer can quote it back. When absent, falls back
    # to ``topic`` (the existing legacy slot used for the question).
    tache_3_prompt: str | None = None,
    **_kwargs,
) -> dict:
    """Analyze a Tâche 3 monologue recording.

    Runs ``analyze_transcript`` for the standard 4-couche output, then
    overlays Tâche 3 argumentation scoring (5 sub-scores + total +
    weakest argument diagnostic) under ``result["tache_3"]``.
    """
    # F-083 — fire the pedagogical rubric in parallel with the
    # existing 4-couche analysis. Argumentation analysis (T3 specialty
    # prompt from F-051) stays sequential afterwards.
    t3_prompt_or_topic = tache_3_prompt or topic or ""
    result, tache_rubric = await asyncio.gather(
        analyze_transcript(
            transcript=transcript or "",
            topic=t3_prompt_or_topic,
            target_level=target_level,
            ui_language=ui_language,
            low_confidence_words=low_confidence_words or [],
            exam_profile=exam_profile,
        ),
        apply_tache_rubric("tache_3", transcript or "", t3_prompt_or_topic),
    )
    if not isinstance(result, dict):
        result = {"raw": str(result)}
    result["mode"] = "tache_3"
    result["tache_rubric"] = tache_rubric

    argumentation = await _run_argumentation_analysis(
        prompt=tache_3_prompt or topic or "",
        transcript=transcript or "",
    )
    arg_total = sum(argumentation[d]["score"] for d in _DIMENSIONS)

    result["tache_3"] = {
        "prompt": tache_3_prompt or topic or "",
        "argumentation": argumentation,
        "tache_3_argumentation_total": arg_total,
        "tache_3_argumentation_max": 25,
    }

    # F-080b: module detection. T3 only ever runs through the
    # recordings.py upload path (no /end), so the router passes db
    # explicitly via _kwargs.
    db = _kwargs.get("db")
    if db is not None:
        detection = await detect_modules(transcript or "", "tache_3", db)
        result["detected_modules"] = detection["detected_modules"]
        result["primary_module"] = detection["primary_module"]
        # P-200: cluster detection runs after F-080b, same sequential
        # pattern. Persistence happens in the recording-router's persist
        # path (recordings.py /upload). Never raises.
        result["cluster_findings_payload"] = await detect_clusters(
            transcript or "", "tache_3", db
        )
    else:
        result["detected_modules"] = []
        result["primary_module"] = None
        result["cluster_findings_payload"] = empty_payload()

    return result
