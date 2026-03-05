"""Tests for the GEOtchaClient Python SDK."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from geotcha.api import GEOtchaClient
from geotcha.config import Settings
from geotcha.models import GSERecord, GSMRecord

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        output_dir=tmp_path / "output",
        cache_dir=tmp_path / "cache",
        data_dir=tmp_path / "data",
    )


@pytest.fixture
def client(settings: Settings) -> GEOtchaClient:
    return GEOtchaClient(settings=settings)


@pytest.fixture
def sample_gsm() -> GSMRecord:
    return GSMRecord(
        gsm_id="GSM111",
        gse_id="GSE99",
        title="Test sample",
        source_name="colon",
        organism="Homo sapiens",
        molecule="total RNA",
        platform_id="GPL20301",
        instrument="HiSeq",
        library_strategy="RNA-Seq",
        library_source="transcriptomic",
        characteristics={},
        tissue="colon",
        disease="ulcerative colitis",
    )


@pytest.fixture
def sample_gse(sample_gsm: GSMRecord) -> GSERecord:
    return GSERecord(
        gse_id="GSE99",
        title="UC study",
        summary="Test",
        overall_design="Test",
        organism=["Homo sapiens"],
        experiment_type=["Expression profiling by high throughput sequencing"],
        platform=["GPL20301"],
        total_samples=1,
        human_rnaseq_samples=1,
        pubmed_ids=[],
        gse_url="https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE99",
        samples=[sample_gsm],
    )


# ---------------------------------------------------------------------------
# TestGEOtchaClientSearch
# ---------------------------------------------------------------------------


class TestGEOtchaClientSearch:
    def test_returns_list_of_strings(self, client: GEOtchaClient) -> None:
        with (
            patch(
                "geotcha.search.entrez.search_geo", return_value=["GSE1", "GSE2"]
            ) as mock_search,
            patch(
                "geotcha.search.filters.filter_results", return_value=["GSE1"]
            ) as mock_filter,
            patch(
                "geotcha.search.query_builder.build_query",
                return_value="(colitis) AND ...",
            ) as mock_bq,
        ):
            result = client.search("colitis")

        assert result == ["GSE1"]
        mock_bq.assert_called_once_with("colitis")
        mock_search.assert_called_once()
        mock_filter.assert_called_once()

    def test_empty_results(self, client: GEOtchaClient) -> None:
        with (
            patch("geotcha.search.entrez.search_geo", return_value=[]),
            patch("geotcha.search.filters.filter_results", return_value=[]),
            patch("geotcha.search.query_builder.build_query", return_value="query"),
        ):
            result = client.search("no match")

        assert result == []


# ---------------------------------------------------------------------------
# TestGEOtchaClientExtract
# ---------------------------------------------------------------------------


class TestGEOtchaClientExtract:
    def test_returns_records(self, client: GEOtchaClient, sample_gse: GSERecord) -> None:
        with patch("geotcha.extract.gse_parser.parse_gse", return_value=sample_gse):
            result = client.extract(["GSE99"])

        assert len(result) == 1
        assert result[0].gse_id == "GSE99"

    def test_failed_parse_skipped(self, client: GEOtchaClient) -> None:
        with patch(
            "geotcha.extract.gse_parser.parse_gse",
            side_effect=RuntimeError("SOFT parse error"),
        ):
            result = client.extract(["GSE_BAD"])

        assert result == []

    def test_partial_failure(self, client: GEOtchaClient, sample_gse: GSERecord) -> None:
        def _parse(gse_id: str, settings: Settings) -> GSERecord:
            if gse_id == "GSE_BAD":
                raise RuntimeError("fail")
            return sample_gse

        with patch("geotcha.extract.gse_parser.parse_gse", side_effect=_parse):
            result = client.extract(["GSE_BAD", "GSE99"])

        assert len(result) == 1
        assert result[0].gse_id == "GSE99"


# ---------------------------------------------------------------------------
# TestGEOtchaClientHarmonize
# ---------------------------------------------------------------------------


class TestGEOtchaClientHarmonize:
    def test_harmonize_sets_harmonized_fields(
        self, client: GEOtchaClient, sample_gse: GSERecord
    ) -> None:
        result = client.harmonize([sample_gse])
        assert result is not None
        assert len(result) == 1
        assert result[0].gse_id == "GSE99"

    def test_harmonize_returns_same_list(
        self, client: GEOtchaClient, sample_gse: GSERecord
    ) -> None:
        records = [sample_gse]
        result = client.harmonize(records)
        assert result is records


# ---------------------------------------------------------------------------
# TestGEOtchaClientExport
# ---------------------------------------------------------------------------


class TestGEOtchaClientExport:
    def test_calls_write_all_with_correct_args(
        self, client: GEOtchaClient, sample_gse: GSERecord, tmp_path: Path
    ) -> None:
        expected = {"gse_summary": tmp_path / "gse_summary.csv"}
        with patch("geotcha.export.writers.write_all", return_value=expected) as mock_write:
            result = client.export([sample_gse], tmp_path, fmt="csv", harmonized=False)

        mock_write.assert_called_once_with(
            [sample_gse], tmp_path, fmt="csv", harmonized=False
        )
        assert result == expected

    def test_returns_paths_dict(
        self, client: GEOtchaClient, sample_gse: GSERecord, tmp_path: Path
    ) -> None:
        ret = {"gse_summary": tmp_path / "x.csv"}
        with patch("geotcha.export.writers.write_all", return_value=ret):
            result = client.export([sample_gse], tmp_path)

        assert "gse_summary" in result


# ---------------------------------------------------------------------------
# TestGEOtchaClientRun
# ---------------------------------------------------------------------------


class TestGEOtchaClientRun:
    def test_run_full_pipeline(
        self, client: GEOtchaClient, sample_gse: GSERecord, tmp_path: Path
    ) -> None:
        with (
            patch.object(client, "search", return_value=["GSE99"]) as mock_search,
            patch.object(client, "extract", return_value=[sample_gse]) as mock_extract,
            patch.object(client, "harmonize", return_value=[sample_gse]) as mock_harmonize,
            patch.object(client, "export", return_value={}) as mock_export,
        ):
            result = client.run("colitis", output_dir=tmp_path, harmonize=True, fmt="tsv")

        mock_search.assert_called_once_with("colitis")
        mock_extract.assert_called_once_with(["GSE99"])
        mock_harmonize.assert_called_once_with([sample_gse], ml_mode="off")
        mock_export.assert_called_once_with(
            [sample_gse], tmp_path, fmt="tsv", harmonized=True
        )
        assert result == [sample_gse]

    def test_run_without_harmonize_skips_harmonize(
        self, client: GEOtchaClient, sample_gse: GSERecord
    ) -> None:
        with (
            patch.object(client, "search", return_value=["GSE99"]),
            patch.object(client, "extract", return_value=[sample_gse]),
            patch.object(client, "harmonize") as mock_harmonize,
        ):
            client.run("colitis")

        mock_harmonize.assert_not_called()

    def test_run_without_output_dir_skips_export(
        self, client: GEOtchaClient, sample_gse: GSERecord
    ) -> None:
        with (
            patch.object(client, "search", return_value=["GSE99"]),
            patch.object(client, "extract", return_value=[sample_gse]),
            patch.object(client, "export") as mock_export,
        ):
            client.run("colitis", output_dir=None)

        mock_export.assert_not_called()


# ---------------------------------------------------------------------------
# test_no_typer_rich_imported
# ---------------------------------------------------------------------------


def test_no_typer_rich_imported() -> None:
    """Importing geotcha.api must not pull in typer or rich."""
    import importlib
    import sys

    # Remove cached module to force fresh import check
    for mod in list(sys.modules.keys()):
        if mod.startswith("geotcha.api"):
            del sys.modules[mod]

    # Clear typer/rich from modules to detect if api re-imports them
    saved_typer = sys.modules.pop("typer", None)
    saved_rich = sys.modules.pop("rich", None)

    try:
        importlib.import_module("geotcha.api")
        assert "typer" not in sys.modules, "geotcha.api must not import typer"
        assert "rich" not in sys.modules, "geotcha.api must not import rich"
    finally:
        if saved_typer is not None:
            sys.modules["typer"] = saved_typer
        if saved_rich is not None:
            sys.modules["rich"] = saved_rich
