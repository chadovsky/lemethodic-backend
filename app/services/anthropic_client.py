"""F-311 Phase A — centralized Anthropic API client.

One place for:
  - HTTP call to /v1/messages
  - Cache_control wrapping on the system prompt
  - Structured token-usage + cache-hit logging
  - JSON-content extraction (with code-fence tolerance)

Both `analysis._call_claude` and `writing_analysis._call_claude` refactor
to wrap this. Inline httpx call sites (tache_1, tache_2,
argument_assistant, transcript_suggestions) also route through here.

Cache_control pattern (per Anthropic prompt-caching docs):
  - Default `cache_system=True` AND `settings.ENABLE_PROMPT_CACHE=True`:
    system prompt becomes a single-block content array with
    `cache_control: {"type": "ephemeral"}`. First call within the 5-min
    window: cache write (1.25x base cost). Subsequent calls within
    window: cache hit (0.1x base cost).
  - Pre-conditions for caching to actually engage: system prompt must
    be >= 1024 tokens for Sonnet, >= 4096 for Haiku. Below threshold,
    Anthropic ignores the cache_control marker silently.
  - `cache_system=False`: pass system as plain string (no caching).

Caller patterns:
  result = await call_anthropic(
      system=SYSTEM_PROMPT,
      messages=[{"role": "user", "content": user_msg}],
      model=pick_model("diagnostic"),
      max_tokens=settings.MAX_TOKENS_DIAGNOSTIC,
  )
  # Returns dict (parsed JSON) or str (raw text on JSON parse failure).

  content, usage = await call_anthropic(..., return_meta=True)
  # usage = {input_tokens, output_tokens, cache_creation_input_tokens,
  #          cache_read_input_tokens}

Failure modes:
  - HTTPStatusError → raises (caller's responsibility — same as before).
  - Empty/missing API key → 401-equivalent raises from Anthropic.
  - JSON parse fail on content → returns the raw text (legacy behavior
    preserved; demo-fallback paths in analysis.py + writing_analysis.py
    handle this).
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Union

import httpx

from app.config import settings


logger = logging.getLogger(__name__)


ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"

# Anthropic prompt-caching needs a beta header on most plans during
# rollout. The header is harmless on plans where caching is GA.
_ANTHROPIC_BETA_PROMPT_CACHE = "prompt-caching-2024-07-31"


async def call_anthropic(
    *,
    system: Union[str, list[dict]],
    messages: list[dict],
    model: str,
    max_tokens: int,
    cache_system: bool = True,
    temperature: float | None = None,
    timeout: float = 120.0,
    return_meta: bool = False,
) -> Union[dict, str, tuple]:
    """Call Anthropic /v1/messages and return parsed content.

    Args:
        system: System prompt. If a plain string AND cache_system=True
            AND settings.ENABLE_PROMPT_CACHE=True, wrapped as a
            cache_control content array. If a pre-built list of content
            blocks, passed through as-is (advanced callers controlling
            their own caching markers).
        messages: Anthropic message array. At least one user message.
        model: Anthropic model ID. Get from ai_router.pick_model(task).
        max_tokens: Output cap. Diagnostic = 1600 (per F-311 Q1 override);
            examiner = 256; etc.
        cache_system: Wrap system prompt with cache_control. Default True.
        temperature: Sampling temperature. Default None = Anthropic default (1.0).
        timeout: httpx timeout in seconds.
        return_meta: If True, return (content, usage_dict). Else return
            content only.

    Returns:
        dict | str | tuple — see return_meta.
    """
    # Build the system field
    if isinstance(system, str):
        if cache_system and settings.ENABLE_PROMPT_CACHE:
            system_field: Union[str, list] = [
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ]
        else:
            system_field = system
    else:
        system_field = system  # pre-built list; caller knows what they're doing

    headers = {
        "x-api-key": settings.ANTHROPIC_API_KEY,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
    }
    if cache_system and settings.ENABLE_PROMPT_CACHE:
        headers["anthropic-beta"] = _ANTHROPIC_BETA_PROMPT_CACHE

    payload: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system_field,
        "messages": messages,
    }
    if temperature is not None:
        payload["temperature"] = temperature

    t_start = time.time()
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(ANTHROPIC_MESSAGES_URL, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
    elapsed = time.time() - t_start

    usage = data.get("usage", {}) or {}
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    cache_creation = usage.get("cache_creation_input_tokens", 0)
    cache_read = usage.get("cache_read_input_tokens", 0)

    logger.info(
        "F-311 anthropic call model=%s in=%d out=%d cache_write=%d cache_hit=%d "
        "elapsed_s=%.2f",
        model, input_tokens, output_tokens, cache_creation, cache_read, elapsed,
    )

    raw = data["content"][0]["text"]
    parsed = _try_parse_json(raw)

    if return_meta:
        return parsed, {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_creation_input_tokens": cache_creation,
            "cache_read_input_tokens": cache_read,
            "model": model,
            "elapsed_s": elapsed,
        }
    return parsed


def _try_parse_json(raw: str) -> Union[dict, str]:
    """Try to parse Claude content as JSON, tolerating markdown fences."""
    try:
        return json.loads(
            raw.strip()
            .removeprefix("```json").removeprefix("```")
            .removesuffix("```").strip()
        )
    except json.JSONDecodeError:
        return raw
