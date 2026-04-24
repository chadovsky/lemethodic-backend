"""Tâche 1 analysis engine — F-048.

Tâche 1 of the TCF Expression Orale is a multi-turn conversation: the
examiner prompts a self-presentation, then probes with 2–4 follow-ups
tailored to what the candidate said. This module owns two entry points:

- ``generate_examiner_turn(conversation)`` — asks Claude Sonnet to
  produce the next examiner utterance given the turns so far. Opening
  turn is deterministic (random pick from OPENING_PROMPTS) to save the
  API call.
- ``analyze_tache_1(conversation, ...)`` — runs after the conversation
  is marked completed. Aggregates candidate turns into a combined
  transcript, calls the existing 4-couche analyzer with Tâche 1
  weights (via ``SCORING_PROFILES``), then layers on Tâche 1-specific
  dimensions: elaboration, naturalness, per-turn answered-check.

The persona lives in ``app.services.personas.tache_1_examiner`` — swap
that file to tune examiner behavior without touching this module.
"""
from __future__ import annotations

import json
import logging
from typing import Iterable

import httpx

from app.config import settings
from app.services.analysis import analyze_transcript, _call_claude
from app.services.personas.tache_1_examiner import (
    FALLBACK_CLOSE,
    MAX_CANDIDATE_TURNS,
    MIN_CANDIDATE_TURNS,
    PERSONA,
    OPENING_PROMPTS,
    random_opening,
)

logger = logging.getLogger(__name__)

# Examiner generation uses Sonnet; Opus is ~5× pricier and overkill for
# one-line conversational turns. If you need to change this, prefer
# overriding via the env var rather than hardcoding a second model id.
_EXAMINER_MODEL = "claude-sonnet-4-20250514"
_EXAMINER_MAX_TOKENS = 256

# Per-turn answered check runs AFTER all candidate turns are in. It's a
# single JSON-returning call, so Sonnet is fine here too.
_ANSWERED_CHECK_MODEL = "claude-sonnet-4-20250514"


# ═══════════════════════════════════════════════════════════════
# Examiner generation (runs between candidate turns)
# ═══════════════════════════════════════════════════════════════

def _candidate_turn_count(turns: Iterable) -> int:
    return sum(1 for t in turns if _speaker(t) == "candidate")


def _speaker(turn) -> str:
    # Works with both the ORM model and plain dicts — the router builds
    # turn snapshots in both shapes depending on entry path.
    return getattr(turn, "speaker", None) or (turn.get("speaker") if isinstance(turn, dict) else "")


def _text(turn) -> str:
    return getattr(turn, "text", None) or (turn.get("text") if isinstance(turn, dict) else "") or ""


def _active_turns(conversation) -> list:
    """F-062.3: materialize conversation.turns filtered to non-superseded
    rows. Mirrors the helper in tache_2.py — if/when these shared helpers
    get lifted into a common module, unify both copies."""
    raw = list(getattr(conversation, "turns", []) or [])
    return [t for t in raw if getattr(t, "superseded_at", None) is None]


def _build_messages_from_turns(turns: Iterable) -> list[dict]:
    """Convert the conversation's turn list into the alternating
    user/assistant message shape the Claude messages API expects.
    Candidate = user, examiner = assistant.

    Collapses adjacent same-speaker turns (shouldn't happen in practice
    but guards the API's strict alternation requirement).
    """
    messages: list[dict] = []
    for turn in turns:
        role = "user" if _speaker(turn) == "candidate" else "assistant"
        content = _text(turn).strip() or "(silence)"
        if messages and messages[-1]["role"] == role:
            messages[-1]["content"] += "\n" + content
        else:
            messages.append({"role": role, "content": content})
    # Claude's messages API requires the first message to be from the
    # user. If the first turn was the examiner (the normal case on
    # opening-then-reply), we add a zero-width user stub.
    if messages and messages[0]["role"] == "assistant":
        messages.insert(0, {"role": "user", "content": "(start)"})
    return messages


