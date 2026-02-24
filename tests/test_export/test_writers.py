"""Tests for export writers."""

import csv
from pathlib import Path

from geotcha.export.writers import (
    open_gse_summary_writer,
    write_all,
    write_gse_summary,
    write_gsm_file,
    write_review_queue,
)
from geotcha.harmonize.rules import harmonize_gse, harmonize_gsm
from geotcha.models import GSERecord, GSMRecord


class TestWriteGSESummary:
    def test_writes_csv(self, sample_gse: GSERecord, tmp_output: Path):
        path = write_gse_summary([sample_gse], tmp_output, fmt="csv")
        assert path.exists()
        assert path.suffix == ".csv"

        with open(path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            assert rows[0]["gse_id"] == "GSE12345"

    def test_writes_tsv(self, sample_gse: GSERecord, tmp_output: Path):
        path = write_gse_summary([sample_gse], tmp_output, fmt="tsv")
        assert path.suffix == ".tsv"

    def test_harmonized_columns(self, sample_gse: GSERecord, tmp_output: Path):
        sample_gse.tissue_harmonized = "colon"
        path = write_gse_summary([sample_gse], tmp_output, harmonized=True)

        with open(path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert "tissue_harmonized" in rows[0]


class TestWriteGSMFile:
    def test_writes_gsm_file(self, sample_gse: GSERecord, tmp_output: Path):
        path = write_gsm_file(sample_gse, tmp_output)
        assert path.exists()
        assert sample_gse.gse_id in path.name


class TestWriteAll:
    def test_writes_all_files(self, sample_gse: GSERecord, tmp_output: Path):
        paths = write_all([sample_gse], tmp_output)
        assert "gse_summary" in paths
        assert sample_gse.gse_id in paths


class TestOpenGSESummaryWriter:
    def test_creates_file_with_header(self, tmp_output: Path):
        with open_gse_summary_writer(tmp_output) as _write_row:
            pass
        summary = tmp_output / "gse_summary.csv"
        assert summary.exists()
        with open(summary) as f:
            header = f.readline()
        assert "gse_id" in header

    def test_writes_rows_incrementally(self, sample_gse: GSERecord, tmp_output: Path):
        with open_gse_summary_writer(tmp_output) as write_row:
            write_row(sample_gse)
        summary = tmp_output / "gse_summary.csv"
        with open(summary) as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1
        assert rows[0]["gse_id"] == sample_gse.gse_id

    def test_writes_multiple_rows_in_order(self, sample_gse: GSERecord, tmp_output: Path):
        gse2 = sample_gse.model_copy(update={"gse_id": "GSE99999"})
        with open_gse_summary_writer(tmp_output) as write_row:
            write_row(sample_gse)
            write_row(gse2)
        summary = tmp_output / "gse_summary.csv"
        with open(summary) as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 2
        assert rows[0]["gse_id"] == sample_gse.gse_id
        assert rows[1]["gse_id"] == "GSE99999"

    def test_tsv_format(self, sample_gse: GSERecord, tmp_output: Path):
        with open_gse_summary_writer(tmp_output, fmt="tsv") as write_row:
            write_row(sample_gse)
        summary = tmp_output / "gse_summary.tsv"
        assert summary.exists()
        with open(summary) as f:
            rows = list(csv.DictReader(f, delimiter="\t"))
        assert rows[0]["gse_id"] == sample_gse.gse_id

    def test_harmonized_columns_present(self, sample_gse: GSERecord, tmp_output: Path):
        sample_gse.tissue_harmonized = "colon"
        with open_gse_summary_writer(tmp_output, harmonized=True) as write_row:
            write_row(sample_gse)
        summary = tmp_output / "gse_summary.csv"
        with open(summary) as f:
            rows = list(csv.DictReader(f))
        assert "tissue_harmonized" in rows[0]
        assert rows[0]["tissue_harmonized"] == "colon"


class TestProvenanceColumns:
    def test_provenance_present_when_harmonized(self, sample_gse: GSERecord, tmp_output: Path):
        harmonize_gse(sample_gse)
        for s in sample_gse.samples:
            harmonize_gsm(s)
        path = write_gse_summary([sample_gse], tmp_output, harmonized=True)
        with open(path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert "tissue_source" in rows[0]
        assert "tissue_confidence" in rows[0]
        assert "tissue_ontology_id" in rows[0]

    def test_provenance_absent_when_not_harmonized(
        self, sample_gse: GSERecord, tmp_output: Path,
    ):
        path = write_gse_summary([sample_gse], tmp_output, harmonized=False)
        with open(path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert "tissue_source" not in rows[0]
        assert "tissue_confidence" not in rows[0]

    def test_gsm_provenance_present(self, sample_gse: GSERecord, tmp_output: Path):
        for s in sample_gse.samples:
            harmonize_gsm(s)
        path = write_gsm_file(sample_gse, tmp_output, harmonized=True)
        with open(path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert "tissue_source" in rows[0]
        assert "disease_confidence" in rows[0]

    def test_gsm_provenance_absent(self, sample_gse: GSERecord, tmp_output: Path):
        path = write_gsm_file(sample_gse, tmp_output, harmonized=False)
        with open(path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert "tissue_source" not in rows[0]


class TestReviewQueue:
    def _make_low_confidence_gse(self, sample_gsm: GSMRecord) -> GSERecord:
        """Create a GSERecord with low-confidence fields for review queue testing."""
        gsm = sample_gsm.model_copy()
        harmonize_gsm(gsm)
        # Force a low-confidence field
        gsm.tissue_harmonized = "some tissue"
        gsm.tissue_source = "raw_fallback"
        gsm.tissue_confidence = 0.50
        gsm.tissue_ontology_id = None

        gse = GSERecord(
            gse_id="GSE99999",
            title="Test",
            organism=["Homo sapiens"],
            total_samples=1,
            samples=[gsm],
            tissue="unknown tissue",
        )
        harmonize_gse(gse)
        return gse

    def test_low_confidence_flagged(self, sample_gsm: GSMRecord, tmp_output: Path):
        gse = self._make_low_confidence_gse(sample_gsm)
        path = write_review_queue([gse], tmp_output)
        assert path is not None
        assert path.exists()
        with open(path) as f:
            rows = list(csv.DictReader(f))
        # Should have at least one low-confidence row
        assert len(rows) > 0
        field_names = [r["field_name"] for r in rows]
        assert "tissue" in field_names

    def test_high_confidence_skipped(self, sample_gse: GSERecord, tmp_output: Path):
        harmonize_gse(sample_gse)
        for s in sample_gse.samples:
            harmonize_gsm(s)
        # All fields are exact matches → confidence >= 0.70
        # Only treatment has 0.70 which is >= 0.65 threshold
        # So nothing should be flagged (all >= 0.65)
        path = write_review_queue([sample_gse], tmp_output, confidence_threshold=0.65)
        # All standard test data has confidence >= 0.70
        assert path is None

    def test_write_all_includes_review_queue(
        self, sample_gsm: GSMRecord, tmp_output: Path,
    ):
        gse = self._make_low_confidence_gse(sample_gsm)
        paths = write_all([gse], tmp_output, harmonized=True)
        assert "review_queue" in paths
        assert paths["review_queue"].exists()

    def test_write_all_no_review_queue_when_not_harmonized(
        self, sample_gse: GSERecord, tmp_output: Path,
    ):
        paths = write_all([sample_gse], tmp_output, harmonized=False)
        assert "review_queue" not in paths
