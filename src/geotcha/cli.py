"""CLI interface for GEOtcha."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from geotcha import __version__

app = typer.Typer(
    name="geotcha",
    help="Extract and harmonize RNA-seq metadata from NCBI GEO.",
    no_args_is_help=True,
)
console = Console()

config_app = typer.Typer(help="Manage GEOtcha configuration.")
app.add_typer(config_app, name="config")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        })


def _configure_json_logging() -> None:
    """Replace the root logger's handlers with a structured JSON handler."""
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(_JsonFormatter())
    logging.root.setLevel(logging.INFO)
    logging.root.handlers = [handler]


def version_callback(value: bool) -> None:
    if value:
        console.print(f"GEOtcha v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option("--version", "-v", callback=version_callback, is_eager=True),
    ] = None,
) -> None:
    """GEOtcha: Extract and harmonize RNA-seq metadata from NCBI GEO."""


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command()
def search(
    query: Annotated[str, typer.Argument(help="Disease/condition keyword to search")],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output directory"),
    ] = None,
    api_key: Annotated[
        str | None,
        typer.Option("--api-key", help="NCBI API key"),
    ] = None,
    email: Annotated[
        str | None,
        typer.Option("--email", help="Email for NCBI Entrez"),
    ] = None,
) -> None:
    """Search GEO for RNA-seq datasets matching a disease keyword."""
    from geotcha.config import Settings
    from geotcha.exceptions import GEOtchaError
    from geotcha.search.entrez import search_geo
    from geotcha.search.filters import filter_results
    from geotcha.search.query_builder import build_query

    try:
        settings = Settings.load(
            ncbi_api_key=api_key,
            ncbi_email=email,
            output_dir=output,
        )

        with console.status("[bold green]Building search query..."):
            expanded_query = build_query(query)
        console.print(f"[bold]Search query:[/bold] {expanded_query}")

        with console.status("[bold green]Searching GEO..."):
            raw_results = search_geo(expanded_query, settings)
        console.print(f"[bold]Raw results:[/bold] {len(raw_results)} datasets found")

        with console.status("[bold green]Filtering for human RNA-seq..."):
            filtered = filter_results(raw_results, settings, query=query)
        console.print(
            f"[bold]Filtered results:[/bold] {len(filtered)} human RNA-seq datasets"
        )

        for gse_id in filtered:
            console.print(f"  {gse_id}")
    except GEOtchaError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def extract(
    gse_ids: Annotated[
        list[str],
        typer.Argument(help="GSE IDs to extract metadata from"),
    ],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output directory"),
    ] = None,
    harmonize: Annotated[
        bool,
        typer.Option("--harmonize", help="Apply harmonization rules"),
    ] = False,
    api_key: Annotated[
        str | None,
        typer.Option("--api-key", help="NCBI API key"),
    ] = None,
    include_scrna: Annotated[
        bool,
        typer.Option("--include-scrna", help="Include single-cell RNA-seq datasets"),
    ] = False,
    fmt: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: csv, tsv, or parquet"),
    ] = "csv",
    log_json: Annotated[
        bool,
        typer.Option("--log-json", help="Emit structured JSON logs to stderr"),
    ] = False,
    ml_mode: Annotated[
        str,
        typer.Option("--ml-mode", help="ML harmonization: off, hybrid, or full"),
    ] = "off",
    ml_device: Annotated[
        str,
        typer.Option("--ml-device", help="Device for ML inference: auto, cpu, cuda, or mps"),
    ] = "auto",
    ml_batch_size: Annotated[
        int,
        typer.Option("--ml-batch-size", help="Batch size for ML inference"),
    ] = 32,
    ml_threshold: Annotated[
        float,
        typer.Option("--ml-threshold", help="Min ML confidence to accept prediction"),
    ] = 0.65,
) -> None:
    """Extract metadata from specific GSE IDs."""
    from geotcha.config import Settings
    from geotcha.exceptions import GEOtchaError
    from geotcha.pipeline import run_extract

    if fmt not in ("csv", "tsv", "parquet"):
        console.print(f"[red]Error: --format must be one of: csv, tsv, parquet (got '{fmt}')[/red]")
        raise typer.Exit(1)

    if ml_mode not in ("off", "hybrid", "full"):
        console.print(f"[red]Invalid --ml-mode: {ml_mode}. Must be off, hybrid, or full.[/red]")
        raise typer.Exit(1)

    try:
        settings = Settings.load(
            ncbi_api_key=api_key, output_dir=output,
            include_scrna=include_scrna or None,
            log_json=log_json or None,
            ml_mode=ml_mode if ml_mode != "off" else None,
            ml_device=ml_device if ml_device != "auto" else None,
            ml_batch_size=ml_batch_size if ml_batch_size != 32 else None,
            ml_threshold=ml_threshold if ml_threshold != 0.65 else None,
        )
        if settings.log_json or log_json:
            _configure_json_logging()
        run_extract(gse_ids, settings, harmonize=harmonize, console=console, fmt=fmt)
    except GEOtchaError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def run(
    query: Annotated[str, typer.Argument(help="Disease/condition keyword to search")],
    subset: Annotated[
        int | None,
        typer.Option("--subset", "-s", help="Process a subset first for validation"),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output directory"),
    ] = None,
    harmonize: Annotated[
        bool,
        typer.Option("--harmonize", help="Apply harmonization rules"),
    ] = False,
    llm: Annotated[
        bool,
        typer.Option("--llm", help="Use LLM for harmonization"),
    ] = False,
    llm_provider: Annotated[
        str | None,
        typer.Option("--llm-provider", help="LLM provider: openai, anthropic, ollama"),
    ] = None,
    api_key: Annotated[
        str | None,
        typer.Option("--api-key", help="NCBI API key"),
    ] = None,
    email: Annotated[
        str | None,
        typer.Option("--email", help="Email for NCBI Entrez"),
    ] = None,
    include_scrna: Annotated[
        bool,
        typer.Option("--include-scrna", help="Include single-cell RNA-seq datasets"),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Auto-confirm all prompts (non-interactive)"),
    ] = False,
    non_interactive: Annotated[
        bool,
        typer.Option("--non-interactive", help="Disable all interactive prompts, use defaults"),
    ] = False,
    max_workers: Annotated[
        int | None,
        typer.Option("--max-workers", help="Max parallel workers for extraction (default 4)"),
    ] = None,
    cache_ttl_days: Annotated[
        int | None,
        typer.Option("--cache-ttl-days", help="Entrez cache TTL in days (default 7)"),
    ] = None,
    fmt: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: csv, tsv, or parquet"),
    ] = "csv",
    log_json: Annotated[
        bool,
        typer.Option("--log-json", help="Emit structured JSON logs to stderr"),
    ] = False,
    ml_mode: Annotated[
        str,
        typer.Option("--ml-mode", help="ML harmonization: off, hybrid, or full"),
    ] = "off",
    ml_device: Annotated[
        str,
        typer.Option("--ml-device", help="Device for ML inference: auto, cpu, cuda, or mps"),
    ] = "auto",
    ml_batch_size: Annotated[
        int,
        typer.Option("--ml-batch-size", help="Batch size for ML inference"),
    ] = 32,
    ml_threshold: Annotated[
        float,
        typer.Option("--ml-threshold", help="Min ML confidence to accept prediction"),
    ] = 0.65,
) -> None:
    """Run the full pipeline: search, filter, extract, and export."""
    from geotcha.config import Settings
    from geotcha.exceptions import GEOtchaError
    from geotcha.pipeline import run_pipeline

    if fmt not in ("csv", "tsv", "parquet"):
        console.print(f"[red]Error: --format must be one of: csv, tsv, parquet (got '{fmt}')[/red]")
        raise typer.Exit(1)

    if ml_mode not in ("off", "hybrid", "full"):
        console.print(f"[red]Invalid --ml-mode: {ml_mode}. Must be off, hybrid, or full.[/red]")
        raise typer.Exit(1)

    try:
        settings = Settings.load(
            ncbi_api_key=api_key,
            ncbi_email=email,
            output_dir=output,
            llm_provider=llm_provider,
            include_scrna=include_scrna or None,
            yes=yes or None,
            non_interactive=non_interactive or None,
            max_workers=max_workers,
            cache_ttl_days=cache_ttl_days,
            log_json=log_json or None,
            ml_mode=ml_mode if ml_mode != "off" else None,
            ml_device=ml_device if ml_device != "auto" else None,
            ml_batch_size=ml_batch_size if ml_batch_size != 32 else None,
            ml_threshold=ml_threshold if ml_threshold != 0.65 else None,
        )
        if settings.log_json or log_json:
            _configure_json_logging()
        run_pipeline(
            query=query,
            settings=settings,
            subset_size=subset,
            harmonize=harmonize,
            use_llm=llm,
            console=console,
            fmt=fmt,
        )
    except GEOtchaError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def resume(
    run_id: Annotated[str, typer.Argument(help="Run ID to resume")],
) -> None:
    """Resume an interrupted pipeline run."""
    from geotcha.config import Settings
    from geotcha.exceptions import GEOtchaError
    from geotcha.pipeline import resume_run

    try:
        settings = Settings.load()
        resume_run(run_id, settings, console=console)
    except GEOtchaError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def report(
    run_id: Annotated[str, typer.Argument(help="Run ID to report on")],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Directory to write report.json"),
    ] = None,
) -> None:
    """Print a markdown summary of a completed run."""
    from geotcha.config import Settings

    settings = Settings.load()
    manifest_path = settings.get_data_dir() / run_id / "manifest.json"

    if not manifest_path.exists():
        console.print(f"[red]Run not found: {run_id}[/red]")
        console.print(
            f"[dim]Expected manifest at: {manifest_path}[/dim]"
        )
        raise typer.Exit(1)

    manifest = json.loads(manifest_path.read_text())

    failed_ids = manifest.get("failed_ids", [])
    stage_timings = manifest.get("stage_timings", {})

    console.print(f"\n## Run: {run_id}")
    console.print(f"Query:     {manifest.get('query', '')}")
    console.print(f"Started:   {manifest.get('started_at', '')}")
    console.print(f"Completed: {manifest.get('completed_at', 'incomplete')}")
    console.print(
        f"IDs found / filtered / processed: "
        f"{manifest.get('total_ids', 0)} / "
        f"{manifest.get('filtered_ids', 0)} / "
        f"{manifest.get('processed_ids', 0)}"
    )
    console.print(
        f"Failed: {len(failed_ids)} — {', '.join(failed_ids) if failed_ids else 'none'}"
    )
    if stage_timings:
        timing_str = ", ".join(f"{k}: {v}s" for k, v in stage_timings.items())
        console.print(f"Stage timings: {timing_str}")

    report_data = {
        "run_id": run_id,
        "query": manifest.get("query", ""),
        "started_at": manifest.get("started_at", ""),
        "completed_at": manifest.get("completed_at"),
        "total_ids": manifest.get("total_ids", 0),
        "filtered_ids": manifest.get("filtered_ids", 0),
        "processed_ids": manifest.get("processed_ids", 0),
        "failed_ids": failed_ids,
        "stage_timings": stage_timings,
        "output_paths": manifest.get("output_paths", {}),
    }

    report_dir = output or manifest_path.parent
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "report.json"
    report_path.write_text(json.dumps(report_data, indent=2))
    console.print(f"\n[green]Report written: {report_path}[/green]")