async def generate_examiner_turn(conversation) -> str:
    """Produce the next examiner utterance.

    ``conversation`` must expose a ``turns`` iterable of turns (each with
    ``speaker`` ∈ {"examiner","candidate"} and ``text``). The function is
    pure — it doesn't persist anything; callers append the returned
    string as a new turn.

    Returns the examiner's French utterance as a string. Never empty:
    falls back to FALLBACK_CLOSE if Claude returns nothing usable.
    """
    turns = _active_turns(conversation)

    # Opening turn: no API call. Save the tokens, keep the flow fast.
    if not turns:
        return random_opening()

    # If we've already hit the max number of candidate turns, close out
    # deterministically. Calling Claude with "please wrap up" instructions
    # is wasteful and fragile.
    if _candidate_turn_count(turns) >= MAX_CANDIDATE_TURNS:
        return FALLBACK_CLOSE

    # Demo mode: produce a plausible French follow-up without a real API call.
    if not settings.ANTHROPIC_API_KEY:
        return "Pouvez-vous m'en dire un peu plus sur ce point ?"

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
                    "system": PERSONA,
                    "messages": messages,
                },
            )
            resp.raise_for_status()
            data = resp.json()
        text = (data.get("content", [{}])[0].get("text") or "").strip()
    except Exception as exc:
        logger.warning("F-048 examiner generation failed, using fallback close: %s", exc)
        return FALLBACK_CLOSE

    if not text:
        return FALLBACK_CLOSE
    # Guard against the model slipping back into English or echoing JSON
    # — if it doesn't look like plain French prose, close out.
    if text.startswith(("{", "[", "```")):
        logger.warning("F-048 examiner returned non-prose (%r) — closing", text[:60])
        return FALLBACK_CLOSE
    return text


# ═══════════════════════════════════════════════════════════════
# Tâche 1 analysis (runs on conversation completion)
# ═══════════════════════════════════════════════════════════════

# Elaboration score thresholds (avg candidate words per turn).
# First-pass defaults — Chadi calibrates Day 7.
_ELABORATION_BANDS = (
    (80, 5),   # very elaborate (may also mean rambling — flag in result)
    (40, 4),   # good
    (20, 3),   # acceptable
    (10, 2),   # poor
    (0, 1),    # minimal
)


_NATURALNESS_VERDICTS: list[tuple[int, dict[str, str]]] = [
    (17, {
        "fr": "Échange naturel et fluide. Les réponses s'enchaînent bien avec les questions.",
        "en": "Natural, fluent exchange. Responses flow well from the examiner's questions.",
        "es": "Intercambio natural y fluido. Las respuestas fluyen bien desde las preguntas.",
    }),
    (13, {
        "fr": "Échange correct avec quelques hésitations visibles. À fluidifier.",
        "en": "Acceptable exchange with some visible hesitations. Work on smoothing out.",
        "es": "Intercambio correcto con algunas vacilaciones visibles. Hay que fluidificar.",
    }),
    (9, {
        "fr": "Échange haché. Hésitations et répétitions fréquentes. Travaillez l'aisance conversationnelle.",
        "en": "Choppy exchange with frequent hesitations and repetitions. Work on conversational ease.",
        "es": "Intercambio entrecortado con vacilaciones y repeticiones frecuentes. Trabaja la soltura conversacional.",
    }),
    (0, {
        "fr": "Échange très interrompu. Priorité absolue : l'aisance à répondre spontanément.",
        "en": "Very broken exchange. Top priority: fluency in spontaneous responses.",
        "es": "Intercambio muy entrecortado. Prioridad absoluta: la soltura al responder espontáneamente.",
    }),
]


