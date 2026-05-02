"""Tâche 2 analysis engine — F-049.

Tâche 2 of the TCF Expression Orale is a candidate-driven role-play:
the candidate takes a defined role (customer, traveler, applicant) and
asks the AI-examiner-in-character targeted questions to extract a set
of data points. Scoring happens against the Yarden methodology:

- La Pyramide  — open with closed (yes/no) questions, drill into open ones
- Le Rebond    — bridging phrases (accusé / reformulation / zoom / surprise)
- Le Ciblage   — depth on 3 targets > surface on 5+

Entry points:
- ``generate_examiner_turn(conversation, scenario)`` — produce the next
  examiner-in-character turn. Unlike Tâche 1, there is NO opening turn:
  the candidate drives, the examiner reacts. Returns ``None`` when no
  candidate turn has happened yet.
- ``analyze_tache_2(conversation, ...)`` — aggregate analysis when the
  conversation ends. Calls the existing 4-couche engine with
  ``tache_mode="tache_2"`` weights plus a dedicated Yarden-scoring
  Claude call.

Personas live in ``app.services.personas.tache_2_examiner``; swap that
module to tune examiner behavior.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Iterable

import httpx

from app.config import settings
from app.services.analysis import analyze_transcript, _call_claude
from app.services.tache_rubric import apply_tache_rubric
from app.services.module_detector import detect_modules
from app.services.detection import detect_clusters
from app.schemas.detection import empty_payload
from app.services.personas.tache_2_examiner import (
    BEHAVIOR_RULES,
    MAX_CANDIDATE_TURNS_HARD,
    MAX_CANDIDATE_TURNS_HINT,
    build_persona,
)

logger = logging.getLogger(__name__)

_EXAMINER_MODEL = "claude-sonnet-4-20250514"
_EXAMINER_MAX_TOKENS = 200  # Tâche 2 answers are shorter than Tâche 1.

_YARDEN_MODEL = "claude-sonnet-4-20250514"


# ═══════════════════════════════════════════════════════════════
# Shared turn helpers (mirror tache_1 — could lift into a module later)
# ═══════════════════════════════════════════════════════════════

def _speaker(turn) -> str:
    return getattr(turn, "speaker", None) or (turn.get("speaker") if isinstance(turn, dict) else "")


def _text(turn) -> str:
    return getattr(turn, "text", None) or (turn.get("text") if isinstance(turn, dict) else "") or ""


def _candidate_turn_count(turns: Iterable) -> int:
    return sum(1 for t in turns if _speaker(t) == "candidate")


def _active_turns(conversation) -> list:
    """F-062.3: materialize conversation.turns filtered to non-superseded
    rows. Superseded turns (Refaire cette prise) are retakes the candidate
    rejected and must not feed into examiner-prompt context or analysis."""
    raw = list(getattr(conversation, "turns", []) or [])
    return [t for t in raw if getattr(t, "superseded_at", None) is None]


def _build_messages_from_turns(turns: Iterable) -> list[dict]:
    """Alternating user/assistant message list for Claude. Candidate =
    user, examiner = assistant. Collapses adjacent same-speaker turns."""
    messages: list[dict] = []
    for turn in turns:
        role = "user" if _speaker(turn) == "candidate" else "assistant"
        content = _text(turn).strip() or "(silence)"
        if messages and messages[-1]["role"] == role:
            messages[-1]["content"] += "\n" + content
        else:
            messages.append({"role": role, "content": content})
    # Claude messages API requires first message from user. T2 opens
    # with the candidate by design, so this guard rarely fires — but
    # keep it defensive.
    if messages and messages[0]["role"] == "assistant":
        messages.insert(0, {"role": "user", "content": "(start)"})
    return messages


# ═══════════════════════════════════════════════════════════════
# Examiner generation (runs after each candidate turn)
# ═══════════════════════════════════════════════════════════════

async def generate_examiner_turn(conversation, scenario) -> str | None:
    """Produce the next examiner-in-character utterance.

    Tâche 2 is candidate-driven — unlike Tâche 1 there's no opening
    examiner turn. If the candidate hasn't spoken yet, return ``None``
    and let the router skip appending an examiner turn.
    """
    turns = _active_turns(conversation)

    if _candidate_turn_count(turns) == 0:
        return None

    # Demo mode: plausible fallback so the conversation still runs
    # without burning API credits (handy for manual QA).
    if not settings.ANTHROPIC_API_KEY:
        return "D'accord, pouvez-vous préciser ?"

    system = build_persona(scenario)
    messages = _build_messages_from_turns(turns)

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": _EXAMINER_MODEL,
                    "max_tokens": _EXAMINER_MAX_TOKENS,
                    "system": system,
                    "messages": messages,
                },
            )
            resp.raise_for_status()
            data = resp.json()
        text = (data.get("content", [{}])[0].get("text") or "").strip()
    except Exception as exc:
        logger.warning("F-049 examiner generation failed: %s", exc)
        # Stay in character even on error — don't leak a 500 into the
        # conversation transcript.
        return "Pardon ? Pouvez-vous reformuler ?"

    if not text:
        return "Pardon ? Pouvez-vous reformuler ?"
    if text.startswith(("{", "[", "```")):
        logger.warning("F-049 examiner returned non-prose (%r) — swallowing", text[:60])
        return "Pardon ? Pouvez-vous reformuler ?"
    return text


# ═══════════════════════════════════════════════════════════════
# Yarden methodology scoring
# ═══════════════════════════════════════════════════════════════

_YARDEN_SYSTEM = """You are evaluating a TCF Tâche 2 candidate's questioning strategy against the Yarden methodology. The methodology has three principles:

1. LA PYRAMIDE — open with closed (yes/no) questions to collect factual scaffolding, then move to open questions to drill into specific data points. Counter-intuitive for anglophones who default to open questions immediately.

2. LE REBOND — bridge phrases that turn two consecutive questions into a conversation rather than an interrogation. Four families:
   - Accusé de réception ("Ah d'accord", "Très bien", "Je vois")
   - Reformulation ("Donc si je comprends bien...", "Vous voulez dire que...")
   - Zoom ("Et plus précisément...", "Pouvez-vous me donner un exemple ?")
   - Surprise / réaction ("Vraiment ?", "C'est étonnant", "Je ne savais pas")

3. LE CIBLAGE — depth on 3 specific data targets rather than surface on 5+. Strategic curiosity over completionist information-gathering.

Given the candidate's questions in order and the data targets they were trying to extract, score each principle 0-5 and give a brief bilingual verdict.

Return JSON:
{
  "pyramide": {"score": int, "verdict_fr": "...", "verdict_en": "...", "verdict_es": "..."},
  "rebond":   {"score": int, "verdict_fr": "...", "verdict_en": "...", "verdict_es": "..."},
  "ciblage":  {"score": int, "verdict_fr": "...", "verdict_en": "...", "verdict_es": "..."},
  "data_targets_hit":    ["destinations disponibles", ...],
  "data_targets_missed": ["activités incluses", ...]
}

