"""Pipeline orchestrator with user checkpoints and state tracking."""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

from geotcha import __version__
from geotcha.config import Settings
from geotcha.export.writers import (
    gse_to_row,
    read_gse_summary,
    write_all,
    write_gse_summary_rows,
    write_gsm_file,
)
from geotcha.extract.gse_parser import parse_gse
from geotcha.models import GSERecord
from geotcha.search.entrez import search_geo
from geotcha.search.filters import filter_results
from geotcha.search.query_builder import build_query

logger = logging.getLogger(__name__)


def _build_settings_snapshot(settings: Settings) -> dict:
    """Build a settings snapshot with API keys masked."""
    snapshot: dict = {}
    for field_name in settings.model_fields:
        value = getattr(settings, field_name)
        if "api_key" in field_name and isinstance(value, str) and value:
            value = value[:4] + "****" if len(value) > 4 else "****"
        elif isinstance(value, Path):
            value = str(value)
        snapshot[field_name] = value
    return snapshot


def _save_state(run_id: str, state: dict, settings: Settings) -> Path:
    """Save pipeline state (atomic write via tmp + os.replace)."""
    state_dir = settings.get_data_dir() / run_id
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / "state.json"
    tmp_file = state_dir / "state.json.tmp"
    tmp_file.write_text(json.dumps(state, indent=2, default=str))
    os.replace(tmp_file, state_file)
    return state_file


def _save_manifest(run_id: str, manifest: dict, settings: Settings) -> Path:
    """Save run manifest (atomic write via tmp + os.replace)."""
    state_dir = settings.get_data_dir() / run_id
    state_dir.mkdir(parents=True, exist_ok=True)
    manifest_file = state_dir / "manifest.json"
    tmp_file = state_dir / "manifest.json.tmp"
    tmp_file.write_text(json.dumps(manifest, indent=2, default=str))
    os.replace(tmp_file, manifest_file)
    return manifest_file


def _load_state(run_id: str, settings: Settings) -> dict | None:
    """Load pipeline state."""
    state_file = settings.get_data_dir() / run_id / "state.json"
    if state_file.exists():
        return json.loads(state_file.read_text())
    return None


def _extract_batch(
    gse_ids: list[str],
    settings: Settings,
    console: Console,
    harmonize: bool = False,
    use_llm: bool = False,
    include_scrna: bool = False,
) -> tuple[list[GSERecord], list[tuple[str, str]]]:
    """Extract metadata for a batch of GSE IDs with progress tracking.

    Returns:
        Tuple of (records, failed) where failed is a list of (gse_id, error_message).
    """
    records: list[GSERecord] = []
    failed: list[tuple[str, str]] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Extracting metadata...", total=len(gse_ids))

        for gse_id in gse_ids:
            try:
                progress.update(task, description=f"Processing {gse_id}...")
                record = parse_gse(gse_id, settings, include_scrna=include_scrna)

                if harmonize:
                    record = _harmonize_record(record, use_llm, settings)

                records.append(record)
            except Exception as e:
                logger.error(f"Failed to process {gse_id}: {e}")
                failed.append((gse_id, str(e)))
            finally:
                progress.advance(task)

    if failed:
        console.print(f"\n[yellow]Warning: {len(failed)} datasets failed:[/yellow]")
        for gse_id, error in failed:
            console.print(f"  [dim]{gse_id}: {error}[/dim]")

    return records, failed


def _harmonize_record(
    record: GSERecord,
    use_llm: bool = False,
    settings: Settings | None = None,
) -> GSERecord:
    """Apply harmonization to a GSERecord and its samples."""
    from geotcha.harmonize.rules import harmonize_gse, harmonize_gsm

    record = harmonize_gse(record)
    record.samples = [harmonize_gsm(s) for s in record.samples]

    if use_llm:
        try:
            from geotcha.harmonize.llm import llm_harmonize_record

            provider = (settings.llm_provider or "openai") if settings else "openai"
            api_key = settings.llm_api_key if settings else None
            model = settings.llm_model if settings else None
            record = llm_harmonize_record(record, provider=provider, api_key=api_key, model=model)
        except ImportError:
            logger.warning("LLM dependencies not installed. Skipping LLM harmonization.")
        except Exception as e:
            logger.warning(f"LLM harmonization failed: {e}")

    return record


