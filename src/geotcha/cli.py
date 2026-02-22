"""CLI interface for GEOtcha."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

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


def version_callback(value: bool) -> None:
    if value:
        console.print(f"GEOtcha v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option("--version", "-v", callback=version_callback, is_eager=True),
    ] = None,
) -> None:
    """GEOtcha: Extract and harmonize RNA-seq metadata from NCBI GEO."""


@app.command()
def search(
    query: Annotated[str, typer.Argument(help="Disease/condition keyword to search")],
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Output directory"),
    ] = None,
    api_key: Annotated[
        Optional[str],
        typer.Option("--api-key", help="NCBI API key"),
    ] = None,
    email: Annotated[
        Optional[str],
        typer.Option("--email", help="Email for NCBI Entrez"),
    ] = None,
) -> None:
    """Search GEO for RNA-seq datasets matching a disease keyword."""
    from geotcha.config import Settings
    from geotcha.exceptions import GEOtchaError
    from geotcha.search.entrez import search_geo
    from geotcha.search.query_builder import build_query
    from geotcha.search.filters import filter_results

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
        Optional[Path],
        typer.Option("--output", "-o", help="Output directory"),
    ] = None,
    harmonize: Annotated[
        bool,
        typer.Option("--harmonize", help="Apply harmonization rules"),
    ] = False,
    api_key: Annotated[
        Optional[str],
        typer.Option("--api-key", help="NCBI API key"),
    ] = None,
) -> None:
    """Extract metadata from specific GSE IDs."""
    from geotcha.config import Settings
    from geotcha.exceptions import GEOtchaError
    from geotcha.pipeline import run_extract

    try:
        settings = Settings.load(ncbi_api_key=api_key, output_dir=output)
        run_extract(gse_ids, settings, harmonize=harmonize, console=console)
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
        Optional[int],
        typer.Option("--subset", "-s", help="Process a subset first for validation"),
    ] = None,
    output: Annotated[
        Optional[Path],
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
        Optional[str],
        typer.Option("--llm-provider", help="LLM provider: openai, anthropic, ollama"),
    ] = None,
    api_key: Annotated[
        Optional[str],
        typer.Option("--api-key", help="NCBI API key"),
    ] = None,
    email: Annotated[
        Optional[str],
        typer.Option("--email", help="Email for NCBI Entrez"),
    ] = None,
) -> None:
    """Run the full pipeline: search, filter, extract, and export."""
    from geotcha.config import Settings
    from geotcha.exceptions import GEOtchaError
    from geotcha.pipeline import run_pipeline

    try:
        settings = Settings.load(
            ncbi_api_key=api_key,
            ncbi_email=email,
            output_dir=output,
            llm_provider=llm_provider,
        )
        run_pipeline(
            query=query,
            settings=settings,
            subset_size=subset,
            harmonize=harmonize,
            use_llm=llm,
            console=console,
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


@config_app.command("set")
def config_set(
    key: Annotated[str, typer.Argument(help="Configuration key")],
    value: Annotated[str, typer.Argument(help="Configuration value")],
) -> None:
    """Set a configuration value."""
    from geotcha.config import save_config, get_config_path

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
