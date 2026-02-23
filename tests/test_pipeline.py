"""Tests for pipeline orchestrator (0.2.0 reliability features)."""

from __future__ import annotations

import csv
import json
from io import StringIO
from unittest.mock import patch

import pytest

from geotcha.config import Settings
from geotcha.models import GSERecord
from geotcha.pipeline import (
    _build_settings_snapshot,
    _save_manifest,
    _save_state,
    resume_run,
    run_pipeline,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def quiet_console():
    from rich.console import Console
    return Console(file=StringIO())


# ---------------------------------------------------------------------------
# Atomic writes
# ---------------------------------------------------------------------------

class TestAtomicStateWrite:
    def test_state_file_created(self, test_settings):
        state = {
            "run_id": "abc", "query": "IBD",
            "all_gse_ids": [], "processed_gse_ids": [], "status": "filtered",
        }
        path = _save_state("abc", state, test_settings)
        assert path.exists()

    def test_state_contents_correct(self, test_settings):
        state = {"run_id": "abc", "query": "IBD", "all_gse_ids": ["GSE1"],
                 "processed_gse_ids": [], "status": "filtered"}
        path = _save_state("abc", state, test_settings)
        loaded = json.loads(path.read_text())
        assert loaded["run_id"] == "abc"
        assert loaded["all_gse_ids"] == ["GSE1"]

    def test_no_tmp_file_left(self, test_settings):
        state = {"run_id": "abc", "query": "IBD", "all_gse_ids": [],
                 "processed_gse_ids": [], "status": "filtered"}
        _save_state("abc", state, test_settings)
        tmp = test_settings.get_data_dir() / "abc" / "state.json.tmp"
        assert not tmp.exists()


# ---------------------------------------------------------------------------
# Run manifest
# ---------------------------------------------------------------------------

class TestRunManifest:
    def test_manifest_created(self, test_settings):
        manifest = {
            "run_id": "m1", "query": "IBD", "started_at": "2026-01-01T00:00:00+00:00",
            "completed_at": None, "pipeline_version": "0.2.0",
            "total_ids": 10, "filtered_ids": 5, "processed_ids": 5,
            "failed_ids": [], "output_paths": {}, "settings_snapshot": {},
        }
        path = _save_manifest("m1", manifest, test_settings)
        assert path.name == "manifest.json"
        assert path.exists()

    def test_manifest_contents(self, test_settings):
        manifest = {"run_id": "m2", "total_ids": 42, "filtered_ids": 7}
        path = _save_manifest("m2", manifest, test_settings)
        loaded = json.loads(path.read_text())
        assert loaded["total_ids"] == 42
        assert loaded["filtered_ids"] == 7

    def test_no_tmp_file_left(self, test_settings):
        _save_manifest("m3", {"run_id": "m3"}, test_settings)
        tmp = test_settings.get_data_dir() / "m3" / "manifest.json.tmp"
        assert not tmp.exists()

    def test_pipeline_writes_manifest(self, tmp_path, quiet_console):
        """manifest.json is present after run_pipeline completes."""
        settings = Settings(
            output_dir=tmp_path / "output",
            data_dir=tmp_path / "data",
            yes=True,
        )
        settings.output_dir.mkdir(parents=True, exist_ok=True)
        record = GSERecord(gse_id="GSE001")

        with patch("geotcha.pipeline.build_query", return_value="IBD"), \
             patch("geotcha.pipeline.search_geo", return_value=["GSE001"]), \
             patch("geotcha.pipeline.filter_results", return_value=["GSE001"]), \
             patch("geotcha.pipeline._extract_batch", return_value=([record], [])), \
             patch("geotcha.pipeline.write_all", return_value={}):
            run_pipeline("IBD", settings, console=quiet_console)

        # Find the manifest (run_id is random, so glob)
        manifests = list(settings.get_data_dir().glob("*/manifest.json"))
        assert len(manifests) == 1
        data = json.loads(manifests[0].read_text())
        assert data["query"] == "IBD"
        assert data["pipeline_version"] == "0.2.0"
        assert "started_at" in data
        assert "settings_snapshot" in data

    def test_manifest_counts_correct(self, tmp_path, quiet_console):
        """Manifest records correct filtered/processed counts."""
        settings = Settings(
            output_dir=tmp_path / "output",
            data_dir=tmp_path / "data",
            yes=True,
        )
        settings.output_dir.mkdir(parents=True, exist_ok=True)
        record = GSERecord(gse_id="GSE001")

        with patch("geotcha.pipeline.build_query", return_value="IBD"), \
             patch("geotcha.pipeline.search_geo", return_value=["GSE001", "GSE002", "GSE003"]), \
             patch("geotcha.pipeline.filter_results", return_value=["GSE001"]), \
             patch("geotcha.pipeline._extract_batch", return_value=([record], [])), \
             patch("geotcha.pipeline.write_all", return_value={}):
            run_pipeline("IBD", settings, console=quiet_console)

        manifests = list(settings.get_data_dir().glob("*/manifest.json"))
        data = json.loads(manifests[0].read_text())
        assert data["total_ids"] == 3
        assert data["filtered_ids"] == 1
        assert data["processed_ids"] == 1


# ---------------------------------------------------------------------------
# Settings snapshot / API key masking
# ---------------------------------------------------------------------------

class TestSettingsSnapshot:
    def test_ncbi_api_key_masked(self, tmp_path):
        settings = Settings(
            ncbi_api_key="super_secret_key_99",
            output_dir=tmp_path / "out",
            data_dir=tmp_path / "data",
        )
        snapshot = _build_settings_snapshot(settings)
        assert "super_secret" not in str(snapshot["ncbi_api_key"])
        assert "****" in str(snapshot["ncbi_api_key"])

    def test_llm_api_key_masked(self, tmp_path):
        settings = Settings(
            llm_api_key="sk-abcdefghij",
            output_dir=tmp_path / "out",
            data_dir=tmp_path / "data",
        )
        snapshot = _build_settings_snapshot(settings)
        assert "abcdefghij" not in str(snapshot["llm_api_key"])
        assert "****" in str(snapshot["llm_api_key"])

    def test_non_key_fields_preserved(self, tmp_path):
        settings = Settings(output_dir=tmp_path / "out", data_dir=tmp_path / "data")
        snapshot = _build_settings_snapshot(settings)
        assert snapshot["ncbi_tool"] == "geotcha"
        assert snapshot["max_retries"] == 3

    def test_short_api_key_masked(self, tmp_path):
        settings = Settings(
            ncbi_api_key="tiny",
            output_dir=tmp_path / "out",
            data_dir=tmp_path / "data",
        )
        snapshot = _build_settings_snapshot(settings)
        assert "****" in str(snapshot["ncbi_api_key"])


# ---------------------------------------------------------------------------
# Resume merge correctness
# ---------------------------------------------------------------------------

class TestResumeMerge:
    def test_resume_merges_existing_and_new(self, test_settings, quiet_console):
        """resume_run produces a gse_summary with existing + new rows."""
        from geotcha.export.writers import write_gse_summary

        output_dir = test_settings.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        # Write 2 existing records to gse_summary
        existing = [
            GSERecord(gse_id="GSE001", title="Study 1"),
            GSERecord(gse_id="GSE002", title="Study 2"),
        ]
        write_gse_summary(existing, output_dir)

        # State: 3 total, 2 processed
        state = {
            "run_id": "run1",
            "query": "IBD",
            "all_gse_ids": ["GSE001", "GSE002", "GSE003"],
            "processed_gse_ids": ["GSE001", "GSE002"],
            "harmonize": False,
            "use_llm": False,
            "status": "subset_complete",
        }
        _save_state("run1", state, test_settings)

        new_record = GSERecord(gse_id="GSE003", title="Study 3")
        with patch("geotcha.pipeline.parse_gse", return_value=new_record):
            resume_run("run1", test_settings, console=quiet_console)

        summary = output_dir / "gse_summary.csv"
        assert summary.exists()
        with open(summary) as f:
            rows = list(csv.DictReader(f))

        gse_ids = {r["gse_id"] for r in rows}
        assert gse_ids == {"GSE001", "GSE002", "GSE003"}
        assert len(rows) == 3

    def test_resume_deduplicates_by_gse_id(self, test_settings, quiet_console):
        """New record with same gse_id replaces existing row."""
        from geotcha.export.writers import write_gse_summary

        output_dir = test_settings.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        write_gse_summary([GSERecord(gse_id="GSE001", title="Old Title")], output_dir)

        state = {
            "run_id": "run2",
            "query": "IBD",
            "all_gse_ids": ["GSE001"],
            "processed_gse_ids": [],
            "harmonize": False,
            "use_llm": False,
            "status": "filtered",
        }
        _save_state("run2", state, test_settings)

        new_record = GSERecord(gse_id="GSE001", title="New Title")
        with patch("geotcha.pipeline.parse_gse", return_value=new_record):
            resume_run("run2", test_settings, console=quiet_console)

        summary = output_dir / "gse_summary.csv"
        with open(summary) as f:
            rows = list(csv.DictReader(f))

        assert len(rows) == 1
        assert rows[0]["title"] == "New Title"

    def test_resume_no_existing_summary(self, test_settings, quiet_console):
        """resume_run works even if gse_summary.csv doesn't exist yet."""
        output_dir = test_settings.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        state = {
            "run_id": "run3",
            "query": "IBD",
            "all_gse_ids": ["GSE001"],
            "processed_gse_ids": [],
            "harmonize": False,
            "use_llm": False,
            "status": "filtered",
        }
        _save_state("run3", state, test_settings)

        record = GSERecord(gse_id="GSE001", title="First Run")
        with patch("geotcha.pipeline.parse_gse", return_value=record):
            resume_run("run3", test_settings, console=quiet_console)

        summary = output_dir / "gse_summary.csv"
        assert summary.exists()
        with open(summary) as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1

    def test_resume_missing_run_id_exits(self, test_settings, quiet_console):
        """resume_run raises Exit for unknown run_id."""
        from click.exceptions import Exit as ClickExit
        with pytest.raises(ClickExit):
            resume_run("nonexistent", test_settings, console=quiet_console)


# ---------------------------------------------------------------------------
# LLM settings propagation
# ---------------------------------------------------------------------------

class TestLLMPropagation:
    def test_llm_provider_passed_to_harmonize(self):
        """Settings.llm_provider is forwarded to llm_harmonize_record."""
        from geotcha.pipeline import _harmonize_record

        record = GSERecord(gse_id="GSE001", tissue="colon", disease="UC")
        settings = Settings(
            llm_provider="anthropic",
            llm_api_key="test-key-xyz",
            llm_model="claude-haiku-4-5",
        )

        with patch("geotcha.harmonize.rules.harmonize_gse", return_value=record), \
             patch("geotcha.harmonize.rules.harmonize_gsm", side_effect=lambda s: s), \
             patch("geotcha.harmonize.llm.llm_harmonize_record") as mock_llm:
            mock_llm.return_value = record
            _harmonize_record(record, use_llm=True, settings=settings)

        mock_llm.assert_called_once_with(
            record,
            provider="anthropic",
            api_key="test-key-xyz",
            model="claude-haiku-4-5",
        )

    def test_llm_defaults_to_openai_without_settings(self):
        """Without settings, LLM defaults to openai provider."""
        from geotcha.pipeline import _harmonize_record

        record = GSERecord(gse_id="GSE001")

        with patch("geotcha.harmonize.rules.harmonize_gse", return_value=record), \
             patch("geotcha.harmonize.rules.harmonize_gsm", side_effect=lambda s: s), \
             patch("geotcha.harmonize.llm.llm_harmonize_record") as mock_llm:
            mock_llm.return_value = record
            _harmonize_record(record, use_llm=True, settings=None)

        mock_llm.assert_called_once_with(
            record,
            provider="openai",
            api_key=None,
            model=None,
        )

    def test_llm_failure_does_not_raise(self):
        """LLM errors are caught and logged, not propagated."""
        from geotcha.pipeline import _harmonize_record

        record = GSERecord(gse_id="GSE001")
        settings = Settings(llm_provider="openai")

        err = RuntimeError("API down")
        with patch("geotcha.harmonize.rules.harmonize_gse", return_value=record), \
             patch("geotcha.harmonize.rules.harmonize_gsm", side_effect=lambda s: s), \
             patch("geotcha.harmonize.llm.llm_harmonize_record", side_effect=err):
            result = _harmonize_record(record, use_llm=True, settings=settings)

        assert result.gse_id == "GSE001"


# ---------------------------------------------------------------------------
# Non-interactive / --yes flag
# ---------------------------------------------------------------------------

class TestNonInteractive:
    def test_yes_flag_skips_prompts(self, tmp_path, quiet_console):
        """`--yes` completes without calling typer.confirm or typer.prompt."""
        settings = Settings(
            output_dir=tmp_path / "output",
            data_dir=tmp_path / "data",
            yes=True,
        )
        settings.output_dir.mkdir(parents=True, exist_ok=True)
        record = GSERecord(gse_id="GSE001")

        with patch("geotcha.pipeline.build_query", return_value="IBD"), \
             patch("geotcha.pipeline.search_geo", return_value=["GSE001"]), \
             patch("geotcha.pipeline.filter_results", return_value=["GSE001"]), \
             patch("geotcha.pipeline._extract_batch", return_value=([record], [])), \
             patch("geotcha.pipeline.write_all", return_value={}), \
             patch("typer.confirm") as mock_confirm, \
             patch("typer.prompt") as mock_prompt:
            run_pipeline("IBD", settings, console=quiet_console)

        mock_confirm.assert_not_called()
        mock_prompt.assert_not_called()

    def test_non_interactive_flag_skips_prompts(self, tmp_path, quiet_console):
        """`--non-interactive` completes without prompts."""
        settings = Settings(
            output_dir=tmp_path / "output",
            data_dir=tmp_path / "data",
            non_interactive=True,
        )
        settings.output_dir.mkdir(parents=True, exist_ok=True)
        record = GSERecord(gse_id="GSE001")

        with patch("geotcha.pipeline.build_query", return_value="IBD"), \
             patch("geotcha.pipeline.search_geo", return_value=["GSE001"]), \
             patch("geotcha.pipeline.filter_results", return_value=["GSE001"]), \
             patch("geotcha.pipeline._extract_batch", return_value=([record], [])), \
             patch("geotcha.pipeline.write_all", return_value={}), \
             patch("typer.confirm") as mock_confirm:
            run_pipeline("IBD", settings, console=quiet_console)

        mock_confirm.assert_not_called()

    def test_explicit_subset_respected_in_non_interactive(self, tmp_path, quiet_console):
        """Explicit --subset is used even in non-interactive mode."""
        settings = Settings(
            output_dir=tmp_path / "output",
            data_dir=tmp_path / "data",
            yes=True,
        )
        settings.output_dir.mkdir(parents=True, exist_ok=True)
        records = [GSERecord(gse_id=f"GSE00{i}") for i in range(3)]

        all_ids = ["GSE001", "GSE002", "GSE003"]
        extract_ret = ([records[0]], [])
        with patch("geotcha.pipeline.build_query", return_value="IBD"), \
             patch("geotcha.pipeline.search_geo", return_value=all_ids), \
             patch("geotcha.pipeline.filter_results", return_value=all_ids), \
             patch("geotcha.pipeline._extract_batch", return_value=extract_ret) as mock_extract, \
             patch("geotcha.pipeline.write_all", return_value={}):
            # subset_size=1 out of 3 → first batch has 1, then 2 remaining (auto-proceed)
            run_pipeline("IBD", settings, subset_size=1, console=quiet_console)

        # Called twice: once for subset, once for remaining
        assert mock_extract.call_count == 2