def run_pipeline(
    query: str,
    settings: Settings,
    subset_size: int | None = None,
    harmonize: bool = False,
    use_llm: bool = False,
    console: Console | None = None,
) -> None:
    """Run the full pipeline: search → filter → extract → export."""
    if console is None:
        console = Console()

    run_id = str(uuid.uuid4())[:8]
    output_dir = settings.output_dir
    started_at = datetime.now(timezone.utc).isoformat()
    all_failed: list[tuple[str, str]] = []
    non_interactive = settings.non_interactive or settings.yes

    manifest: dict = {
        "run_id": run_id,
        "query": query,
        "started_at": started_at,
        "completed_at": None,
        "pipeline_version": __version__,
        "total_ids": 0,
        "filtered_ids": 0,
        "processed_ids": 0,
        "failed_ids": [],
        "output_paths": {},
        "settings_snapshot": _build_settings_snapshot(settings),
    }

    # Step 1: Search
    with console.status("[bold green]Building search query..."):
        expanded_query = build_query(query)
    console.print(f"[bold]Search query:[/bold] {expanded_query[:120]}...")

    with console.status("[bold green]Searching GEO..."):
        raw_ids = search_geo(expanded_query, settings)
    manifest["total_ids"] = len(raw_ids)
    console.print(f"[bold]Raw results:[/bold] {len(raw_ids)} datasets found")

    if not raw_ids:
        console.print("[yellow]No datasets found. Try a different search term.[/yellow]")
        return

    # Step 2: Filter (organism + type + relevance)
    with console.status("[bold green]Filtering for human RNA-seq..."):
        filtered_ids = filter_results(raw_ids, settings, query=query)
    manifest["filtered_ids"] = len(filtered_ids)

    console.print(
        f"Found [bold]{len(raw_ids)}[/bold] datasets. "
        "After filtering (Homo sapiens + RNA-seq + relevance): "
        f"[bold]{len(filtered_ids)}[/bold] datasets."
    )

    if not filtered_ids:
        console.print("[yellow]No human RNA-seq datasets found after filtering.[/yellow]")
        return

    # Step 2b: Optional LLM relevance filtering
    if use_llm and filtered_ids:
        try:
            from geotcha.harmonize.llm import llm_check_relevance
            from geotcha.search.entrez import get_gse_summaries

            console.print("[bold]Running LLM relevance check...[/bold]")
            with console.status("[bold green]Classifying dataset relevance with LLM..."):
                gse_summaries = get_gse_summaries(filtered_ids, settings)
                datasets_for_llm = [
                    {
                        "gse_id": gse_id,
                        "title": gse_summaries.get(gse_id, {}).get("title", ""),
                        "summary": gse_summaries.get(gse_id, {}).get("summary", ""),
                    }
                    for gse_id in filtered_ids
                ]
                provider = settings.llm_provider or "openai"
                relevant_ids = llm_check_relevance(
                    datasets_for_llm,
                    query,
                    provider=provider,
                    api_key=settings.llm_api_key,
                    model=settings.llm_model,
                )

            pre_llm_count = len(filtered_ids)
            filtered_ids = [gid for gid in filtered_ids if gid in relevant_ids]
            manifest["filtered_ids"] = len(filtered_ids)
            console.print(
                f"LLM relevance filter: [bold]{pre_llm_count}[/bold] → "
                f"[bold]{len(filtered_ids)}[/bold] datasets"
            )

            if not filtered_ids:
                console.print("[yellow]No datasets passed LLM relevance check.[/yellow]")
                return
        except ImportError:
            logger.warning("LLM dependencies not installed. Skipping LLM relevance filtering.")
        except Exception as e:
            logger.warning(
                f"LLM relevance filtering failed: {e}. Continuing with rule-based results.",
            )

    # Save initial state + manifest
    state = {
        "run_id": run_id,
        "query": query,
        "all_gse_ids": filtered_ids,
        "processed_gse_ids": [],
        "harmonize": harmonize,
        "use_llm": use_llm,
        "status": "filtered",
    }
    _save_state(run_id, state, settings)
    _save_manifest(run_id, manifest, settings)

    # Step 3: User Checkpoint #1 — Subset selection
    if not non_interactive:
        if subset_size is None:
            run_subset = typer.confirm("Run on a subset first?", default=True)
            if run_subset:
                subset_size = int(
                    typer.prompt("Subset size", default=str(settings.default_subset_size))
                )

    if subset_size and subset_size < len(filtered_ids):
        subset_ids = filtered_ids[:subset_size]
        remaining_ids = filtered_ids[subset_size:]

        console.print(f"\nProcessing {len(subset_ids)}/{len(filtered_ids)} datasets...")

        records, failed = _extract_batch(
            subset_ids, settings, console, harmonize, use_llm,
            include_scrna=settings.include_scrna,
        )
        all_failed.extend(failed)

        paths = write_all(records, output_dir, settings.output_format, harmonize)
        console.print(
            f"\n[green]Results: {paths.get('gse_summary', '')} "
            f"({len(records)} rows), {output_dir / 'gsm'} "
            f"({sum(1 for k in paths if k != 'gse_summary')} files)[/green]"
        )

        state["processed_gse_ids"] = subset_ids
        state["status"] = "subset_complete"
        manifest["processed_ids"] = len(records)
        manifest["failed_ids"] = [gid for gid, _ in all_failed]
        manifest["output_paths"] = {k: str(v) for k, v in paths.items()}
        _save_state(run_id, state, settings)
        _save_manifest(run_id, manifest, settings)

        # Step 4: User Checkpoint #2 — Approve full run
        if remaining_ids:
            if non_interactive:
                proceed = True
            else:
                proceed = typer.confirm(
                    f"\nProceed with remaining {len(remaining_ids)} datasets?",
                    default=True,
                )
            if not proceed:
                console.print(
                    f"[dim]Run ID: {run_id} — resume later with: geotcha resume {run_id}[/dim]"
                )
                return

            console.print(f"\nProcessing remaining {len(remaining_ids)} datasets...")
            more_records, more_failed = _extract_batch(
                remaining_ids, settings, console, harmonize, use_llm,
                include_scrna=settings.include_scrna,
            )
            all_failed.extend(more_failed)
            records.extend(more_records)

            paths = write_all(records, output_dir, settings.output_format, harmonize)
            state["processed_gse_ids"] = filtered_ids
            state["status"] = "complete"
            manifest["processed_ids"] = len(records)
            manifest["failed_ids"] = [gid for gid, _ in all_failed]
            manifest["completed_at"] = datetime.now(timezone.utc).isoformat()
            manifest["output_paths"] = {k: str(v) for k, v in paths.items()}
            _save_state(run_id, state, settings)
            _save_manifest(run_id, manifest, settings)
    else:
        # No subset — process all
        console.print(f"\nProcessing {len(filtered_ids)} datasets...")
        records, failed = _extract_batch(
            filtered_ids, settings, console, harmonize, use_llm,
            include_scrna=settings.include_scrna,
        )
        all_failed.extend(failed)
        paths = write_all(records, output_dir, settings.output_format, harmonize)

        state["processed_gse_ids"] = filtered_ids
        state["status"] = "complete"
        manifest["processed_ids"] = len(records)
        manifest["failed_ids"] = [gid for gid, _ in all_failed]
        manifest["completed_at"] = datetime.now(timezone.utc).isoformat()
        manifest["output_paths"] = {k: str(v) for k, v in paths.items()}
        _save_state(run_id, state, settings)
        _save_manifest(run_id, manifest, settings)

    console.print("\n[bold green]Pipeline complete![/bold green]")
    console.print(f"[dim]Run ID: {run_id}[/dim]")
    console.print(f"[dim]Output: {output_dir}[/dim]")


