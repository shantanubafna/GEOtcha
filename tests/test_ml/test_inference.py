"""Tests for ML inference / MLHarmonizer."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from geotcha.ml.inference import MLHarmonizer
from geotcha.models import GSERecord, GSMRecord


@pytest.fixture
def bare_gsm():
    """GSM record with no harmonization applied."""
    return GSMRecord(
        gsm_id="GSM999",
        gse_id="GSE111",
        title="RNA-seq of colon biopsy, UC patient",
        source_name="colon biopsy",
        description="Colon biopsy from ulcerative colitis patient",
        characteristics={"tissue": "colon", "disease": "ulcerative colitis"},
    )


@pytest.fixture
def bare_gse():
    """GSE record with no harmonization applied."""
    return GSERecord(
        gse_id="GSE111",
        title="Transcriptomic analysis of UC",
        summary="RNA-seq of colon biopsies from UC patients",
        overall_design="Colon biopsies at baseline",
    )


class TestMLHarmonizerInit:
    def test_defaults(self):
        h = MLHarmonizer()
        assert h.threshold == 0.65
        assert h.device == "auto"
        assert h.review_threshold == 0.50
        assert h._ner is None
        assert h._linker is None

    def test_review_threshold_wired(self):
        h = MLHarmonizer(review_threshold=0.40)
        assert h.review_threshold == 0.40


class TestNeedsMl:
    def test_missing_field(self, bare_gsm):
        h = MLHarmonizer()
        assert h._needs_ml(bare_gsm, "disease") is True

    def test_low_confidence(self, bare_gsm):
        bare_gsm.disease_harmonized = "UC"
        bare_gsm.disease_confidence = 0.40
        h = MLHarmonizer(threshold=0.65)
        assert h._needs_ml(bare_gsm, "disease") is True

    def test_high_confidence(self, bare_gsm):
        bare_gsm.disease_harmonized = "ulcerative colitis"
        bare_gsm.disease_confidence = 0.90
        h = MLHarmonizer(threshold=0.65)
        assert h._needs_ml(bare_gsm, "disease") is False


class TestHarmonizeGsm:
    def test_no_ner_model(self, bare_gsm):
        h = MLHarmonizer(ner_model=None)
        result = h.harmonize_gsm(bare_gsm)
        assert result.disease_harmonized is None

    def test_with_entities(self, bare_gsm):
        mock_ner = MagicMock()
        mock_ner.predict_entities.return_value = [
            {"label": "disease", "text": "ulcerative colitis", "score": 0.92},
        ]
        h = MLHarmonizer(ner_model=mock_ner, threshold=0.65)
        result = h.harmonize_gsm(bare_gsm)
        assert result.disease_harmonized == "ulcerative colitis"
        assert result.disease_source == "ml"
        assert result.disease_confidence == 0.92

    def test_score_below_review_flags_review(self, bare_gsm):
        """Score below review_threshold → needs_review = True."""
        mock_ner = MagicMock()
        mock_ner.predict_entities.return_value = [
            {"label": "disease", "text": "UC", "score": 0.30},
        ]
        h = MLHarmonizer(ner_model=mock_ner, threshold=0.65, review_threshold=0.50)
        result = h.harmonize_gsm(bare_gsm)
        assert result.needs_review is True
        assert result.disease_harmonized is None

    def test_score_between_thresholds_no_flag(self, bare_gsm):
        """Score between review_threshold and threshold → no review flag, no apply."""
        mock_ner = MagicMock()
        mock_ner.predict_entities.return_value = [
            {"label": "disease", "text": "UC", "score": 0.55},
        ]
        h = MLHarmonizer(ner_model=mock_ner, threshold=0.65, review_threshold=0.50)
        result = h.harmonize_gsm(bare_gsm)
        assert result.needs_review is False
        assert result.disease_harmonized is None

    def test_skips_high_confidence_fields(self, bare_gsm):
        bare_gsm.disease_harmonized = "ulcerative colitis"
        bare_gsm.disease_confidence = 0.95
        bare_gsm.disease_source = "rule"
        mock_ner = MagicMock()
        mock_ner.predict_entities.return_value = [
            {"label": "disease", "text": "Crohn's disease", "score": 0.99},
        ]
        h = MLHarmonizer(ner_model=mock_ner, threshold=0.65)
        result = h.harmonize_gsm(bare_gsm)
        # Disease should NOT be overwritten
        assert result.disease_harmonized == "ulcerative colitis"
        assert result.disease_source == "rule"


class TestHarmonizeGse:
    def test_with_entities(self, bare_gse):
        mock_ner = MagicMock()
        mock_ner.predict_entities.return_value = [
            {"label": "disease", "text": "ulcerative colitis", "score": 0.88},
            {"label": "tissue", "text": "colon", "score": 0.91},
        ]
        h = MLHarmonizer(ner_model=mock_ner, threshold=0.65)
        result = h.harmonize_gse(bare_gse)
        assert result.disease_harmonized == "ulcerative colitis"
        assert result.disease_source == "ml"
        assert result.tissue_harmonized == "colon"
        assert result.tissue_source == "ml"


class TestBuildText:
    def test_gsm_text(self, bare_gsm):
        h = MLHarmonizer()
        text = h._build_text(bare_gsm)
        assert "colon biopsy" in text
        assert "ulcerative colitis" in text

    def test_gse_text(self, bare_gse):
        h = MLHarmonizer()
        text = h._build_gse_text(bare_gse)
        assert "Transcriptomic" in text
        assert "RNA-seq" in text


class TestFromConfig:
    def test_from_config(self):
        mock_settings = MagicMock()
        mock_settings.ml_device = "cpu"
        mock_settings.ml_threshold = 0.70
        mock_settings.ml_review_threshold = 0.45

        mock_ner = MagicMock()
        mock_linker = MagicMock()

        with (
            patch("geotcha.ml.loader._resolve_device", return_value="cpu"),
            patch("geotcha.ml.loader.load_ner_model", return_value=mock_ner),
            patch("geotcha.ml.loader.load_linker", return_value=mock_linker),
        ):
            h = MLHarmonizer.from_config(mock_settings)
        assert h.threshold == 0.70
        assert h.device == "cpu"
        assert h.review_threshold == 0.45
        assert h._ner is mock_ner
        assert h._linker is mock_linker

    def test_review_threshold_from_config(self):
        mock_settings = MagicMock()
        mock_settings.ml_device = "cpu"
        mock_settings.ml_threshold = 0.65
        mock_settings.ml_review_threshold = 0.30

        with (
            patch("geotcha.ml.loader._resolve_device", return_value="cpu"),
            patch("geotcha.ml.loader.load_ner_model", return_value=None),
            patch("geotcha.ml.loader.load_linker", return_value=None),
        ):
            h = MLHarmonizer.from_config(mock_settings)
        assert h.review_threshold == 0.30
