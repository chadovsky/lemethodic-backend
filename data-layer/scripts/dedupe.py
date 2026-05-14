"""
make dedupe — near-duplicate collapsing beyond what normalize_surface catches.

Targets:
- "s'en aller" vs "s en aller" (apostrophe variant)
- "ne pas comprendre" vs "ne pas... comprendre" (artifact whitespace)
- Variants with and without diacritics
- Identical surface, different case across sources

normalize_surface already handles most of these at insert time. This script
runs a second pass for any duplicates that slipped through, especially across
sources that landed at different times.
"""

from __future__ import annotations

import click
from rich.console import Console
from sqlalchemy import text

from scripts.common import get_engine, setup_logger

console = Console()


@click.command()
@click.option("--config", default="config.yml")
@click.option("--dry-run", is_flag=True, help="Report but don't modify")
def main(config: str, dry_run: bool) -> None:
    log = setup_logger("dedupe")
    log.info(f"Running dedupe (dry_run={dry_run})")

    # Find chunks with identical normalized_surface (shouldn't exist if upsert
    # worked correctly, but defensive check).
    with get_engine().connect() as conn:
        duplicates = conn.execute(text("""
            SELECT normalized_surface, COUNT(*) AS n
            FROM chunks
            GROUP BY normalized_surface
            HAVING COUNT(*) > 1
        """)).fetchall()

    if duplicates:
        log.warning(f"Found {len(duplicates)} normalized_surface duplicates")
        if not dry_run:
            with get_engine().begin() as conn:
                # Keep oldest, merge others into it
                conn.execute(text("""
                    WITH dups AS (
                        SELECT normalized_surface, MIN(id) AS keep_id,
                               array_agg(id) AS all_ids
                        FROM chunks
                        GROUP BY normalized_surface
                        HAVING COUNT(*) > 1
                    )
                    UPDATE chunk_sources cs
                    SET chunk_id = d.keep_id
                    FROM dups d
                    WHERE cs.chunk_id = ANY(d.all_ids)
                      AND cs.chunk_id != d.keep_id
                """))
                conn.execute(text("""
                    WITH dups AS (
                        SELECT normalized_surface, MIN(id) AS keep_id,
                               array_agg(id) AS all_ids
                        FROM chunks
                        GROUP BY normalized_surface
                        HAVING COUNT(*) > 1
                    )
                    UPDATE chunk_examples ce
                    SET chunk_id = d.keep_id
                    FROM dups d
                    WHERE ce.chunk_id = ANY(d.all_ids)
                      AND ce.chunk_id != d.keep_id
                """))
                conn.execute(text("""
                    DELETE FROM chunks
                    WHERE id IN (
                        SELECT id FROM chunks c
                        WHERE EXISTS (
                            SELECT 1 FROM chunks c2
                            WHERE c2.normalized_surface = c.normalized_surface
                              AND c2.id < c.id
                        )
                    )
                """))
            log.info("Duplicates merged.")
    else:
        log.info("No normalized_surface duplicates found.")

    # TODO: Additional dedupe passes — apostrophe variants, accent variants —
    # can be added here. Initial pass focuses on the literal dupes.

    log.info("Dedupe complete.")


if __name__ == "__main__":
    main()
