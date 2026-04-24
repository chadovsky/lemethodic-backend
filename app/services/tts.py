"""F-052 — Text-to-speech abstraction for the AI examiner voice.

Currently wraps OpenAI TTS-1-HD. Designed so a future ticket can swap
to ElevenLabs by adding an alternate implementation behind the same
interface (see ``TTS_PROVIDER`` in config).

Caching: per (text, voice, model) — SHA-256 → ``{TTS_CACHE_DIR}/{hash}.mp3``.
Identical phrases (e.g. the Tâche 1 opening prompts) are synthesized
once and then served from disk. Cost-logging is a plain JSONL file at
``TTS_COST_LOG`` for Chadi to eyeball after the sprint.

Failure modes:
- missing API key → returns None (caller shows text-only with a
  "voix indisponible" indicator).
- 401/429/5xx → one retry with 1s backoff, then returns None.
- offline / network error → same retry path, then None.

Security: cache keys are non-guessable SHA-256 digests but files under
``/tts_audio/<key>.mp3`` are publicly served. Callers must only
synthesize AI-generated examiner text or pre-authored prompts — never
user input.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# OpenAI TTS-1-HD pricing (USD) as of 2026-04. 1K input characters ≈
# $0.030. Chadi can override by setting the env var, but the default
# tracks the public price list.
_DEFAULT_MODEL = "tts-1-hd"
_OPENAI_ENDPOINT = "https://api.openai.com/v1/audio/speech"
_COST_PER_1K_CHARS_USD = float(os.getenv("TTS_COST_PER_1K_CHARS", "0.030"))
_RESPONSE_FORMAT = "mp3"  # default for OpenAI TTS; smallest / most portable

_URL_PREFIX = "/tts_audio"  # matches the static mount in main.py


def _cache_dir() -> Path:
    """Resolve + ensure the cache directory. Lazy so tests can override
    ``settings.TTS_CACHE_DIR`` between calls."""
    d = Path(settings.TTS_CACHE_DIR)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cost_log_path() -> Path:
    p = Path(settings.TTS_COST_LOG)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _cache_key(text: str, voice: str, model: str) -> str:
    return hashlib.sha256(f"{text}|{voice}|{model}".encode("utf-8")).hexdigest()


def _cached_path(cache_key: str) -> Path:
    return _cache_dir() / f"{cache_key}.{_RESPONSE_FORMAT}"


def _public_url(cache_key: str) -> str:
    return f"{_URL_PREFIX}/{cache_key}.{_RESPONSE_FORMAT}"


def _log_cost(event: str, text_len: int, voice: str, model: str, cached: bool) -> None:
    """Append-only JSONL. Cheap enough to run on every call; Chadi can
    `sort | uniq -c` the daily totals when he checks unit economics."""
    entry = {
        "ts": time.time(),
        "event": event,
        "text_len": text_len,
        "voice": voice,
        "model": model,
        "cached": cached,
        "estimated_usd": 0.0 if cached else round(text_len * _COST_PER_1K_CHARS_USD / 1000.0, 6),
    }
    try:
        with _cost_log_path().open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as exc:
        # Don't fail a request just because we couldn't log.
        logger.warning("F-052 cost log write failed: %s", exc)


async def _call_openai(text: str, voice: str, model: str) -> bytes | None:
    """Single HTTP call to OpenAI TTS. Returns audio bytes or None on
    failure. Pure — caller handles retries / backoff."""
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                _OPENAI_ENDPOINT,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "voice": voice,
                    "input": text,
                    "response_format": _RESPONSE_FORMAT,
                },
            )
    except Exception as exc:
        logger.warning("F-052 OpenAI TTS network error: %s", exc)
        return None

    if resp.status_code != 200:
        logger.warning(
            "F-052 OpenAI TTS non-200: status=%s body=%s",
            resp.status_code,
            (resp.text or "")[:200],
        )
        return None
    return resp.content


async def synthesize(
    text: str,
    voice: str = "nova",
    model: str = _DEFAULT_MODEL,
) -> Optional[str]:
    """Synthesize French text to speech.

    Returns a publicly-servable URL like ``/tts_audio/<sha256>.mp3`` on
    success, or ``None`` if TTS is unavailable. Never raises — callers
    must tolerate a ``None`` return by falling back to text-only.

    Cache: SHA-256(text|voice|model). Hits are free and instant.

    Retry policy: one retry with a 1 s backoff on network / 5xx / 429.
    Two calls total, then give up.
    """
    text = (text or "").strip()
    if not text:
        return None
    if settings.TTS_PROVIDER not in ("openai",):
        logger.warning("F-052 unknown TTS_PROVIDER=%s, falling back to None", settings.TTS_PROVIDER)
        return None

    key = _cache_key(text, voice, model)
    cached = _cached_path(key)
    if cached.exists() and cached.stat().st_size > 0:
        _log_cost("cache_hit", len(text), voice, model, cached=True)
        return _public_url(key)

    if not settings.OPENAI_API_KEY:
        # Still log — the miss is useful to see how often we'd have
        # paid for TTS if the key were set.
        _log_cost("no_key", len(text), voice, model, cached=False)
        return None

    audio_bytes: bytes | None = None
    for attempt in (1, 2):
        audio_bytes = await _call_openai(text, voice, model)
        if audio_bytes:
            break
        if attempt == 1:
            await asyncio.sleep(1.0)

    if not audio_bytes:
        _log_cost("failed", len(text), voice, model, cached=False)
        return None

    # Write to a temp sibling file then atomically rename. Prevents a
    # half-written mp3 from being served on a crash between HTTP
    # completion and disk flush.
    tmp = cached.with_suffix(cached.suffix + ".tmp")
    try:
        tmp.write_bytes(audio_bytes)
        os.replace(tmp, cached)
    except OSError as exc:
        logger.warning("F-052 cache write failed (%s); returning None", exc)
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass
        return None

    _log_cost("synthesized", len(text), voice, model, cached=False)
    return _public_url(key)


async def prewarm(phrases: list[str], voice: str, model: str = _DEFAULT_MODEL) -> dict:
    """Pre-synthesize a set of phrases so the first real user doesn't
    wait. Returns ``{phrase: url_or_None}`` for each input. Safe to
    call at app startup; existing cache entries short-circuit the API."""
    results: dict[str, Optional[str]] = {}
    for phrase in phrases:
        results[phrase] = await synthesize(phrase, voice=voice, model=model)
    return results


def is_available() -> bool:
    """Cheap UI-layer check — True when we'd attempt a TTS call.
    Doesn't verify the key actually works."""
    return (
        settings.TTS_PROVIDER == "openai"
        and bool(settings.OPENAI_API_KEY)
    )
