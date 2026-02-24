"""Tests for expanded scRNA detection in GSM parser."""

from geotcha.extract.gsm_parser import _is_single_cell_sample
from geotcha.models import GSMRecord


def _make_gsm(**kwargs) -> GSMRecord:
    """Helper to create a minimal GSMRecord for testing."""
    defaults = {
        "gsm_id": "GSM000001",
        "gse_id": "GSE000001",
        "title": "test sample",
        "source_name": "test",
        "organism": "Homo sapiens",
        "library_strategy": "RNA-Seq",
        "library_source": "transcriptomic",
    }
    defaults.update(kwargs)
    return GSMRecord(**defaults)


class TestExpandedSingleCellDetection:
    def test_library_source_single_cell(self):
        gsm = _make_gsm(library_source="transcriptomic single cell")
        assert _is_single_cell_sample(gsm) is True

    def test_library_source_bulk(self):
        gsm = _make_gsm(library_source="transcriptomic")
        assert _is_single_cell_sample(gsm) is False

    def test_library_strategy_single_cell(self):
        gsm = _make_gsm(library_strategy="single cell RNA-Seq")
        assert _is_single_cell_sample(gsm) is True

    def test_library_strategy_scrna(self):
        gsm = _make_gsm(library_strategy="scRNA-Seq")
        assert _is_single_cell_sample(gsm) is True

    def test_title_10x_chromium(self):
        gsm = _make_gsm(title="10x Chromium scRNA-seq of colon")
        assert _is_single_cell_sample(gsm) is True

    def test_title_drop_seq(self):
        gsm = _make_gsm(title="Drop-seq analysis of gut")
        assert _is_single_cell_sample(gsm) is True

    def test_description_single_cell(self):
        gsm = _make_gsm(description="single-cell RNA sequencing of PBMCs")
        assert _is_single_cell_sample(gsm) is True

    def test_characteristics_scrna(self):
        gsm = _make_gsm(characteristics={"method": "10x Genomics scRNA-seq"})
        assert _is_single_cell_sample(gsm) is True

    def test_bulk_rnaseq_not_flagged(self):
        gsm = _make_gsm(
            title="Bulk RNA-seq of colon biopsy",
            description="RNA-seq from tissue",
        )
        assert _is_single_cell_sample(gsm) is False

    def test_smart_seq2(self):
        gsm = _make_gsm(title="Smart-seq2 single-cell analysis")
        assert _is_single_cell_sample(gsm) is True

    def test_single_nucleus(self):
        gsm = _make_gsm(description="single-nucleus RNA-seq")
        assert _is_single_cell_sample(gsm) is True
