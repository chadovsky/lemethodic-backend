"""
make setup — environment validation and model preparation.

Run once after install. Confirms:
- Postgres connection works
- pgvector extension available
- spaCy French model installed
- Embeddings model downloads correctly
- Ollama running (if configured)
- Output directories exist
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from sqlalchemy import text

console = Console()


def check_db() -> bool:
    try:
        from scripts.common import get_engine
        with get_engine().connect() as conn:
            ver = conn.execute(text("SELECT version()")).scalar()
            console.print(f"  Postgres: [green]✓[/green] {ver.split(',')[0]}")
            return True
    except Exception as e:
        console.print(f"  Postgres: [red]✗[/red] {e}")
        return False


def check_pgvector() -> bool:
    try:
        from scripts.common import get_engine
        with get_engine().connect() as conn:
            r = conn.execute(text(
                "SELECT 1 FROM pg_available_extensions WHERE name = 'vector'"
            )).scalar()
            if r:
                console.print(f"  pgvector: [green]✓[/green] available")
                return True
            else:
                console.print(f"  pgvector: [red]✗[/red] not installed on this Postgres instance")
                return False
    except Exception as e:
        console.print(f"  pgvector: [red]✗[/red] {e}")
        return False


def check_spacy() -> bool:
    try:
        import spacy
        try:
            spacy.load("fr_core_news_lg")
            console.print(f"  spaCy fr_core_news_lg: [green]✓[/green]")
            return True
        except OSError:
            console.print(
                f"  spaCy fr_core_news_lg: [yellow]missing[/yellow] — "
                f"run: python -m spacy download fr_core_news_lg"
            )
            return False
    except ImportError:
        console.print(f"  spaCy: [red]✗[/red] not installed")
        return False


def check_embeddings_model() -> bool:
    try:
        from scripts.common import load_config
        from sentence_transformers import SentenceTransformer
        cfg = load_config()
        model_name = cfg["embeddings"]["model"]
        console.print(f"  Loading embeddings model {model_name} (first run downloads weights)...")
        m = SentenceTransformer(model_name)
        v = m.encode("test", show_progress_bar=False)
        console.print(f"  Embeddings model: [green]✓[/green] dim={len(v)}")
        return True
    except Exception as e:
        console.print(f"  Embeddings model: [red]✗[/red] {e}")
        return False


def check_llm() -> bool:
    try:
        from scripts.common import load_config
        cfg = load_config()
        provider = cfg["llm"]["provider"]
        model = cfg["llm"]["model"]
        if provider == "ollama":
            import requests
            endpoint = cfg["llm"]["endpoint"].rstrip("/")
            r = requests.get(f"{endpoint}/api/tags", timeout=5)
            r.raise_for_status()
            models = [m["name"] for m in r.json().get("models", [])]
            if any(m.startswith(model.split(":")[0]) for m in models):
                console.print(f"  Ollama: [green]✓[/green] {model} loaded")
                return True
            else:
                console.print(
                    f"  Ollama: [yellow]running but {model} not pulled[/yellow] — "
                    f"run: ollama pull {model}"
                )
                return False
        elif provider == "vllm":
            console.print(f"  vLLM: [yellow]not auto-checked, ensure your server is reachable[/yellow]")
            return True
        else:
            console.print(f"  LLM: [red]✗[/red] unknown provider '{provider}'")
            return False
    except Exception as e:
        console.print(f"  LLM: [red]✗[/red] {e}")
        return False


def check_dirs() -> bool:
    try:
        from scripts.common import ensure_dirs, load_config
        ensure_dirs()
        cfg = load_config()
        for key in ("raw_dir", "processed_dir", "logs_dir"):
            console.print(f"  {key}: [green]✓[/green] {cfg['data'][key]}")
        return True
    except Exception as e:
        console.print(f"  Directories: [red]✗[/red] {e}")
        return False


@click.command()
@click.option("--config", default="config.yml", help="Path to config.yml")
def main(config: str) -> None:
    console.rule("[bold]Le Méthodic data-layer setup")
    if not Path(config).exists():
        console.print(f"[red]Missing {config}.[/red] Copy config.example.yml -> config.yml and edit.")
        sys.exit(1)

    console.print("\n[bold]Database[/bold]")
    db_ok = check_db()
    if db_ok:
        check_pgvector()

    console.print("\n[bold]Python environment[/bold]")
    check_spacy()

    console.print("\n[bold]Models[/bold]")
    check_embeddings_model()
    check_llm()

    console.print("\n[bold]Directories[/bold]")
    check_dirs()

    console.rule("[bold]Setup complete")
    console.print("If anything above is red or yellow, resolve before running `make schema`.")


if __name__ == "__main__":
    main()