Return ONLY JSON, no preamble."""


def _scenario_data_targets(scenario) -> list[str]:
    if scenario is None:
        return []
    raw = getattr(scenario, "data_targets", None)
    if isinstance(raw, list):
        return [str(x) for x in raw]
    if isinstance(raw, str):
        try:
            decoded = json.loads(raw)
            return [str(x) for x in decoded] if isinstance(decoded, list) else []
        except json.JSONDecodeError:
            return []
    return []


def _yarden_fallback(data_targets: list[str]) -> dict:
    """Used when ANTHROPIC_API_KEY is absent or the call fails. Keeps
    the feedback page populated without pretending to score."""
    none_fr = "Analyse Yarden indisponible — nouvelle tentative au prochain enregistrement."
    none_en = "Yarden analysis unavailable — will retry on next recording."
    none_es = "Análisis Yarden no disponible — se reintentará en la próxima grabación."
    def _stub():
        return {"score": 0, "verdict_fr": none_fr, "verdict_en": none_en, "verdict_es": none_es}
    return {
        "pyramide": _stub(),
        "rebond": _stub(),
        "ciblage": _stub(),
        "data_targets_hit": [],
        "data_targets_missed": list(data_targets),
    }


def _coerce_yarden(raw, data_targets: list[str]) -> dict:
    """Normalise whatever Claude returned into the documented shape.
    Scores outside 0-5 are clamped; missing subfields fall back to 0."""
    if not isinstance(raw, dict):
        return _yarden_fallback(data_targets)

    def _clean(block):
        if not isinstance(block, dict):
            block = {}
        try:
            s = int(block.get("score", 0))
        except (TypeError, ValueError):
            s = 0
        s = max(0, min(5, s))
        return {
            "score": s,
            "verdict_fr": str(block.get("verdict_fr", ""))[:300],
            "verdict_en": str(block.get("verdict_en", ""))[:300],
            "verdict_es": str(block.get("verdict_es", ""))[:300],
        }

    hit = raw.get("data_targets_hit") or []
    missed = raw.get("data_targets_missed") or []
    if not isinstance(hit, list):
        hit = []
    if not isinstance(missed, list):
        missed = []
    return {
        "pyramide": _clean(raw.get("pyramide")),
        "rebond": _clean(raw.get("rebond")),
        "ciblage": _clean(raw.get("ciblage")),
        "data_targets_hit": [str(x) for x in hit],
        "data_targets_missed": [str(x) for x in missed],
    }


async def _run_yarden_analysis(
    candidate_questions: list[str],
    conversation_transcript: str,
    data_targets: list[str],
) -> dict:
    if not settings.ANTHROPIC_API_KEY:
        return _yarden_fallback(data_targets)

    user_payload = {
        "data_targets": data_targets,
        "candidate_questions_in_order": candidate_questions,
        "full_conversation": conversation_transcript,
    }
    try:
        raw = await _call_claude(_YARDEN_SYSTEM, json.dumps(user_payload, ensure_ascii=False))
    except Exception as exc:
        logger.warning("F-049 Yarden analysis failed: %s", exc)
        return _yarden_fallback(data_targets)

    return _coerce_yarden(raw, data_targets)


# ═══════════════════════════════════════════════════════════════
# Tâche 2 analysis (runs on conversation completion)
# ═══════════════════════════════════════════════════════════════

def _build_candidate_transcript(turns: list) -> str:
    parts = [_text(t).strip() for t in turns if _speaker(t) == "candidate"]
    parts = [p for p in parts if p]
    return "\n—\n".join(parts)


def _build_full_transcript(turns: list) -> str:
    """Speaker-tagged transcript used by the Yarden call so the model
    sees what the examiner said too (Le Rebond needs that context)."""
    lines = []
    for t in turns:
        sp = _speaker(t)
        label = "Candidat" if sp == "candidate" else "Examinateur"
        body = _text(t).strip()
        if body:
            lines.append(f"{label}: {body}")
    return "\n".join(lines)


def _scenario_context(scenario) -> str:
    if scenario is None:
        return "Tâche 2 — Jeu de rôle (scénario inconnu)."
    title = (
        getattr(scenario, "title_fr", "")
        or getattr(scenario, "title_en", "")
        or getattr(scenario, "code", "")
        or "jeu de rôle"
    )
    register = getattr(scenario, "register", "") or ""
    return f"Tâche 2 — Jeu de rôle. Scénario: {title}. Registre: {register}."


async def analyze_tache_2(
    conversation=None,
    *,
    # Crossover kwargs — mirror tache_1 so the F-047 dispatcher still
    # works if anyone passes a flat transcript.
    transcript: str | None = None,
    **kwargs,
) -> dict:
    """Aggregate analysis for a completed Tâche 2 conversation.

    When ``conversation`` is provided the full multi-turn analysis runs;
    when only ``transcript`` is provided the function degrades to the
    legacy oral analyzer with the mode stamped.
    """
    if conversation is None:
        result = await analyze_transcript(transcript=transcript or "", **kwargs)
        if isinstance(result, dict):
            result["mode"] = "tache_2"
        return result

    scenario = getattr(conversation, "scenario", None)
    turns = _active_turns(conversation)
    candidate_turns = [t for t in turns if _speaker(t) == "candidate"]
    candidate_questions = [_text(t).strip() for t in candidate_turns if _text(t).strip()]
    candidate_transcript = _build_candidate_transcript(turns)
    full_transcript = _build_full_transcript(turns)
    data_targets = _scenario_data_targets(scenario)

    forwarded = {
        "topic": _scenario_context(scenario),
        "target_level": kwargs.get("target_level", "B2"),
        "ui_language": kwargs.get("ui_language", "en"),
        "low_confidence_words": kwargs.get("low_confidence_words", []),
        "exam_profile": kwargs.get("exam_profile", "tcf_canada"),
    }
    # F-083 — fire the per-Tâche pedagogical rubric in parallel with
    # the existing diagnostic call so total latency stays at max() of
    # the two. Yarden runs sequentially after — it depends on the same
    # Claude Sonnet quota budget but its prompt is conversation-shape
    # specific and shorter; not worth a third gather slot.
    result, tache_rubric = await asyncio.gather(
        analyze_transcript(transcript=candidate_transcript, **forwarded),
        apply_tache_rubric("tache_2", candidate_transcript, _scenario_context(scenario)),
    )
    if not isinstance(result, dict):
        result = {"raw": str(result)}
    result["mode"] = "tache_2"
    result["tache_rubric"] = tache_rubric

    yarden = await _run_yarden_analysis(
        candidate_questions=candidate_questions,
        conversation_transcript=full_transcript,
        data_targets=data_targets,
    )
    yarden_total = (
        yarden["pyramide"]["score"]
        + yarden["rebond"]["score"]
        + yarden["ciblage"]["score"]
    )

    result["tache_2"] = {
        "scenario_code": getattr(scenario, "code", None),
        "scenario_title_fr": getattr(scenario, "title_fr", None),
        "scenario_register": getattr(scenario, "register", None),
        "scenario_difficulty": getattr(scenario, "difficulty", None),
        "candidate_turn_count": len(candidate_turns),
        "total_candidate_words": sum(len(q.split()) for q in candidate_questions),
        "data_targets": data_targets,
        "yarden": yarden,
        "yarden_total": yarden_total,
        "yarden_max": 15,
        "max_candidate_turns_hard": MAX_CANDIDATE_TURNS_HARD,
        "max_candidate_turns_hint": MAX_CANDIDATE_TURNS_HINT,
    }

    # F-080b: module detection. Same pattern as tache_1 — runs over the
    # candidate-only transcript (Yarden-relevant questioning strategy is
    # scored above; module detection is about L1-interference patterns
    # in the candidate's own utterances).
    db = kwargs.get("db")
    if db is not None:
        detection = await detect_modules(candidate_transcript, "tache_2", db)
        result["detected_modules"] = detection["detected_modules"]
        result["primary_module"] = detection["primary_module"]
        # P-200: cluster detection runs after F-080b. Persistence happens
        # in conversations.py /end. Never raises.
        result["cluster_findings_payload"] = await detect_clusters(
            candidate_transcript, "tache_2", db
        )
    else:
        result["detected_modules"] = []
        result["primary_module"] = None
        result["cluster_findings_payload"] = empty_payload()

    return result
