"""F-052 — pre-synthesize the Tâche 1 opening prompts so the very first
candidate doesn't wait a second or two for the mic-warm greeting.

Safe to re-run: ``tts.synthesize`` short-circuits on cache hits.

Usage from project root:
    python -m scripts.prewarm_tts
"""
from __future__ import annotations

import asyncio
import sys

from app.config import settings
from app.services.personas.tache_1_examiner import OPENING_PROMPTS, FALLBACK_CLOSE
from app.services.tts import prewarm


async def _main() -> int:
    if not settings.OPENAI_API_KEY:
        print("OPENAI_API_KEY not set — nothing to synthesize. Skipping.")
        return 0

    phrases = list(OPENING_PROMPTS) + [FALLBACK_CLOSE]
    results = await prewarm(phrases, voice=settings.TTS_VOICE_TACHE_1)
    for phrase, url in results.items():
        status = "OK" if url else "FAILED"
        print(f"  [{status}] {phrase}")
    ok = sum(1 for u in results.values() if u)
    print(f"Prewarm complete: {ok}/{len(results)} phrases cached.")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
