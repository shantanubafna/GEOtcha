"""Tests for harmonization rules."""

from geotcha.harmonize.rules import (
    NormResult,
    harmonize_gse,
    harmonize_gsm,
    normalize_age,
    normalize_disease,
    normalize_gender,
    normalize_timepoint,
    normalize_tissue,
    normalize_treatment,
)
from geotcha.models import GSERecord, GSMRecord


class TestNormalizeGender:
    def test_male(self):
        result = normalize_gender("male")
        assert result == NormResult("male", "rule", 1.0, None)

    def test_male_variants(self):
        assert normalize_gender("M").value == "male"
        assert normalize_gender("Male").value == "male"

    def test_female(self):
        assert normalize_gender("female").value == "female"
        assert normalize_gender("F").value == "female"

    def test_unknown(self):
        assert normalize_gender("NA").value == "unknown"
        assert normalize_gender("n/a").value == "unknown"

    def test_none(self):
        assert normalize_gender(None) is None
        assert normalize_gender("") is None

    def test_unrecognized_fallback(self):
        result = normalize_gender("intersex")
        assert result.value == "intersex"
        assert result.source == "raw_fallback"
        assert result.confidence == 0.50

    def test_confidence(self):
        result = normalize_gender("male")
        assert result.confidence == 1.0
        assert result.source == "rule"


class TestNormalizeAge:
    def test_numeric(self):
        result = normalize_age("45")
        assert result.value == "45"
        assert result.source == "rule"
        assert result.confidence == 1.0

    def test_with_years(self):
        assert normalize_age("45 years").value == "45"

    def test_with_yo(self):
        assert normalize_age("45yo").value == "45"

    def test_decimal(self):
        assert normalize_age("3.5 years").value == "3.5"

    def test_none(self):
        assert normalize_age(None) is None

    def test_unrecognized_fallback(self):
        result = normalize_age("unknown age")
        assert result.value == "unknown age"
        assert result.source == "raw_fallback"
        assert result.confidence == 0.50


class TestNormalizeTissue:
    def test_known_tissue(self):
        result = normalize_tissue("colon")
        assert result.value == "colon"
        assert result.confidence == 1.0
        assert result.ontology_id == "UBERON:0001155"

    def test_blood(self):
        result = normalize_tissue("blood")
        assert result.value == "blood"
        assert result.ontology_id == "UBERON:0000178"

    def test_pbmc(self):
        result = normalize_tissue("PBMC")
        assert result.value == "peripheral blood mononuclear cell"

    def test_unknown_tissue(self):
        result = normalize_tissue("some tissue")
        assert result.value == "some tissue"
        assert result.source == "raw_fallback"
        assert result.confidence == 0.50
        assert result.ontology_id is None

    def test_none(self):
        assert normalize_tissue(None) is None


class TestNormalizeDisease:
    def test_known_disease(self):
        result = normalize_disease("UC")
        assert result.value == "ulcerative colitis"
        assert result.confidence == 1.0
        assert result.ontology_id == "DOID:8577"

    def test_ibd(self):
        assert normalize_disease("IBD").value == "inflammatory bowel disease"

    def test_crohns(self):
        assert normalize_disease("crohn's disease").value == "Crohn's disease"

    def test_healthy(self):
        assert normalize_disease("healthy").value == "healthy"
        assert normalize_disease("control").value == "healthy"
        assert normalize_disease("normal").value == "healthy"

    def test_none(self):
        assert normalize_disease(None) is None

    def test_unknown_disease_fallback(self):
        result = normalize_disease("rare unknown disease xyz")
        assert result.source == "raw_fallback"
        assert result.confidence == 0.50


class TestNormalizeTimepoint:
    def test_week(self):
        assert normalize_timepoint("W8").value == "W8"
        assert normalize_timepoint("Week 4").value == "W4"

    def test_day(self):
        assert normalize_timepoint("D7").value == "D7"
        assert normalize_timepoint("Day 14").value == "D14"

    def test_baseline(self):
        result = normalize_timepoint("baseline")
        assert result.value == "baseline"
        assert result.source == "rule"
        assert result.confidence == 1.0

    def test_none(self):
        assert normalize_timepoint(None) is None

    def test_unrecognized_fallback(self):
        result = normalize_timepoint("some timepoint")
        assert result.source == "raw_fallback"
        assert result.confidence == 0.50


class TestNormalizeTreatment:
    def test_cleanup(self):
        result = normalize_treatment("  infliximab   5mg/kg  ")
        assert result.value == "infliximab 5mg/kg"
        assert result.source == "rule"
        assert result.confidence == 0.70

    def test_none(self):
        assert normalize_treatment(None) is None


class TestHarmonizeGSM:
    def test_harmonizes_all_fields(self, sample_gsm: GSMRecord):
        result = harmonize_gsm(sample_gsm)
        assert result.gender_harmonized == "male"
        assert result.age_harmonized == "45"
        assert result.tissue_harmonized == "colon"
        assert result.disease_harmonized == "ulcerative colitis"

    def test_provenance_populated(self, sample_gsm: GSMRecord):
        result = harmonize_gsm(sample_gsm)
        # Tissue provenance
        assert result.tissue_source == "rule"
        assert result.tissue_confidence == 1.0
        assert result.tissue_ontology_id == "UBERON:0001155"
        # Disease provenance
        assert result.disease_source == "rule"
        assert result.disease_confidence == 1.0
        assert result.disease_ontology_id == "DOID:8577"
        # Gender provenance
        assert result.gender_source == "rule"
        assert result.gender_confidence == 1.0
        # Age provenance
        assert result.age_source == "rule"
        assert result.age_confidence == 1.0
        # Treatment provenance
        assert result.treatment_source == "rule"
        assert result.treatment_confidence == 0.70

    def test_cell_type_passthrough(self, sample_gsm: GSMRecord):
        sample_gsm.cell_type = "T cell"
        result = harmonize_gsm(sample_gsm)
        assert result.cell_type_harmonized == "T cell"
        assert result.cell_type_source == "raw_fallback"
        assert result.cell_type_confidence == 0.50

    def test_none_fields_no_provenance(self):
        gsm = GSMRecord(gsm_id="GSM1", gse_id="GSE1")
        result = harmonize_gsm(gsm)
        assert result.tissue_harmonized is None
        assert result.tissue_source is None
        assert result.tissue_confidence is None


class TestHarmonizeGSE:
    def test_harmonizes_gse_fields(self, sample_gse: GSERecord):
        result = harmonize_gse(sample_gse)
        assert result.tissue_harmonized == "colon"
        assert result.tissue_source == "rule"
        assert result.tissue_confidence == 1.0
        assert result.tissue_ontology_id == "UBERON:0001155"
        assert result.disease_harmonized == "ulcerative colitis"
        assert result.disease_source == "rule"
        assert result.disease_confidence == 1.0
