"""Tests for treatment normalization improvements."""

from __future__ import annotations

from geotcha.harmonize.rules import normalize_treatment


class TestNormalizeTreatmentDrugName:
    def test_infliximab_exact(self):
        result = normalize_treatment("infliximab")
        assert result.value == "infliximab"
        assert result.confidence == 1.0
        assert result.source == "rule"

    def test_methotrexate_exact(self):
        result = normalize_treatment("methotrexate")
        assert result.value == "methotrexate"
        assert result.confidence == 1.0

    def test_dexamethasone_exact(self):
        result = normalize_treatment("dexamethasone")
        assert result.value == "dexamethasone"
        assert result.confidence == 1.0

    def test_lps_exact(self):
        result = normalize_treatment("LPS")
        assert result.value == "lipopolysaccharide"
        assert result.confidence == 1.0


class TestNormalizeTreatmentSynonym:
    def test_remicade_to_infliximab(self):
        result = normalize_treatment("remicade")
        assert result.value == "infliximab"
        assert result.confidence == 0.85

    def test_humira_to_adalimumab(self):
        result = normalize_treatment("humira")
        assert result.value == "adalimumab"
        assert result.confidence == 0.85

    def test_mtx_to_methotrexate(self):
        result = normalize_treatment("MTX")
        assert result.value == "methotrexate"
        assert result.confidence == 0.85


class TestNormalizeTreatmentDoseStrings:
    def test_infliximab_with_dose(self):
        result = normalize_treatment("infliximab 5mg/kg")
        assert result is not None
        # Substring match on "infliximab"
        assert result.confidence == 0.70
        assert result.value == "infliximab"

    def test_dexamethasone_with_dose(self):
        result = normalize_treatment("dexamethasone 10mg")
        assert result.confidence == 0.70
        assert result.value == "dexamethasone"

    def test_prednisone_with_dose(self):
        result = normalize_treatment("prednisone 40mg daily")
        assert result.confidence == 0.70
        assert result.value == "prednisone"


class TestNormalizeTreatmentFallback:
    def test_unrecognized(self):
        result = normalize_treatment("experimental compound XYZ-123")
        assert result.source == "raw_fallback"
        assert result.confidence == 0.50
        assert result.value == "experimental compound XYZ-123"


class TestNormalizeTreatmentEdgeCases:
    def test_none(self):
        assert normalize_treatment(None) is None

    def test_whitespace_cleanup(self):
        result = normalize_treatment("  some   unknown   drug  ")
        assert result.value == "some unknown drug"
        assert result.source == "raw_fallback"
        assert result.confidence == 0.50
