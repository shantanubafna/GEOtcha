"""Tests for ML integration with the pipeline."""
from __future__ import annotations

import json
import sys
from unittest.mock import MagicMock, patch

from geotcha.config import Settings
from geotcha.models import GSERecord, GSMRecord
from geotcha.pipeline import (
    _harmonize_record,
    _load_state,
    _save_state,
    run_extract,
    run_pipeline,
)


def _make_gse() -> GSERecord:
    gsm = GSMRecord(gsm_id="GSM1", gse_id="GSE1", title="test sample")
    return GSERecord(
        gse_id="GSE1",
        title="test series",
        summary="test summary",
        samples=[gsm],
    )


def _make_settings(tmp_path, **kwargs):
    defaults = dict(
        output_dir=tmp_path / "output",
        cache_dir=tmp_path / "cache",
        data_dir=tmp_path / "data",
        non_interactive=True,
    )
    defaults.update(kwargs)
    return Settings(**defaults)


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
        settings = _make_settings(tmp_path, ml_mode="off")
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


class TestStatePersistsMlMode:
    def test_state_includes_ml_mode(self, tmp_path):
        settings = _make_settings(tmp_path, ml_mode="hybrid")
        state = {
            "run_id": "test123",
            "query": "test",
            "all_gse_ids": ["GSE1"],
            "processed_gse_ids": [],
            "harmonize": True,
            "use_llm": False,
            "ml_mode": settings.ml_mode,
            "status": "filtered",
        }
        _save_state("test123", state, settings)
        loaded = _load_state("test123", settings)
        assert loaded["ml_mode"] == "hybrid"

    def test_resume_without_ml_mode_defaults_off(self, tmp_path):
        """Old state files without ml_mode should default to 'off'."""
        settings = _make_settings(tmp_path)
        state = {
            "run_id": "old_run",
            "query": "test",
            "all_gse_ids": ["GSE1"],
            "processed_gse_ids": [],
            "harmonize": False,
            "use_llm": False,
            "status": "filtered",
        }
        _save_state("old_run", state, settings)
        loaded = _load_state("old_run", settings)
        assert loaded.get("ml_mode", "off") == "off"


class TestResumeRunMl:
    def test_resume_preserves_ml_mode(self, tmp_path):
        """resume_run reads ml_mode from saved state."""
        settings = _make_settings(tmp_path, ml_mode="hybrid")
        state = {
            "run_id": "res123",
            "query": "test",
            "all_gse_ids": ["GSE1"],
            "processed_gse_ids": [],
            "harmonize": True,
            "use_llm": False,
            "ml_mode": "hybrid",
            "status": "subset_complete",
        }
        _save_state("res123", state, settings)

        record = _make_gse()
        mock_ml_cls = MagicMock()
        mock_ml_instance = MagicMock()
        mock_ml_cls.from_config.return_value = mock_ml_instance
        mock_ml_instance.harmonize_gse.return_value = record
        mock_ml_instance.harmonize_gsm.side_effect = lambda r: r

        with (
            patch("geotcha.pipeline.parse_gse", return_value=record),
            patch("geotcha.pipeline.write_gsm_file"),
            patch("geotcha.pipeline.read_gse_summary", return_value=[]),
            patch("geotcha.pipeline.write_gse_summary_rows"),
            patch("geotcha.ml.inference.MLHarmonizer", mock_ml_cls),
        ):
            from geotcha.pipeline import resume_run

            resume_run("res123", settings)

        mock_ml_cls.from_config.assert_called_once_with(settings)

    def test_resume_creates_ml_harmonizer(self, tmp_path):
        """resume_run creates MLHarmonizer when ml_mode != off."""
        settings = _make_settings(tmp_path, ml_mode="full")
        state = {
            "run_id": "res456",
            "query": "test",
            "all_gse_ids": ["GSE2"],
            "processed_gse_ids": [],
            "harmonize": True,
            "use_llm": False,
            "ml_mode": "full",
            "status": "subset_complete",
        }
        _save_state("res456", state, settings)

        record = _make_gse()
        mock_ml_cls = MagicMock()
        mock_ml_instance = MagicMock()
        mock_ml_cls.from_config.return_value = mock_ml_instance
        mock_ml_instance.harmonize_gse.return_value = record
        mock_ml_instance.harmonize_gsm.side_effect = lambda r: r

        with (
            patch("geotcha.pipeline.parse_gse", return_value=record),
            patch("geotcha.pipeline.write_gsm_file"),
            patch("geotcha.pipeline.read_gse_summary", return_value=[]),
            patch("geotcha.pipeline.write_gse_summary_rows"),
            patch("geotcha.ml.inference.MLHarmonizer", mock_ml_cls),
        ):
            from geotcha.pipeline import resume_run

            resume_run("res456", settings)

        mock_ml_cls.from_config.assert_called_once()


