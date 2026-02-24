"""Tests for parallel extraction in the pipeline (0.3.0 performance features)."""

from __future__ import annotations

import time
from io import StringIO
from unittest.mock import patch

import pytest

from geotcha.config import Settings
from geotcha.models import GSERecord, GSMRecord
from geotcha.pipeline import _extract_batch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_gse(gse_id: str, n_samples: int = 0) -> GSERecord:
    """Create a minimal GSERecord for testing."""
    samples = [
        GSMRecord(
            gsm_id=f"GSM{i:03d}",
            gse_id=gse_id,
            title=f"Sample {i}",
            source_name="biopsy",
            organism="Homo sapiens",
            molecule="total RNA",
            platform_id="GPL123",
            instrument="Illumina HiSeq",
            library_strategy="RNA-Seq",
            library_source="transcriptomic",
            characteristics={},
        )
        for i in range(n_samples)
    ]
    return GSERecord(
        gse_id=gse_id,
        title=f"Study {gse_id}",
        summary="",
        overall_design="",
        organism=["Homo sapiens"],
        experiment_type=["Expression profiling by high throughput sequencing"],
        platform=["GPL123"],
        total_samples=n_samples,
        human_rnaseq_samples=n_samples,
        pubmed_ids=[],
        gse_url=f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={gse_id}",
        samples=samples,
    )


@pytest.fixture
def quiet_console():
    from rich.console import Console
    return Console(file=StringIO())


@pytest.fixture
def parallel_settings(tmp_path):
    """Settings with an API key to allow up to 6 parallel workers."""
    return Settings(
        output_dir=tmp_path / "output",
        cache_dir=tmp_path / "cache",
        data_dir=tmp_path / "data",
        ncbi_api_key="testkey123456",
        max_workers=4,
    )


# ---------------------------------------------------------------------------
# Worker capping
# ---------------------------------------------------------------------------

class TestWorkerCapping:
    def test_no_api_key_capped_at_2(self):
        settings = Settings(max_workers=4)
        assert settings.get_effective_max_workers() == 2

    def test_no_api_key_custom_value_also_capped(self):
        settings = Settings(max_workers=8)
        assert settings.get_effective_max_workers() == 2

    def test_with_api_key_respects_max_workers(self):
        settings = Settings(ncbi_api_key="key123456", max_workers=4)
        assert settings.get_effective_max_workers() == 4

    def test_with_api_key_capped_at_6(self):
        settings = Settings(ncbi_api_key="key123456", max_workers=10)
        assert settings.get_effective_max_workers() == 6

    def test_with_api_key_low_max_workers_respected(self):
        settings = Settings(ncbi_api_key="key123456", max_workers=2)
        assert settings.get_effective_max_workers() == 2

    def test_default_max_workers_is_4(self):
        settings = Settings()
        assert settings.max_workers == 4


# ---------------------------------------------------------------------------
# Output ordering
# ---------------------------------------------------------------------------

class TestOrderPreservation:
    def test_records_returned_in_submission_order(
        self, parallel_settings, quiet_console
    ):
        """Records are ordered by original GSE ID list position, not completion time."""
        gse_ids = ["GSE001", "GSE002", "GSE003"]
        record_map = {gid: _make_gse(gid) for gid in gse_ids}

        def mock_parse(gse_id, settings, include_scrna=False):
            # Delay the first GSE so the others likely finish before it
            if gse_id == "GSE001":
                time.sleep(0.05)
            return record_map[gse_id]

        with patch("geotcha.pipeline.parse_gse", side_effect=mock_parse):
            returned, failed = _extract_batch(
                gse_ids, parallel_settings, quiet_console
            )

        assert failed == []
        assert [r.gse_id for r in returned] == gse_ids

    def test_empty_batch_returns_empty(self, test_settings, quiet_console):
        returned, failed = _extract_batch([], test_settings, quiet_console)
        assert returned == []
        assert failed == []

    def test_single_gse_returned_correctly(self, test_settings, quiet_console):
        with patch(
            "geotcha.pipeline.parse_gse",
            return_value=_make_gse("GSE001"),
        ):
            returned, failed = _extract_batch(["GSE001"], test_settings, quiet_console)

        assert len(returned) == 1
        assert returned[0].gse_id == "GSE001"
        assert failed == []


