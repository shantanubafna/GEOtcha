"""Tests for Parquet output writers."""

from __future__ import annotations

from pathlib import Path

import pytest

pyarrow = pytest.importorskip("pyarrow")

from geotcha.export.writers import write_all, write_gse_parquet, write_gsm_parquet  # noqa: E402
from geotcha.models import GSERecord, GSMRecord  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_gsm() -> GSMRecord:
    return GSMRecord(
        gsm_id="GSM777",
        gse_id="GSE42",
        title="Colon biopsy",
        source_name="colon biopsy",
        organism="Homo sapiens",
        molecule="total RNA",
        platform_id="GPL20301",
        instrument="HiSeq 2500",
        library_strategy="RNA-Seq",
        library_source="transcriptomic",
        characteristics={"tissue": "colon"},
        tissue="colon",
        disease="ulcerative colitis",
        gender="male",
        age="40",
    )


@pytest.fixture
def sample_gse(sample_gsm: GSMRecord) -> GSERecord:
    return GSERecord(
        gse_id="GSE42",
        title="UC transcriptomics",
        summary="Test study",
        overall_design="Colon biopsies",
        organism=["Homo sapiens"],
        experiment_type=["Expression profiling by high throughput sequencing"],
        platform=["GPL20301"],
        total_samples=1,
        human_rnaseq_samples=1,
        pubmed_ids=["99999"],
        gse_url="https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE42",
        tissue="colon",
        disease="ulcerative colitis",
        samples=[sample_gsm],
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestWriteGSEParquet:
    def test_creates_file(self, sample_gse: GSERecord, tmp_path: Path) -> None:
        path = write_gse_parquet([sample_gse], tmp_path)
        assert path.exists()
        assert path.name == "gse_summary.parquet"

    def test_readable(self, sample_gse: GSERecord, tmp_path: Path) -> None:
        import pyarrow.parquet as pq

        write_gse_parquet([sample_gse], tmp_path)
        table = pq.read_table(tmp_path / "gse_summary.parquet")
        assert table.num_rows == 1

    def test_has_expected_columns(self, sample_gse: GSERecord, tmp_path: Path) -> None:
        import pyarrow.parquet as pq

        write_gse_parquet([sample_gse], tmp_path)
        table = pq.read_table(tmp_path / "gse_summary.parquet")
        assert "gse_id" in table.schema.names
        assert "disease" in table.schema.names
        assert "title" in table.schema.names

    def test_creates_output_dir(self, sample_gse: GSERecord, tmp_path: Path) -> None:
        nested = tmp_path / "nested" / "dir"
        write_gse_parquet([sample_gse], nested)
        assert nested.exists()


class TestWriteGSMParquet:
    def test_creates_file(self, sample_gse: GSERecord, tmp_path: Path) -> None:
        path = write_gsm_parquet(sample_gse, tmp_path)
        assert path.exists()
        assert path.name == "GSE42_samples.parquet"

    def test_file_in_gsm_subdir(self, sample_gse: GSERecord, tmp_path: Path) -> None:
        path = write_gsm_parquet(sample_gse, tmp_path)
        assert path.parent.name == "gsm"

    def test_readable(self, sample_gse: GSERecord, tmp_path: Path) -> None:
        import pyarrow.parquet as pq

        write_gsm_parquet(sample_gse, tmp_path)
        table = pq.read_table(tmp_path / "gsm" / "GSE42_samples.parquet")
        assert table.num_rows == 1

    def test_has_gsm_columns(self, sample_gse: GSERecord, tmp_path: Path) -> None:
        import pyarrow.parquet as pq

        write_gsm_parquet(sample_gse, tmp_path)
        table = pq.read_table(tmp_path / "gsm" / "GSE42_samples.parquet")
        assert "gsm_id" in table.schema.names
        assert "tissue" in table.schema.names


class TestWriteAllParquetFmt:
    def test_returns_paths_dict(self, sample_gse: GSERecord, tmp_path: Path) -> None:
        paths = write_all([sample_gse], tmp_path, fmt="parquet")
        assert "gse_summary" in paths
        assert "GSE42" in paths

    def test_gse_summary_is_parquet(self, sample_gse: GSERecord, tmp_path: Path) -> None:
        paths = write_all([sample_gse], tmp_path, fmt="parquet")
        assert paths["gse_summary"].suffix == ".parquet"
        assert paths["gse_summary"].exists()

    def test_gsm_file_is_parquet(self, sample_gse: GSERecord, tmp_path: Path) -> None:
        paths = write_all([sample_gse], tmp_path, fmt="parquet")
        assert paths["GSE42"].suffix == ".parquet"
        assert paths["GSE42"].exists()

    def test_parquet_readable_row_count(self, sample_gse: GSERecord, tmp_path: Path) -> None:
        import pyarrow.parquet as pq

        write_all([sample_gse], tmp_path, fmt="parquet")
        table = pq.read_table(tmp_path / "gse_summary.parquet")
        assert table.num_rows == 1


class TestParquetHarmonizedColumns:
    def test_harmonized_columns_present(self, sample_gse: GSERecord, tmp_path: Path) -> None:
        import pyarrow.parquet as pq

        from geotcha.harmonize.rules import harmonize_gse, harmonize_gsm

        harmonize_gse(sample_gse)
        for s in sample_gse.samples:
            harmonize_gsm(s)

        write_gse_parquet([sample_gse], tmp_path, harmonized=True)
        table = pq.read_table(tmp_path / "gse_summary.parquet")
        assert "tissue_harmonized" in table.schema.names
        assert "disease_harmonized" in table.schema.names

    def test_gsm_harmonized_columns_present(
        self, sample_gse: GSERecord, tmp_path: Path
    ) -> None:
        import pyarrow.parquet as pq

        from geotcha.harmonize.rules import harmonize_gse, harmonize_gsm

        harmonize_gse(sample_gse)
        for s in sample_gse.samples:
            harmonize_gsm(s)

        write_gsm_parquet(sample_gse, tmp_path, harmonized=True)
        table = pq.read_table(tmp_path / "gsm" / "GSE42_samples.parquet")
        assert "tissue_harmonized" in table.schema.names
        assert "disease_harmonized" in table.schema.names