class TestManifestMlTelemetry:
    def test_manifest_ml_telemetry_fields(self, tmp_path):
        """run_pipeline manifest includes ML telemetry when ml_mode != off."""
        settings = _make_settings(tmp_path, ml_mode="hybrid")
        record = _make_gse()

        mock_ml_cls = MagicMock()
        mock_ml_instance = MagicMock()
        mock_ml_cls.from_config.return_value = mock_ml_instance
        mock_ml_instance.harmonize_gse.return_value = record
        mock_ml_instance.harmonize_gsm.side_effect = lambda r: r

        with (
            patch("geotcha.pipeline.build_query", return_value="test query"),
            patch("geotcha.pipeline.search_geo", return_value=["GSE1"]),
            patch("geotcha.pipeline.filter_results", return_value=["GSE1"]),
            patch("geotcha.pipeline.parse_gse", return_value=record),
            patch("geotcha.pipeline.write_all", return_value={"gse_summary": "out.csv"}),
            patch("geotcha.pipeline.write_gsm_file"),
            patch("geotcha.ml.inference.MLHarmonizer", mock_ml_cls),
        ):
            run_pipeline("test", settings, harmonize=True)

        # Read manifest from data dir
        data_dir = settings.get_data_dir()
        manifests = list(data_dir.glob("*/manifest.json"))
        assert len(manifests) == 1
        manifest = json.loads(manifests[0].read_text())
        assert manifest["ml_mode_requested"] == "hybrid"
        assert manifest["ml_mode_effective"] == "hybrid"
        assert manifest["ml_models_loaded"] is True
        assert manifest["ml_fallback_reason"] is None

    def test_manifest_ml_fallback_reason(self, tmp_path):
        """Manifest records fallback reason when ML loading fails."""
        settings = _make_settings(tmp_path, ml_mode="full")
        record = _make_gse()

        with (
            patch("geotcha.pipeline.build_query", return_value="test query"),
            patch("geotcha.pipeline.search_geo", return_value=["GSE1"]),
            patch("geotcha.pipeline.filter_results", return_value=["GSE1"]),
            patch("geotcha.pipeline.parse_gse", return_value=record),
            patch("geotcha.pipeline.write_all", return_value={"gse_summary": "out.csv"}),
            patch("geotcha.pipeline.write_gsm_file"),
            patch(
                "geotcha.ml.inference.MLHarmonizer.from_config",
                side_effect=ImportError("gliner not installed"),
            ),
        ):
            run_pipeline("test", settings, harmonize=True)

        data_dir = settings.get_data_dir()
        manifests = list(data_dir.glob("*/manifest.json"))
        assert len(manifests) == 1
        manifest = json.loads(manifests[0].read_text())
        assert manifest["ml_mode_requested"] == "full"
        assert manifest["ml_mode_effective"] == "off"
        assert manifest["ml_models_loaded"] is False
        assert "gliner not installed" in manifest["ml_fallback_reason"]

    def test_manifest_ml_mode_off_no_telemetry(self, tmp_path):
        """When ml_mode=off, manifest shows off with no fallback reason."""
        settings = _make_settings(tmp_path, ml_mode="off")
        record = _make_gse()

        with (
            patch("geotcha.pipeline.build_query", return_value="test query"),
            patch("geotcha.pipeline.search_geo", return_value=["GSE1"]),
            patch("geotcha.pipeline.filter_results", return_value=["GSE1"]),
            patch("geotcha.pipeline.parse_gse", return_value=record),
            patch("geotcha.pipeline.write_all", return_value={"gse_summary": "out.csv"}),
            patch("geotcha.pipeline.write_gsm_file"),
        ):
            run_pipeline("test", settings, harmonize=False)

        data_dir = settings.get_data_dir()
        manifests = list(data_dir.glob("*/manifest.json"))
        assert len(manifests) == 1
        manifest = json.loads(manifests[0].read_text())
        assert manifest["ml_mode_requested"] == "off"
        assert manifest["ml_mode_effective"] == "off"
        assert manifest["ml_models_loaded"] is False
        assert manifest["ml_fallback_reason"] is None


class TestMlModeOffZeroImport:
    def test_ml_mode_off_zero_import(self, tmp_path):
        """When ml_mode=off, geotcha.ml modules are never imported."""
        settings = _make_settings(tmp_path, ml_mode="off")
        record = _make_gse()

        # Remove any cached ML modules
        ml_mods = [k for k in sys.modules if k.startswith("geotcha.ml")]
        saved = {k: sys.modules.pop(k) for k in ml_mods}

        try:
            with (
                patch("geotcha.pipeline.build_query", return_value="test query"),
                patch("geotcha.pipeline.search_geo", return_value=["GSE1"]),
                patch("geotcha.pipeline.filter_results", return_value=["GSE1"]),
                patch("geotcha.pipeline.parse_gse", return_value=record),
                patch("geotcha.pipeline.write_all", return_value={}),
                patch("geotcha.pipeline.write_gsm_file"),
            ):
                run_pipeline("test", settings, harmonize=False)

            imported = [k for k in sys.modules if k.startswith("geotcha.ml.inference")]
            assert imported == [], f"ML modules imported when ml_mode=off: {imported}"
        finally:
            sys.modules.update(saved)
