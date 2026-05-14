"""
make decide — interactive prompts for the five [DECIDE-*] forks from the backlog.

Persists answers to config.yml under `decisions:`. Re-running shows current
values and lets you change them.
"""

from __future__ import annotations

from datetime import datetime

import click
from rich.console import Console
from rich.prompt import Prompt

from scripts.common import load_config, save_config

console = Console()


DECISIONS = [
    {
        "key": "postgres_host",
        "marker": "[DECIDE-F1A]",
        "question": "Postgres hosting",
        "choices": ["local", "supabase", "neon"],
        "default": "local",
        "help": (
            "local: your current Postgres instance (if pgvector is available)\n"
            "supabase: managed Postgres with pgvector built-in (free tier)\n"
            "neon: serverless Postgres with pgvector built-in (free tier)"
        ),
    },
    {
        "key": "llm_compute",
        "marker": "[DECIDE-F6A]",
        "question": "LLM enrichment compute",
        "choices": ["cpu_overnight", "gpu_one_day"],
        "default": "cpu_overnight",
        "help": (
            "cpu_overnight: your laptop running Ollama for ~1 week ($0)\n"
            "gpu_one_day: one-day RunPod RTX 4090 rental (~$15, 5-10× faster)"
        ),
    },
    {
        "key": "llm_model",
        "marker": "[DECIDE-F6B]",
        "question": "LLM model for enrichment",
        "choices": ["qwen2.5:7b-instruct", "mistral-small:24b-instruct"],
        "default": "qwen2.5:7b-instruct",
        "help": (
            "qwen2.5:7b-instruct: Apache 2.0, 7B params, decent French (start here)\n"
            "mistral-small:24b-instruct: Apache 2.0, 24B params, better French (slower)"
        ),
    },
    {
        "key": "triangulation_strictness",
        "marker": "[DECIDE-F5A]",
        "question": "Triangulation strictness for core library",
        "choices": ["loose", "strict"],
        "default": "strict",
        "help": (
            "loose: a chunk needs ≥1 source to be in core library (more chunks, more variance)\n"
            "strict: a chunk needs ≥2 sources to be in core library (fewer chunks, higher quality)"
        ),
    },
    {
        "key": "phase_2b_start",
        "marker": "[DECIDE-XA]",
        "question": "When to start Phase 2-B (surface wiring)",
        "choices": ["after_f5", "after_f9"],
        "default": "after_f9",
        "help": (
            "after_f5: start wiring surfaces once basic data is in (enrichment still running)\n"
            "after_f9: wait for foundation to fully validate before wiring surfaces (safer)"
        ),
    },
]


@click.command()
@click.option("--config", default="config.yml", help="Path to config.yml")
def main(config: str) -> None:
    cfg = load_config(config)
    decisions = cfg.get("decisions", {})

    console.rule("[bold]Decision prompts")
    console.print(
        "These choices are persisted to config.yml. Press Enter to accept "
        "the default (shown in brackets), or type a different option.\n"
    )

    for d in DECISIONS:
        current = decisions.get(d["key"], d["default"])
        console.rule(d["marker"])
        console.print(f"[bold]{d['question']}[/bold]")
        console.print(d["help"])
        console.print(f"  Current: [cyan]{current}[/cyan]")

        choice = Prompt.ask(
            f"Choose",
            choices=d["choices"],
            default=current,
            show_choices=True,
        )
        decisions[d["key"]] = choice

    decisions["last_updated"] = datetime.utcnow().isoformat() + "Z"
    cfg["decisions"] = decisions

    # If llm_model was changed, also update llm.model
    cfg["llm"]["model"] = decisions["llm_model"]

    save_config(cfg, config)
    console.rule("[green]Decisions saved")
    console.print(f"Written to [bold]{config}[/bold].")


if __name__ == "__main__":
    main()
