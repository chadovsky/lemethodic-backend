"""
make license-audit — per-source license report.

Outputs:
1. A text report listing every source, license, attribution requirement.
2. Suggested attribution copy ready for inclusion in the product's About page.
3. A flag for any source whose commercial use status is unverified.

Run before launching the product publicly. Read the report. Sign off.
"""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from sqlalchemy import text

from scripts.common import LICENSE_REGISTRY, get_engine, setup_logger

console = Console()


@click.command()
@click.option("--config", default="config.yml")
@click.option("--output", default="processed/LICENSE_AUDIT.md")
def main(config: str, output: str) -> None:
    log = setup_logger("license_audit")

    # Find which sources actually contributed to chunks in our DB
    with get_engine().connect() as conn:
        contributing = {row.source_name: row.contributed_count for row in conn.execute(text("""
            SELECT source_name, COUNT(DISTINCT chunk_id) AS contributed_count
            FROM chunk_sources
            GROUP BY source_name
        """))}

    lines: list[str] = []
    lines.append("# Le Méthodic — data source license audit")
    lines.append("")
    lines.append(f"Generated: {__import__('datetime').datetime.utcnow().isoformat()}Z")
    lines.append("")

    # Quick visual table
    table = Table(show_header=True, header_style="bold")
    table.add_column("Source")
    table.add_column("License")
    table.add_column("Chunks", justify="right")
    table.add_column("Commercial use")
    table.add_column("Status")

    unverified = []
    for source, info in LICENSE_REGISTRY.items():
        n = contributing.get(source, 0)
        ok = info.get("commercial_use", "").lower().startswith("yes")
        status = "OK" if ok else "VERIFY"
        if not ok and n > 0:
            unverified.append(source)
        table.add_row(source, info.get("license", "?"), f"{n:,}", info.get("commercial_use", "?"), status)

    console.print(table)

    # Markdown report
    lines.append("## Sources contributing to the data layer")
    lines.append("")
    lines.append("| Source | License | Chunks | Commercial use |")
    lines.append("|---|---|---:|---|")
    for source, info in LICENSE_REGISTRY.items():
        n = contributing.get(source, 0)
        lines.append(f"| {source} | {info.get('license', '?')} | {n:,} | {info.get('commercial_use', '?')} |")

    lines.append("")
    lines.append("## Attribution copy for product About page")
    lines.append("")
    lines.append("> Le Méthodic uses open language data. We thank the following projects:")
    lines.append(">")
    for source, info in LICENSE_REGISTRY.items():
        n = contributing.get(source, 0)
        if n == 0:
            continue
        lines.append(f"> - **{source}** ([{info.get('url', '')}]({info.get('url', '')})): {info.get('attribution', '')} Licensed under {info.get('license', '?')}.")

    if unverified:
        lines.append("")
        lines.append("## ⚠️ Verification required")
        lines.append("")
        lines.append("The following sources have commercial use marked as conditional or unverified. Verify each before public launch:")
        lines.append("")
        for s in unverified:
            lines.append(f"- **{s}**: {LICENSE_REGISTRY[s].get('commercial_use', '')}")
            lines.append(f"  - License: {LICENSE_REGISTRY[s].get('license', '?')}")
            lines.append(f"  - URL: {LICENSE_REGISTRY[s].get('url', '')}")

    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text("\n".join(lines), encoding="utf-8")
    log.info(f"License audit written to {output}")

    if unverified:
        console.print(f"\n[bold yellow]⚠️ {len(unverified)} source(s) require verification before launch:[/bold yellow]")
        for s in unverified:
            console.print(f"  - {s}")


if __name__ == "__main__":
    main()
