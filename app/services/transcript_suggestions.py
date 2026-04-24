"""F-002: Contextual best-guess corrections for low-confidence STT words.

Called once per recording when low_conf_ratio <= 0.30. Asks Claude Haiku
(cheap, fast) to propose replacements for each flagged word given the
surrounding French transcript + the topic context.

Returns {word_index: suggested_replacement_text}. Gracefully degrades to
{} on any failure — frontend still shows AssemblyAI's guess + custom input
and the correction UI remains usable.
"""
from __future__ import annotations

import json
import logging
from typing import Iterable

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Haiku 4.5 per F-002 decision 2: cheaper + faster for per-word contextual
# guessing. Sonnet stays the primary feedback model.
_MODEL = "claude-haiku-4-5-20251001"


async def suggest_corrections(
    transcript: str,
    words: list[dict],
    low_conf_indices: Iterable[int],
    topic: str = "",
) -> dict[int, str]:
    low_conf_indices = list(low_conf_indices)
    if not low_conf_indices:
        return {}
    if not settings.ANTHROPIC_API_KEY:
        logger.info("[F-002] ANTHROPIC_API_KEY missing, skipping Claude suggestions")
        return {}

    flagged_block = "\n".join(
        f'  index {i}: "{words[i]["text"]}" (STT confidence={words[i].get("confidence", 0):.2f})'
        for i in low_conf_indices
        if 0 <= i < len(words)
    )

    system = (
        "Tu es un correcteur de transcription automatique de français parlé. "
        "Pour chaque mot à faible confiance, propose le mot le plus probable que "
        "l'étudiant a réellement dit, en tenant compte du sujet, du contexte "
        "francophone, et des composés courants (télétravail, covoiturage, etc.).\n\n"
        "Règles :\n"
        "- Propose UN seul mot ou expression courte par index.\n"
        "- Si la transcription semble déjà correcte, renvoie le mot original.\n"
        "- Privilégie le français naturel. Évite les calques anglais.\n"
        "- N'invente pas : si le contexte ne permet pas de trancher, reprends l'original.\n\n"
        "Réponds UNIQUEMENT en JSON valide, sans markdown :\n"
        '{"suggestions":[{"index":<int>,"guess":"<mot>"}]}'
    )

    user_msg = (
        f"Sujet : {topic or '(non spécifié)'}\n\n"
        f"Transcription complète :\n\"\"\"\n{transcript}\n\"\"\"\n\n"
        f"Mots à faible confiance :\n{flagged_block}"
    )

    try:
        async with httpx.AsyncClient(timeout=45) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": _MODEL,
                    "max_tokens": 1024,
                    "system": system,
                    "messages": [{"role": "user", "content": user_msg}],
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.warning(f"[F-002] Haiku suggestion call failed: {e}")
        return {}

    raw = data.get("content", [{}])[0].get("text", "")
    try:
        parsed = json.loads(
            raw.strip()
            .removeprefix("```json").removeprefix("```")
            .removesuffix("```").strip()
        )
    except json.JSONDecodeError:
        logger.warning(f"[F-002] Haiku returned non-JSON; dropping suggestions")
        return {}

    out: dict[int, str] = {}
    for entry in parsed.get("suggestions", []) or []:
        if not isinstance(entry, dict):
            continue
        idx = entry.get("index")
        guess = entry.get("guess")
        if isinstance(idx, int) and isinstance(guess, str) and guess.strip():
            out[idx] = guess.strip()
    return out
