"""
make enrich — LLM batch enrichment over chunks.

Runs four enrichment passes per chunk:
1. Topic classification (TCF/TEF/DELF taxonomy)
2. Quebec variant detection
3. Register classification
4. Per-CEFR-level example generation

Resumable: tracks completion per (chunk, enrichment_type) in enrichment_log.
Re-running skips already-completed pairs.

This is the longest-running stage. With Ollama on a laptop it can take a week.
With vLLM on a rented GPU it completes overnight.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Iterator, Optional

import click
import requests
from rich.console import Console
from sqlalchemy import text
from tqdm import tqdm

from scripts.common import db_session, get_engine, load_config, setup_logger

console = Console()

ENRICHMENT_TYPES = ("topic", "quebec_variant", "register", "examples")

PROMPT_PATHS = {
    "topic": "prompts/topic_classification.txt",
    "quebec_variant": "prompts/quebec_variant.txt",
    "register": "prompts/register.txt",
    "examples": "prompts/example_generation.txt",
}


class LLMClient:
    """Provider-agnostic LLM client. Currently supports Ollama; vLLM stub."""

    def __init__(self, cfg: dict, log) -> None:
        self.provider = cfg["llm"]["provider"]
        self.model = cfg["llm"]["model"]
        self.endpoint = cfg["llm"]["endpoint"].rstrip("/")
        self.log = log

    def generate(self, prompt: str, timeout: int = 60) -> str:
        if self.provider == "ollama":
            return self._ollama_generate(prompt, timeout)
        elif self.provider == "vllm":
            return self._vllm_generate(prompt, timeout)
        raise ValueError(f"Unknown provider: {self.provider}")

    def _ollama_generate(self, prompt: str, timeout: int) -> str:
        r = requests.post(
            f"{self.endpoint}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.2, "num_predict": 800},
            },
            timeout=timeout,
        )
        r.raise_for_status()
        return r.json()["response"]

    def _vllm_generate(self, prompt: str, timeout: int) -> str:
        # OpenAI-compatible endpoint for vLLM
        r = requests.post(
            f"{self.endpoint}/v1/chat/completions",
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 800,
                "response_format": {"type": "json_object"},
            },
            timeout=timeout,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


def load_prompts() -> dict[str, str]:
    return {k: Path(v).read_text(encoding="utf-8") for k, v in PROMPT_PATHS.items()}


def chunks_needing_enrichment(enrichment_type: str, batch_size: int = 100) -> Iterator[dict]:
    """Yield chunks that haven't been enriched for the given type yet."""
    with get_engine().connect() as conn:
        offset = 0
        while True:
            rows = conn.execute(text("""
                SELECT c.id, c.surface_fr, c.cefr_level,
                       (SELECT example_fr FROM chunk_examples e WHERE e.chunk_id = c.id LIMIT 1) AS example
                FROM chunks c
                WHERE c.language = 'fr'
                AND c.confidence_tier IN ('core', 'extended')
                AND NOT EXISTS (
                    SELECT 1 FROM enrichment_log l
                    WHERE l.chunk_id = c.id
                    AND l.enrichment_type = :etype
                    AND l.status = 'success'
                )
                ORDER BY c.id
                LIMIT :limit OFFSET :offset
            """), {"etype": enrichment_type, "limit": batch_size, "offset": offset}).fetchall()
            if not rows:
                break
            for r in rows:
                yield dict(r._mapping)
            offset += batch_size


def log_enrichment(chunk_id: int, enrichment_type: str, status: str,
                   error_message: Optional[str], model: str) -> None:
    with db_session() as session:
        session.execute(text("""
            INSERT INTO enrichment_log (chunk_id, enrichment_type, status, error_message, model_used)
            VALUES (:chunk_id, :etype, :status, :err, :model)
            ON CONFLICT (chunk_id, enrichment_type) DO UPDATE
            SET status = EXCLUDED.status,
                error_message = EXCLUDED.error_message,
                model_used = EXCLUDED.model_used,
                created_at = NOW()
        """), {
            "chunk_id": chunk_id,
            "etype": enrichment_type,
            "status": status,
            "err": error_message,
            "model": model,
        })


def apply_topic(chunk_id: int, response: dict) -> None:
    topics = response.get("topics", [])
    topic_codes = []
    with db_session() as session:
        for t in topics:
            code = t.get("topic_code")
            exam = t.get("exam")
            conf = t.get("confidence", 0.0)
            if not code or not exam or conf < 0.5:
                continue
            session.execute(text("""
                INSERT INTO chunk_topics (chunk_id, topic_code, exam, confidence, source)
                VALUES (:cid, :code, :exam, :conf, 'llm_enrichment')
                ON CONFLICT (chunk_id, topic_code, exam) DO UPDATE
                SET confidence = EXCLUDED.confidence
            """), {"cid": chunk_id, "code": code, "exam": exam, "conf": conf})
            topic_codes.append(code)

        session.execute(text("""
            UPDATE chunks SET topic_codes = :codes WHERE id = :cid
        """), {"codes": topic_codes, "cid": chunk_id})