def _score_elaboration(avg_words: float) -> tuple[int, bool]:
    """Return (score 1-5, rambling_flag)."""
    for threshold, score in _ELABORATION_BANDS:
        if avg_words >= threshold:
            rambling = threshold == 80 and avg_words > 140
            return score, rambling
    return 1, False


def _pick_naturalness_verdict(fluency_score: int | None) -> dict[str, str]:
    score = int(fluency_score or 0)
    for threshold, verdict in _NATURALNESS_VERDICTS:
        if score >= threshold:
            return verdict
    return _NATURALNESS_VERDICTS[-1][1]


def _pair_turns_for_answered_check(turns: list) -> list[tuple[str, str, int]]:
    """Walk turns in order, pairing each candidate response with the
    immediately preceding examiner question. Returns
    [(question, response, candidate_turn_number), ...].
    """
    pairs: list[tuple[str, str, int]] = []
    last_examiner: str | None = None
    for t in turns:
        if _speaker(t) == "examiner":
            last_examiner = _text(t)
        elif _speaker(t) == "candidate":
            if last_examiner is None:
                # shouldn't happen — the opener is always the examiner —
                # but stay defensive.
                continue
            pairs.append((last_examiner, _text(t), getattr(t, "turn_number", -1)))
            last_examiner = None
    return pairs


async def _answered_check(pairs: list[tuple[str, str, int]]) -> list[dict]:
    """Ask Claude whether each candidate response answered the examiner's
    question. Falls back to a conservative "answered=True, no-reason"
    list if the API is unavailable or the response is malformed."""
    if not pairs:
        return []

    # Demo/no-key mode: return a heuristic — any response with > 5 words
    # is assumed to have answered. Keeps the feedback card populated
    # without making network calls.
    if not settings.ANTHROPIC_API_KEY:
        return [
            {
                "turn": tn,
                "answered": len((resp or "").split()) > 5,
                "why": "[DEMO] word-count heuristic",
            }
            for _q, resp, tn in pairs
        ]

    system = (
        "You are judging whether a candidate's French oral response answered "
        "the examiner's question. For each pair, return JSON: a list of "
        "{turn:int, answered:bool, why:string (<=10 words, in the UI language)}. "
        "'answered' is true when the response addressed the question's core "
        "ask, even partially. Return ONLY JSON, no preamble."
    )
    payload = {
        "pairs": [
            {"turn": tn, "question": q, "response": resp}
            for q, resp, tn in pairs
        ]
    }
    user_msg = json.dumps(payload, ensure_ascii=False)

    try:
        raw = await _call_claude(system, user_msg)
    except Exception as exc:
        logger.warning("F-048 answered-check failed, conservative fallback: %s", exc)
        return [{"turn": tn, "answered": True, "why": ""} for _q, _r, tn in pairs]

    if isinstance(raw, list):
        return [r for r in raw if isinstance(r, dict)]
    if isinstance(raw, dict):
        # Model sometimes wraps the list in an object.
        for key in ("results", "pairs", "turns"):
            if isinstance(raw.get(key), list):
                return [r for r in raw[key] if isinstance(r, dict)]
    logger.warning("F-048 answered-check returned unexpected shape: %r", str(raw)[:120])
    return [{"turn": tn, "answered": True, "why": ""} for _q, _r, tn in pairs]


def _build_combined_transcript(turns: list) -> str:
    """Concatenate candidate turns into one transcript separated by em-
    dashes on their own line. Light separator so the analyzer can see
    turn boundaries without treating them as sentences."""
    parts = [_text(t).strip() for t in turns if _speaker(t) == "candidate"]
    parts = [p for p in parts if p]
    return "\n—\n".join(parts)


def _build_examiner_context(turns: list) -> str:
    """Build a short summary of the examiner questions so the analyzer
    knows what the candidate was responding to. This is passed via the
    ``topic`` argument of ``analyze_transcript`` — it's the closest slot
    in the existing prompt for "here's the context of what was asked"."""
    lines = [_text(t).strip() for t in turns if _speaker(t) == "examiner"]
    lines = [l for l in lines if l]
    if not lines:
        return "Tâche 1 — Présentation de soi."
    body = " / ".join(lines)
    return f"Tâche 1 — Présentation de soi. Questions de l'examinateur: {body}"


