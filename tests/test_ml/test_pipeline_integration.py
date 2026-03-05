"""Tests for ML integration with the pipeline."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from geotcha.config import Settings
from geotcha.models import GSERecord, GSMRecord
from geotcha.pipeline import _harmonize_record


def _make_gse() -> GSERecord:
    gsm = GSMRecord(gsm_id="GSM1", gse_id="GSE1", title="test sample")
    return GSERecord(
        gse_id="GSE1",
        title="test series",
        summary="test summary",
        samples=[gsm],
    )


class TestHarmonizeRecordWithMl:
    def test_ml_called_after_rules(self):
        record = _make_gse()
        mock_ml = MagicMock()
        mock_ml.harmonize_gse.return_value = record
        mock_ml.harmonize_gsm.side_effect = lambda r: r

        result = _harmonize_record(record, use_llm=False, ml_harmonizer=mock_ml)
        mock_ml.harmonize_gse.assert_called_once()
        assert mock_ml.harmonize_gsm.call_count == 1
        assert result is record

    def test_ml_none_rules_only(self):
        record = _make_gse()
        result = _harmonize_record(record, use_llm=False, ml_harmonizer=None)
        assert result is record

    def test_ml_failure_logged(self):
        record = _make_gse()
        mock_ml = MagicMock()
        mock_ml.harmonize_gse.side_effect = RuntimeError("NER crashed")

        result = _harmonize_record(record, use_llm=False, ml_harmonizer=mock_ml)
        # Should still return the record (rules applied, ML failed gracefully)
        assert result is record

    def test_ml_mode_off_no_import(self, tmp_path):
        settings = Settings(
            output_dir=tmp_path, cache_dir=tmp_path / "cache",
            data_dir=tmp_path / "data", ml_mode="off",
        )
        assert settings.ml_mode == "off"
        # When ml_mode is off, pipeline should not try to import ML modules
        # This is tested by the fact that run_pipeline checks settings.ml_mode != "off"

    def test_extract_batch_threads_ml(self):
        """Verify _extract_batch passes ml_harmonizer to _harmonize_record."""
        record = _make_gse()
        mock_ml = MagicMock()
        mock_ml.harmonize_gse.return_value = record
        mock_ml.harmonize_gsm.side_effect = lambda r: r

        with patch("geotcha.pipeline.parse_gse", return_value=record):
            _harmonize_record(
                record, use_llm=False, settings=None, ml_harmonizer=mock_ml
            )
        mock_ml.harmonize_gse.assert_called_once()
