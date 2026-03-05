"""Tests for benchmark infrastructure."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from geotcha.benchmark import (
    BenchmarkResult,
    FieldMetrics,
    _build_gse_record,
    _compare_field,
    load_fixtures,
    run_benchmark,
    write_report,
)

# ---------------------------------------------------------------------------
# Fixture loading
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "benchmark"


class TestLoadFixtures:
    def test_loads_all_fixtures(self):
        fixtures = load_fixtures(FIXTURES_DIR)
        assert len(fixtures) == 20

    def test_fixture_has_required_keys(self):
        fixtures = load_fixtures(FIXTURES_DIR)
        for f in fixtures:
            assert "gse_id" in f
            assert "input" in f
            assert "expected" in f

    def test_missing_index_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_fixtures(tmp_path)


# ---------------------------------------------------------------------------
# Metric computation
# ---------------------------------------------------------------------------

class TestCompareField:
    def test_exact_match(self):
        assert _compare_field("colon", "colon") is True

    def test_case_insensitive(self):
        assert _compare_field("Colon", "colon") is True

    def test_mismatch(self):
        assert _compare_field("colon", "liver") is False

    def test_none_both(self):
        assert _compare_field(None, None) is True

    def test_none_one(self):
        assert _compare_field(None, "colon") is False
        assert _compare_field("colon", None) is False


class TestRunBenchmark:
    def test_returns_benchmark_result(self):
        fixtures = load_fixtures(FIXTURES_DIR)
        result = run_benchmark(fixtures)
        assert isinstance(result, BenchmarkResult)

    def test_fixture_count(self):
        fixtures = load_fixtures(FIXTURES_DIR)
        result = run_benchmark(fixtures)
        assert result.fixture_count == 20

    def test_summary_keys(self):
        fixtures = load_fixtures(FIXTURES_DIR)
        result = run_benchmark(fixtures)
        assert "overall_exact_match" in result.summary
        assert "overall_completeness" in result.summary
        assert "overall_ontology_coverage" in result.summary

    def test_per_field_populated(self):
        fixtures = load_fixtures(FIXTURES_DIR)
        result = run_benchmark(fixtures)
        assert "tissue" in result.per_field
        assert "disease" in result.per_field
        assert isinstance(result.per_field["tissue"], FieldMetrics)

    def test_tissue_has_high_accuracy(self):
        fixtures = load_fixtures(FIXTURES_DIR)
        result = run_benchmark(fixtures)
        assert result.per_field["tissue"].exact_match >= 0.8

    def test_ml_mode_recorded(self):
        fixtures = load_fixtures(FIXTURES_DIR)
        result = run_benchmark(fixtures, ml_mode="off")
        assert result.ml_mode == "off"


class TestRunBenchmarkMinimal:
    def test_single_fixture(self, tmp_path):
        fixture = {
            "gse_id": "GSE_TEST",
            "input": {"tissue": "colon", "disease": "UC"},
            "expected": {
                "tissue_harmonized": "colon",
                "disease_harmonized": "ulcerative colitis",
            },
            "samples": [],
        }
        result = run_benchmark([fixture])
        assert result.fixture_count == 1
        assert result.per_field["tissue"].correct == 1
        assert result.per_field["disease"].correct == 1

    def test_empty_fixtures(self):
        result = run_benchmark([])
        assert result.fixture_count == 0
        assert result.summary == {}


# ---------------------------------------------------------------------------
# Report writing
# ---------------------------------------------------------------------------

class TestWriteReport:
    def test_writes_json(self, tmp_path):
        result = BenchmarkResult(fixture_count=5)
        out = tmp_path / "report.json"
        path = write_report(result, out)
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["fixture_count"] == 5

    def test_creates_parent_dirs(self, tmp_path):
        out = tmp_path / "sub" / "dir" / "report.json"
        write_report(BenchmarkResult(), out)
        assert out.exists()

    def test_report_has_version(self, tmp_path):
        from geotcha import __version__
        result = BenchmarkResult()
        out = tmp_path / "report.json"
        write_report(result, out)
        data = json.loads(out.read_text())
        assert data["benchmark_version"] == __version__


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestBuildGseRecord:
    def test_builds_from_fixture(self):
        fixture = {
            "gse_id": "GSE999",
            "input": {"title": "Test", "tissue": "brain"},
            "expected": {},
            "samples": [
                {"gsm_id": "GSM001", "input": {"tissue": "brain", "gender": "M"}, "expected": {}}
            ],
        }
        record = _build_gse_record(fixture)
        assert record.gse_id == "GSE999"
        assert record.tissue == "brain"
        assert len(record.samples) == 1
        assert record.samples[0].gender == "M"

    def test_no_samples(self):
        fixture = {
            "gse_id": "GSE999",
            "input": {"tissue": "liver"},
            "expected": {},
        }
        record = _build_gse_record(fixture)
        assert len(record.samples) == 0


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------

class TestBenchmarkCLI:
    def test_benchmark_command_exists(self):
        from geotcha.cli import app
        command_names = [cmd.callback.__name__ for cmd in app.registered_commands if cmd.callback]
        assert "benchmark" in command_names

    def test_benchmark_cli_runs(self):
        from typer.testing import CliRunner

        from geotcha.cli import app

        runner = CliRunner()
        result = runner.invoke(app, [
            "benchmark",
            "--input", str(FIXTURES_DIR),
            "--output", "/tmp/geotcha_test_benchmark_report.json",
        ])
        assert result.exit_code == 0
        assert "Benchmark Results" in result.stdout

    def test_benchmark_cli_missing_dir(self):
        from typer.testing import CliRunner

        from geotcha.cli import app

        runner = CliRunner()
        result = runner.invoke(app, [
            "benchmark",
            "--input", "/nonexistent/path",
        ])
        assert result.exit_code != 0
