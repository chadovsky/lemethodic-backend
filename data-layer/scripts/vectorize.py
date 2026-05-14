"""
make vectorize — embeddings + audio + CDN upload.

Three sub-stages:
1. Compute embeddings for every chunk via sentence-transformers, write to pgvector.
2. Generate audio for every chunk and example via Piper TTS, save locally.
3. Upload audio to CDN (R2 or S3), write back audio_url.

Resumable: skips chunks/examples that already have embeddings/audio.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from sqlalchemy import text
from tqdm import tqdm

from scripts.common import get_engine, load_config, setup_logger

console = Console()


# ----------------------- Embeddings -----------------------

def run_embeddings(cfg: dict, log) -> None:
    from sentence_transformers import SentenceTransformer

    model_name = cfg["embeddings"]["model"]
    log.info(f"Loading embeddings model: {model_name}")
    model = SentenceTransformer(model_name)

    with get_engine().connect() as conn:
        rows = conn.execute(text("""
            SELECT c.id, c.surface_fr,
                   (SELECT example_fr FROM chunk_examples e WHERE e.chunk_id = c.id LIMIT 1) AS example
            FROM chunks c
            WHERE c.embedding IS NULL
            AND c.language = 'fr'
            ORDER BY c.id
        """)).fetchall()
    log.info(f"{len(rows)} chunks need embeddings")

    BATCH = 64
    with get_engine().begin() as conn:
        for i in tqdm(range(0, len(rows), BATCH), desc="Embedding"):
            batch = rows[i:i+BATCH]
            texts_to_embed = [
                f"{r.surface_fr}: {r.example}" if r.example else r.surface_fr
                for r in batch
            ]
            vectors = model.encode(texts_to_embed, show_progress_bar=False)
            for r, vec in zip(batch, vectors):
                conn.execute(text("UPDATE chunks SET embedding = :v WHERE id = :id"),
                             {"v": vec.tolist(), "id": r.id})


# ----------------------- Audio generation -----------------------

def piper_synthesize(text_to_speak: str, voice: str, output_path: Path) -> None:
    """Invoke Piper CLI. Assumes piper is on PATH."""
    proc = subprocess.run(
        ["piper", "--model", voice, "--output_file", str(output_path)],
        input=text_to_speak.encode("utf-8"),
        capture_output=True,
        timeout=30,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Piper failed: {proc.stderr.decode('utf-8', errors='ignore')}")


def audio_filename(text_content: str) -> str:
    """Content-addressed filename for caching."""
    h = hashlib.sha1(text_content.encode("utf-8")).hexdigest()[:16]
    return f"{h}.wav"


def run_audio(cfg: dict, log) -> None:
    output_dir = Path(cfg["tts"]["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    voice_fr = cfg["tts"]["voice_fr"]
    voice_qc = cfg["tts"]["voice_fr_quebec"]

    # Chunks without audio
    with get_engine().connect() as conn:
        chunks = conn.execute(text("""
            SELECT id, surface_fr, is_quebec_specific, quebec_variant
            FROM chunks
            WHERE audio_url IS NULL
            AND language = 'fr'
            AND confidence_tier IN ('core', 'extended')
        """)).fetchall()
    log.info(f"{len(chunks)} chunks need audio")

    for chunk in tqdm(chunks, desc="Audio (chunks)"):
        text_to_speak = chunk.quebec_variant or chunk.surface_fr
        voice = voice_qc if chunk.is_quebec_specific else voice_fr
        fname = audio_filename(f"{voice}|{text_to_speak}")
        out_path = output_dir / fname
        try:
            if not out_path.exists():
                piper_synthesize(text_to_speak, voice, out_path)
            with get_engine().begin() as conn:
                # Local path for now; CDN upload step rewrites if configured
                conn.execute(text("UPDATE chunks SET audio_url = :u WHERE id = :id"),
                             {"u": str(out_path), "id": chunk.id})
        except Exception as e:
            log.error(f"Chunk {chunk.id} ({text_to_speak}): {e}")

    # Examples without audio
    with get_engine().connect() as conn:
        examples = conn.execute(text("""
            SELECT id, example_fr FROM chunk_examples
            WHERE audio_url IS NULL
        """)).fetchall()
    log.info(f"{len(examples)} examples need audio")

    for ex in tqdm(examples, desc="Audio (examples)"):
        fname = audio_filename(f"{voice_fr}|{ex.example_fr}")
        out_path = output_dir / fname
        try:
            if not out_path.exists():
                piper_synthesize(ex.example_fr, voice_fr, out_path)
            with get_engine().begin() as conn:
                conn.execute(text("UPDATE chunk_examples SET audio_url = :u WHERE id = :id"),
                             {"u": str(out_path), "id": ex.id})
        except Exception as e:
            log.error(f"Example {ex.id}: {e}")


# ----------------------- CDN upload -----------------------

def run_cdn_upload(cfg: dict, log) -> None:
    provider = cfg["cdn"]["provider"]
    if provider == "none":
        log.info("CDN provider = none, skipping upload. Audio URLs remain local paths.")
        return

    try:
        import boto3
    except ImportError:
        raise RuntimeError("boto3 not installed.")

    s3 = boto3.client(
        "s3",
        endpoint_url=cfg["cdn"].get("endpoint_url") or None,
        aws_access_key_id=cfg["cdn"]["access_key_id"],
        aws_secret_access_key=cfg["cdn"]["secret_access_key"],
    )
    bucket = cfg["cdn"]["bucket"]
    public_base = cfg["cdn"]["public_url_base"].rstrip("/")

    # Find audio paths that are still local
    audio_dir = Path(cfg["tts"]["output_dir"]).resolve()
    log.info(f"Scanning {audio_dir} for files to upload")

    with get_engine().connect() as conn:
        local_chunks = conn.execute(text("""
            SELECT id, audio_url FROM chunks
            WHERE audio_url IS NOT NULL
            AND audio_url NOT LIKE 'http%'
        """)).fetchall()
        local_examples = conn.execute(text("""
            SELECT id, audio_url FROM chunk_examples
            WHERE audio_url IS NOT NULL
            AND audio_url NOT LIKE 'http%'
        """)).fetchall()

    def upload_and_update(table: str, rows) -> None:
        for r in tqdm(rows, desc=f"Upload {table}"):
            local = Path(r.audio_url)
            if not local.exists():
                continue
            key = f"audio/{local.name}"
            try:
                s3.upload_file(str(local), bucket, key,
                               ExtraArgs={"ContentType": "audio/wav", "ACL": "public-read"})
                public_url = f"{public_base}/{key}"
                with get_engine().begin() as conn:
                    conn.execute(text(f"UPDATE {table} SET audio_url = :u WHERE id = :id"),
                                 {"u": public_url, "id": r.id})
            except Exception as e:
                log.error(f"{table} {r.id}: upload failed: {e}")

    upload_and_update("chunks", local_chunks)
    upload_and_update("chunk_examples", local_examples)


# ----------------------- Entry point -----------------------

@click.command()
@click.option("--config", default="config.yml")
@click.option("--skip-embeddings", is_flag=True)
@click.option("--skip-audio", is_flag=True)
@click.option("--skip-cdn", is_flag=True)
def main(config: str, skip_embeddings: bool, skip_audio: bool, skip_cdn: bool) -> None:
    log = setup_logger("vectorize")
    cfg = load_config(config)

    if not skip_embeddings:
        log.info("=== Embeddings ===")
        run_embeddings(cfg, log)

    if not skip_audio:
        log.info("=== Audio generation ===")
        run_audio(cfg, log)

    if not skip_cdn:
        log.info("=== CDN upload ===")
        run_cdn_upload(cfg, log)

    log.info("Vectorize complete.")


if __name__ == "__main__":
    main()