# ---------------------------------------------------------------------------
# Config subcommands
# ---------------------------------------------------------------------------


@config_app.command("set")
def config_set(
    key: Annotated[str, typer.Argument(help="Configuration key")],
    value: Annotated[str, typer.Argument(help="Configuration value")],
) -> None:
    """Set a configuration value."""
    from geotcha.config import get_config_path, save_config

    save_config(key, value)
    console.print(f"[green]Set {key} in {get_config_path()}[/green]")


@config_app.command("show")
def config_show() -> None:
    """Show current configuration."""
    from geotcha.config import Settings, get_config_path

    settings = Settings.load()
    console.print(f"[bold]Config file:[/bold] {get_config_path()}")
    console.print()
    for field_name, field_info in settings.model_fields.items():
        value = getattr(settings, field_name)
        if "api_key" in field_name and value:
            value = value[:4] + "..." + value[-4:]
        desc = field_info.description or ""
        console.print(f"  [bold]{field_name}[/bold] = {value}  [dim]# {desc}[/dim]")


@config_app.command("validate")
def config_validate() -> None:
    """Validate current configuration."""
    from pydantic import ValidationError

    from geotcha.config import Settings

    try:
        settings = Settings.load()
    except ValidationError as exc:
        console.print("[red]Error: Configuration is invalid.[/red]")
        for err in exc.errors():
            field = ".".join(str(loc) for loc in err["loc"])
            console.print(f"  [red]{field}: {err['msg']}[/red]")
        raise typer.Exit(1)
    warnings = []
    has_error = False

    # Show settings with masked keys
    console.print("[bold]Current settings:[/bold]")
    console.print()
    for field_name, field_info in settings.model_fields.items():
        value = getattr(settings, field_name)
        if "api_key" in field_name and isinstance(value, str) and value:
            display_value = "****"
        else:
            display_value = str(value)
        desc = field_info.description or ""
        console.print(f"  [bold]{field_name}[/bold] = {display_value}  [dim]# {desc}[/dim]")
    console.print()

    # ML validation
    if settings.ml_mode not in ("off", "hybrid", "full"):
        warnings.append(
            f"ml_mode={settings.ml_mode!r} is invalid. Must be off, hybrid, or full."
        )

    if settings.ml_threshold < 0 or settings.ml_threshold > 1:
        warnings.append(
            f"ml_threshold={settings.ml_threshold} is out of range [0, 1]."
        )

    if settings.ml_review_threshold < 0 or settings.ml_review_threshold > 1:
        warnings.append(
            f"ml_review_threshold={settings.ml_review_threshold} is out of range [0, 1]."
        )

    if settings.ml_device not in ("auto", "cpu", "cuda", "mps"):
        warnings.append(
            f"ml_device={settings.ml_device!r} is invalid. Must be auto, cpu, cuda, or mps."
        )

    # NCBI warnings
    if settings.ncbi_email is None:
        warnings.append(
            "ncbi_email is not set. NCBI requires an email for API usage."
        )

    if settings.ncbi_api_key is None:
        warnings.append(
            "ncbi_api_key is not set. Without an API key rate limit is 3 req/s."
        )

    # Output format validation
    if settings.output_format not in ("csv", "tsv", "parquet"):
        console.print(
            f"[red]Error: output_format '{settings.output_format}' is invalid. "
            "Must be one of: csv, tsv, parquet.[/red]"
        )
        has_error = True

    if warnings:
        for w in warnings:
            console.print(f"[yellow]Warning: {w}[/yellow]")

    if has_error:
        raise typer.Exit(1)
    else:
        console.print("[green]Configuration looks valid.[/green]")