def apply_quebec(chunk_id: int, response: dict) -> None:
    is_qc = bool(response.get("is_quebec_specific"))
    variant = response.get("quebec_variant")
    with db_session() as session:
        session.execute(text("""
            UPDATE chunks
            SET is_quebec_specific = :iq,
                quebec_variant = :qv
            WHERE id = :cid
        """), {"iq": is_qc, "qv": variant, "cid": chunk_id})


def apply_register(chunk_id: int, response: dict) -> None:
    reg = response.get("register")
    if not reg:
        return
    with db_session() as session:
        session.execute(text("""
            UPDATE chunks SET register = :reg WHERE id = :cid AND register IS NULL
        """), {"reg": reg, "cid": chunk_id})


def apply_examples(chunk_id: int, response: dict) -> None:
    examples = response.get("examples", [])
    with db_session() as session:
        for ex in examples:
            session.execute(text("""
                INSERT INTO chunk_examples (chunk_id, example_fr, example_en, cefr_level, source_name)
                VALUES (:cid, :fr, :en, :lvl, 'llm_generated')
                ON CONFLICT DO NOTHING
            """), {
                "cid": chunk_id,
                "fr": ex.get("example_fr"),
                "en": ex.get("example_en"),
                "lvl": ex.get("cefr_level"),
            })


APPLIERS = {
    "topic": apply_topic,
    "quebec_variant": apply_quebec,
    "register": apply_register,
    "examples": apply_examples,
}


@click.command()
@click.option("--config", default="config.yml")
@click.option("--types", default=",".join(ENRICHMENT_TYPES),
              help=f"Comma-separated enrichment types ({','.join(ENRICHMENT_TYPES)})")
@click.option("--limit", type=int, default=None, help="Limit total chunks (for testing)")
def main(config: str, types: str, limit: Optional[int]) -> None:
    log = setup_logger("enrich")
    cfg = load_config(config)
    client = LLMClient(cfg, log)
    prompts = load_prompts()

    selected = [t.strip() for t in types.split(",") if t.strip() in ENRICHMENT_TYPES]
    log.info(f"Enrichment types: {selected}")
    log.info(f"Model: {client.model} via {client.provider}")

    for etype in selected:
        prompt_template = prompts[etype]
        applier = APPLIERS[etype]
        log.info(f"\n=== Enrichment: {etype} ===")

        count = 0
        with tqdm(desc=etype, unit="chunks") as bar:
            for chunk in chunks_needing_enrichment(etype):
                if limit is not None and count >= limit:
                    break
                prompt = prompt_template.format(
                    chunk=chunk["surface_fr"],
                    example=chunk.get("example") or "",
                )
                try:
                    raw = client.generate(prompt)
                    parsed = json.loads(raw)
                except json.JSONDecodeError as e:
                    log.error(f"Chunk {chunk['id']} ({chunk['surface_fr']}): JSON parse failed: {e}")
                    log_enrichment(chunk["id"], etype, "failure", f"json_decode: {e}", client.model)
                    bar.update(1)
                    count += 1
                    continue
                except requests.RequestException as e:
                    log.error(f"Chunk {chunk['id']}: LLM request failed: {e}")
                    log_enrichment(chunk["id"], etype, "failure", f"llm_request: {e}", client.model)
                    bar.update(1)
                    count += 1
                    time.sleep(2)  # back off on transient errors
                    continue

                try:
                    applier(chunk["id"], parsed)
                    log_enrichment(chunk["id"], etype, "success", None, client.model)
                except Exception as e:
                    log.error(f"Chunk {chunk['id']}: apply failed: {e}")
                    log_enrichment(chunk["id"], etype, "failure", f"apply: {e}", client.model)

                bar.update(1)
                count += 1

        log.info(f"{etype}: {count} chunks processed")

    # Mark chunks fully enriched
    with get_engine().begin() as conn:
        conn.execute(text("""
            UPDATE chunks
            SET enrichment_completed_at = NOW()
            WHERE language = 'fr'
            AND (
                SELECT COUNT(DISTINCT enrichment_type) FROM enrichment_log
                WHERE chunk_id = chunks.id AND status = 'success'
            ) >= 4
        """))

    log.info("Enrichment complete.")


if __name__ == "__main__":
    main()