# ---------------------------------------------------------------------------
# Failed-GSE isolation
# ---------------------------------------------------------------------------

class TestFailedGSEIsolation:
    def test_single_failure_does_not_abort_batch(
        self, test_settings, quiet_console
    ):
        """A failing GSE is recorded in failed; the rest succeed."""
        gse_ids = ["GSE001", "GSE002", "GSE003"]

        def mock_parse(gse_id, settings, include_scrna=False):
            if gse_id == "GSE002":
                raise ValueError("Simulated download failure")
            return _make_gse(gse_id)

        with patch("geotcha.pipeline.parse_gse", side_effect=mock_parse):
            returned, failed = _extract_batch(gse_ids, test_settings, quiet_console)

        assert len(returned) == 2
        assert len(failed) == 1
        assert failed[0][0] == "GSE002"
        assert {r.gse_id for r in returned} == {"GSE001", "GSE003"}

    def test_all_failures_returns_empty_records(self, test_settings, quiet_console):
        gse_ids = ["GSE001", "GSE002"]
        with patch(
            "geotcha.pipeline.parse_gse",
            side_effect=RuntimeError("network error"),
        ):
            returned, failed = _extract_batch(gse_ids, test_settings, quiet_console)

        assert returned == []
        assert len(failed) == 2
        assert {f[0] for f in failed} == set(gse_ids)

    def test_failure_message_captured(self, test_settings, quiet_console):
        with patch(
            "geotcha.pipeline.parse_gse",
            side_effect=ValueError("timeout after 120s"),
        ):
            _, failed = _extract_batch(["GSE001"], test_settings, quiet_console)

        assert "timeout after 120s" in failed[0][1]


# ---------------------------------------------------------------------------
# Streaming GSM writes
# ---------------------------------------------------------------------------

class TestStreamingGSMWrite:
    def test_gsm_files_written_when_output_dir_provided(
        self, test_settings, quiet_console
    ):
        """GSM files are written immediately per-GSE when output_dir is given."""
        gse_ids = ["GSE001", "GSE002"]

        with patch(
            "geotcha.pipeline.parse_gse",
            side_effect=lambda gid, *a, **kw: _make_gse(gid, n_samples=2),
        ):
            returned, failed = _extract_batch(
                gse_ids,
                test_settings,
                quiet_console,
                output_dir=test_settings.output_dir,
                fmt="csv",
            )

        assert failed == []
        gsm_dir = test_settings.output_dir / "gsm"
        assert (gsm_dir / "GSE001_samples.csv").exists()
        assert (gsm_dir / "GSE002_samples.csv").exists()

    def test_no_gsm_writes_when_output_dir_none(self, test_settings, quiet_console):
        """No in-flight GSM writes when output_dir=None."""
        with patch(
            "geotcha.pipeline.parse_gse",
            return_value=_make_gse("GSE001", n_samples=2),
        ):
            with patch("geotcha.pipeline.write_gsm_file") as mock_write:
                _extract_batch(
                    ["GSE001"],
                    test_settings,
                    quiet_console,
                    output_dir=None,
                )
                mock_write.assert_not_called()

    def test_gse_without_samples_no_gsm_write(self, test_settings, quiet_console):
        """GSEs with no samples don't produce GSM files."""
        with patch(
            "geotcha.pipeline.parse_gse",
            return_value=_make_gse("GSE001", n_samples=0),
        ):
            returned, failed = _extract_batch(
                ["GSE001"],
                test_settings,
                quiet_console,
                output_dir=test_settings.output_dir,
                fmt="csv",
            )

        assert failed == []
        gsm_dir = test_settings.output_dir / "gsm"
        assert not (gsm_dir / "GSE001_samples.csv").exists()
