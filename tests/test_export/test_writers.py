"""Tests for export writers."""

import csv
from pathlib import Path

from geotcha.export.writers import write_all, write_gse_summary, write_gsm_file
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
