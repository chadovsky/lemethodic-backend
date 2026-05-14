"""
make review-queue — generate a stratified validation spreadsheet.

Samples N chunks (default 500) across confidence tiers, CEFR levels, and
sources. Writes to processed/validation_sample.xlsx for human spot-checking.

You score each row by adding a column 'score' (0-3) and 'notes'. After
manual review, run `validate-import` to load failures back to enrichment_log
for re-processing.
"""

from __future__ import annotations

import click
import pandas as pd
from rich.console import Console
from sqlalchemy import text

from scripts.common import get_engine, load_config, setup_logger

console = Console()


@click.command()
@click.option("--config", default="config.yml")
def main(config: str) -> None:
    log = setup_logger("review_queue")
    cfg = load_config(config)
    sample_size = cfg["validation"]["sample_size"]
    output_path = cfg["validation"]["output_path"]

    log.info(f"Generating validation sample of {sample_size} chunks")

    # Stratified random sample: roughly equal across CEFR levels in core library.
    with get_engine().connect() as conn:
        df = pd.read_sql(text("""
            WITH stratified AS (
                SELECT
                    c.id,
                    c.surface_fr,
                    c.surface_en,
                    c.lemma_fr,
                    c.chunk_type,
                    c.cefr_level,
                    c.register,
                    c.is_quebec_specific,
                    c.quebec_variant,
                    c.topic_codes,
                    c.confidence_tier,
                    (SELECT array_agg(source_name) FROM chunk_sources WHERE chunk_id = c.id) AS sources,
                    (SELECT example_fr FROM chunk_examples e WHERE e.chunk_id = c.id LIMIT 1) AS example_fr,
                    (SELECT example_en FROM chunk_examples e WHERE e.chunk_id = c.id LIMIT 1) AS example_en,
                    ROW_NUMBER() OVER (PARTITION BY c.cefr_level ORDER BY random()) AS rn
                FROM chunks c
                WHERE c.confidence_tier IN ('core', 'extended')
                AND c.language = 'fr'
            )
            SELECT * FROM stratified
            WHERE rn <= :per_level
            ORDER BY cefr_level NULLS LAST, surface_fr
        """), conn, params={"per_level": max(1, sample_size // 6)})

    log.info(f"Selected {len(df)} chunks for review")

    # Add empty columns for human review
    df["accuracy_score"] = ""  # 0=wrong, 1=partial, 2=acceptable, 3=correct
    df["notes"] = ""

    df.to_excel(output_path, index=False, sheet_name="validation")
    log.info(f"Wrote {output_path}")
    console.print(f"\n[bold]Next steps[/bold]:")
    console.print(f"  1. Open {output_path} in Excel/Numbers/LibreOffice")
    console.print(f"  2. For each row, fill 'accuracy_score' (0-3) and any 'notes'")
    console.print(f"  3. Save the file")
    console.print(f"  4. Run: python scripts/review_queue.py --import {output_path}")


if __name__ == "__main__":
    main()
