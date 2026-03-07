"""Benchmark regression guard — ensures harmonization quality stays above thresholds."""

from __future__ import annotations

from pathlib import Path

import pytest

from geotcha.benchmark import load_fixtures, run_benchmark

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "benchmark"

# Minimum acceptable scores (blocking)
MIN_EXACT_MATCH = 0.90
MIN_COMPLETENESS = 0.95


@pytest.fixture(scope="module")
def benchmark_result():
    fixtures = load_fixtures(FIXTURES_DIR)
    return run_benchmark(fixtures)


class TestBenchmarkRegression:
    def test_fixture_count(self, benchmark_result):
        assert benchmark_result.fixture_count >= 100

    def test_overall_exact_match(self, benchmark_result):
        score = benchmark_result.summary["overall_exact_match"]
        assert score >= MIN_EXACT_MATCH, (
            f"overall_exact_match {score:.4f} < {MIN_EXACT_MATCH}"
        )

    def test_overall_completeness(self, benchmark_result):
        score = benchmark_result.summary["overall_completeness"]
        assert score >= MIN_COMPLETENESS, (
            f"overall_completeness {score:.4f} < {MIN_COMPLETENESS}"
        )

    def test_tissue_exact_match(self, benchmark_result):
        m = benchmark_result.per_field.get("tissue")
        assert m is not None
        assert m.exact_match >= 0.85, f"tissue exact_match {m.exact_match:.4f} < 0.85"

    def test_disease_exact_match(self, benchmark_result):
        m = benchmark_result.per_field.get("disease")
        assert m is not None
        assert m.exact_match >= 0.90, f"disease exact_match {m.exact_match:.4f} < 0.90"

    def test_treatment_exact_match(self, benchmark_result):
        m = benchmark_result.per_field.get("treatment")
        assert m is not None
        assert m.exact_match >= 0.90, f"treatment exact_match {m.exact_match:.4f} < 0.90"

    def test_gender_exact_match(self, benchmark_result):
        m = benchmark_result.per_field.get("gender")
        assert m is not None
        assert m.exact_match >= 0.95, f"gender exact_match {m.exact_match:.4f} < 0.95"

    def test_age_exact_match(self, benchmark_result):
        m = benchmark_result.per_field.get("age")
        assert m is not None
        assert m.exact_match >= 0.95, f"age exact_match {m.exact_match:.4f} < 0.95"
