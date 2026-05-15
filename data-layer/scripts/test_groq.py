"""
Smoke test for the Groq LLM provider wired into LLMClient.

Single shot: sends a fixed translation prompt to Groq via the existing
LLMClient and prints the raw response. NOT part of `make enrich` — run
this manually to verify GROQ_API_KEY + endpoint config before kicking
off the real enrichment pipeline.

Usage:
    cd data-layer
    python -m scripts.test_groq
"""

from __future__ import annotations

import logging
import sys

from scripts.common import load_config
from scripts.enrich import LLMClient

PROMPT = (
    "Translate 'bonjour' to English. "
    "Respond with a JSON object of the form {\"translation\": \"...\"}."
)


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    log = logging.getLogger("test_groq")

    cfg = load_config("config.yml")
    provider = cfg["llm"]["provider"]
    if provider != "groq":
        log.error(f"config.yml llm.provider is '{provider}', expected 'groq'.")
        return 2

    log.info(f"Provider: {provider}  model: {cfg['llm']['model']}")
    log.info(f"Endpoint: {cfg['llm']['endpoint']}")

    client = LLMClient(cfg, log)
    try:
        response = client.generate(PROMPT, timeout=30)
    except Exception as e:
        log.error(f"Groq call failed: {e}")
        return 1

    print("\n--- Groq response ---")
    print(response)
    print("--- end ---\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