async def analyze_tache_1(
    conversation=None,
    *,
    # Keep the legacy stub kwargs so the dispatcher can still forward
    # blind kwargs during the F-047→F-048 crossover. When
    # ``conversation`` is provided it wins; when it isn't we fall back
    # to ``analyze_transcript`` so the dispatcher smoke tests still pass.
    transcript: str | None = None,
    **kwargs,
) -> dict:
    """Aggregate analysis for a completed Tâche 1 conversation.

    Signature is deliberately tolerant of two call shapes:
      1. ``analyze_tache_1(conversation=conv)`` — the real production
         call from the router on conversation completion.
      2. ``analyze_tache_1(transcript=..., ...)`` — the crossover path
         the F-047 dispatcher used when ``tache_1`` routed a generic
         oral recording. Still delegates to ``analyze_transcript`` so
         nothing breaks if someone calls it the old way.
    """
    if conversation is None:
        # Crossover path — no conversation object, treat as legacy.
        result = await analyze_transcript(
            transcript=transcript or "",
            **kwargs,
        )
        if isinstance(result, dict):
            result["mode"] = "tache_1"
        return result

    turns = _active_turns(conversation)
    combined_transcript = _build_combined_transcript(turns)
    examiner_context = _build_examiner_context(turns)

    # Reuse the existing analyzer with Tâche 1 context. SCORING_PROFILES
    # weighting is applied at persistence time by the router (see
    # _run_analysis_and_persist), so we don't need to touch weights
    # here — analyze_transcript just needs to know what the learner
    # was asked to do.
    forwarded = {
        "topic": examiner_context,
        "target_level": kwargs.get("target_level", "B2"),
        "ui_language": kwargs.get("ui_language", "en"),
        "low_confidence_words": kwargs.get("low_confidence_words", []),
        "exam_profile": kwargs.get("exam_profile", "tcf_canada"),
    }
    result = await analyze_transcript(
        transcript=combined_transcript,
        **forwarded,
    )
    if not isinstance(result, dict):
        result = {"raw": str(result)}
    result["mode"] = "tache_1"

    # ── Tâche 1-specific layer ───────────────────────────────
    candidate_turns = [t for t in turns if _speaker(t) == "candidate"]
    word_counts = [len((_text(t) or "").split()) for t in candidate_turns]
    total_words = sum(word_counts)
    candidate_turn_count = len(candidate_turns)
    avg_words = (total_words / candidate_turn_count) if candidate_turn_count else 0.0
    elaboration_score, rambling = _score_elaboration(avg_words)

    # Naturalness verdict reads the fluency that will be attached to the
    # Recording row by the router. The router passes it in kwargs when
    # available so we don't have to recompute.
    fluency_score = kwargs.get("fluency_score")
    naturalness = _pick_naturalness_verdict(fluency_score)

    pairs = _pair_turns_for_answered_check(turns)
    answered = await _answered_check(pairs)

    result["tache_1"] = {
        "candidate_turn_count": candidate_turn_count,
        "total_candidate_words": total_words,
        "avg_words_per_turn": round(avg_words, 1),
        "elaboration_score": elaboration_score,
        "elaboration_flag_rambling": rambling,
        "naturalness": {
            "verdict_fr": naturalness["fr"],
            "verdict_en": naturalness["en"],
            "verdict_es": naturalness["es"],
        },
        "answered_check": answered,
        "min_candidate_turns": MIN_CANDIDATE_TURNS,
        "max_candidate_turns": MAX_CANDIDATE_TURNS,
        "under_min_turns": candidate_turn_count < MIN_CANDIDATE_TURNS,
    }

    return result
