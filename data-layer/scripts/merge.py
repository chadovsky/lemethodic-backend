"""
make merge — run cross-source merge SQL and report results.

Recomputes confidence_tier based on the number of contributing sources
per chunk. Idempotent.
"""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table
from sqlalchemy import text

from scripts.common import apply_sql, get_engine, setup_logger

console = Console()


@click.command()
@click.option("--config", default="config.yml")
def main(config: str) -> None:
    log = setup_logger("merge")
    log.info("Running sql/002_merge.sql")
    apply_sql("sql/002_merge.sql")

    console.rule("[bold]Merge results")
    with get_engine().connect() as conn:
        rows = conn.execute(text("""
            SELECT
                confidence_tier,
                COUNT(*) AS chunk_count,
                COUNT(*) FILTER (WHERE cefr_level IS NOT NULL) AS with_cefr,
                COUNT(*) FILTER (WHERE chunk_type IS NOT NULL) AS with_type,
                COUNT(*) FILTER (WHERE surface_en IS NOT NULL) AS with_translation,
                COUNT(*) FILTER (WHERE is_quebec_specific) AS quebec_variants
            FROM chunks
            GROUP BY confidence_tier
            ORDER BY confidence_tier
        """)).fetchall()

    table = Table(show_header=True, header_style="bold")
    table.add_column("tier")
    table.add_column("chunks", justify="right")
    table.add_column("with CEFR", justify="right")
    table.add_column("with type", justify="right")
    table.add_column("with EN", justify="right")
    table.add_column("Quebec", justify="right")

    for r in rows:
        table.add_row(
            r.confidence_tier or "?",
            f"{r.chunk_count:,}",
            f"{r.with_cefr:,}",
            f"{r.with_type:,}",
            f"{r.with_translation:,}",
            f"{r.quebec_variants:,}",
        )

    console.print(table)
    log.info("Merge complete.")


if __name__ == "__main__":
    main()