def run_extract(
    gse_ids: list[str],
    settings: Settings,
    harmonize: bool = False,
    console: Console | None = None,
) -> None:
    """Extract metadata from specific GSE IDs (direct mode)."""
    if console is None:
        console = Console()

    output_dir = settings.output_dir
    console.print(f"Extracting metadata for {len(gse_ids)} GSE ID(s)...")

    records, _failed = _extract_batch(
        gse_ids, settings, console, harmonize,
        include_scrna=settings.include_scrna,
    )

    write_all(records, output_dir, settings.output_format, harmonize)
    console.print("\n[bold green]Extraction complete![/bold green]")
    console.print(f"[dim]Output: {output_dir}[/dim]")


def resume_run(
    run_id: str,
    settings: Settings,
    console: Console | None = None,
) -> None:
    """Resume an interrupted pipeline run."""
    if console is None:
        console = Console()

    state = _load_state(run_id, settings)
    if state is None:
        console.print(f"[red]No state found for run ID: {run_id}[/red]")
        raise typer.Exit(1)

    all_ids = state["all_gse_ids"]
    processed = set(state["processed_gse_ids"])
    remaining = [gid for gid in all_ids if gid not in processed]
    harmonize = state.get("harmonize", False)
    use_llm = state.get("use_llm", False)

    if not remaining:
        console.print("[green]All datasets already processed.[/green]")
        return

    console.print(
        f"Resuming run {run_id}: {len(remaining)} remaining "
        f"(of {len(all_ids)} total)"
    )

    output_dir = settings.output_dir
    records, _failed = _extract_batch(
        remaining, settings, console, harmonize, use_llm,
        include_scrna=settings.include_scrna,
    )

    # Merge with existing gse_summary rows (dedup by gse_id; new records win)
    existing_rows = read_gse_summary(output_dir, settings.output_format)
    merged: dict[str, dict] = {row["gse_id"]: row for row in existing_rows}
    for record in records:
        merged[record.gse_id] = gse_to_row(record, harmonize)
        if record.samples:
            write_gsm_file(record, output_dir, settings.output_format, harmonize)

    write_gse_summary_rows(list(merged.values()), output_dir, settings.output_format, harmonize)

    state["processed_gse_ids"] = all_ids
    state["status"] = "complete"
    _save_state(run_id, state, settings)

    console.print("\n[bold green]Resume complete![/bold green]")
