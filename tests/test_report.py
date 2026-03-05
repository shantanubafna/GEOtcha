"""Tests for the geotcha report command."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from geotcha.cli import app
from geotcha.config import Settings

runner = CliRunner()


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        output_dir=tmp_path / "output",
        cache_dir=tmp_path / "cache",
        data_dir=tmp_path / "data",
    )


@pytest.fixture
def sample_manifest() -> dict:
    return {
        "run_id": "abc12345",
        "query": "ulcerative colitis",
        "started_at": "2026-02-24T10:00:00+00:00",
        "completed_at": "2026-02-24T10:05:00+00:00",
        "pipeline_version": "0.6.0",
        "total_ids": 50,
        "filtered_ids": 12,
        "processed_ids": 12,
        "failed_ids": ["GSE_BAD1"],
        "output_paths": {"gse_summary": "/tmp/output/gse_summary.csv"},
        "settings_snapshot": {},
        "stage_timings": {"search": 1.23, "extract": 45.67, "export": 0.89},
    }


@pytest.fixture
def manifest_file(tmp_path: Path, sample_manifest: dict) -> Path:
    run_dir = tmp_path / "data" / "abc12345"
    run_dir.mkdir(parents=True)
    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(json.dumps(sample_manifest, indent=2))
    return manifest_path


class TestReportReadsManifest:
    def test_report_prints_run_id(
        self, tmp_path: Path, manifest_file: Path, settings: Settings
    ) -> None:
        with patch("geotcha.config.Settings.load", return_value=settings):
            result = runner.invoke(app, ["report", "abc12345"])

        assert result.exit_code == 0
        assert "abc12345" in result.output

    def test_report_shows_query(
        self, tmp_path: Path, manifest_file: Path, settings: Settings
    ) -> None:
        with patch("geotcha.config.Settings.load", return_value=settings):
            result = runner.invoke(app, ["report", "abc12345"])

        assert "ulcerative colitis" in result.output

    def test_report_shows_id_counts(
        self, tmp_path: Path, manifest_file: Path, settings: Settings
    ) -> None:
        with patch("geotcha.config.Settings.load", return_value=settings):
            result = runner.invoke(app, ["report", "abc12345"])

        assert "50" in result.output
        assert "12" in result.output

    def test_report_shows_failed_ids(
        self, tmp_path: Path, manifest_file: Path, settings: Settings
    ) -> None:
        with patch("geotcha.config.Settings.load", return_value=settings):
            result = runner.invoke(app, ["report", "abc12345"])

        assert "GSE_BAD1" in result.output

    def test_report_shows_stage_timings(
        self, tmp_path: Path, manifest_file: Path, settings: Settings
    ) -> None:
        with patch("geotcha.config.Settings.load", return_value=settings):
            result = runner.invoke(app, ["report", "abc12345"])

        assert "search" in result.output
        assert "1.23" in result.output


class TestReportJsonWritten:
    def test_report_json_created_in_manifest_dir(
        self, tmp_path: Path, manifest_file: Path, settings: Settings
    ) -> None:
        with patch("geotcha.config.Settings.load", return_value=settings):
            result = runner.invoke(app, ["report", "abc12345"])

        assert result.exit_code == 0
        report_path = manifest_file.parent / "report.json"
        assert report_path.exists()

    def test_report_json_has_required_keys(
        self, tmp_path: Path, manifest_file: Path, settings: Settings
    ) -> None:
        with patch("geotcha.config.Settings.load", return_value=settings):
            runner.invoke(app, ["report", "abc12345"])

        report_path = manifest_file.parent / "report.json"
        data = json.loads(report_path.read_text())
        assert data["run_id"] == "abc12345"
        assert "stage_timings" in data
        assert data["stage_timings"]["search"] == 1.23

    def test_report_json_written_to_custom_output(
        self, tmp_path: Path, manifest_file: Path, settings: Settings
    ) -> None:
        custom_out = tmp_path / "reports"
        with patch("geotcha.config.Settings.load", return_value=settings):
            result = runner.invoke(
                app, ["report", "abc12345", "--output", str(custom_out)]
            )

        assert result.exit_code == 0
        assert (custom_out / "report.json").exists()


class TestReportMissingRunId:
    def test_missing_run_id_exits_with_error(
        self, tmp_path: Path, settings: Settings
    ) -> None:
        with patch("geotcha.config.Settings.load", return_value=settings):
            result = runner.invoke(app, ["report", "nonexistent_run"])

        assert result.exit_code == 1
        assert "not found" in result.output.lower() or "nonexistent_run" in result.output

    def test_missing_run_id_no_traceback(
        self, tmp_path: Path, settings: Settings
    ) -> None:
        with patch("geotcha.config.Settings.load", return_value=settings):
            result = runner.invoke(app, ["report", "totally_bogus"])

        # Should not contain Python traceback
        assert "Traceback" not in result.output
        assert result.exit_code == 1
