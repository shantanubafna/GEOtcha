"""Tests for export writers."""

import csv
from pathlib import Path

from geotcha.export.writers import (
    open_gse_summary_writer,
    write_all,
    write_gse_summary,
    write_gsm_file,
)
from geotcha.models import GSERecord


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
