"""Tests for harmonization rules."""

from geotcha.harmonize.rules import (
    harmonize_gsm,
    normalize_age,
    normalize_disease,
    normalize_gender,
    normalize_timepoint,
    normalize_tissue,
)
from geotcha.models import GSMRecord


class TestNormalizeGender:
    def test_male(self):
        assert normalize_gender("male") == "male"
        assert normalize_gender("M") == "male"
        assert normalize_gender("Male") == "male"

    def test_female(self):
        assert normalize_gender("female") == "female"
        assert normalize_gender("F") == "female"

    def test_unknown(self):
        assert normalize_gender("NA") == "unknown"
        assert normalize_gender("n/a") == "unknown"

    def test_none(self):
        assert normalize_gender(None) is None
        assert normalize_gender("") is None


class TestNormalizeAge:
    def test_numeric(self):
        assert normalize_age("45") == "45"

    def test_with_years(self):
        assert normalize_age("45 years") == "45"

    def test_with_yo(self):
        assert normalize_age("45yo") == "45"

    def test_decimal(self):
        assert normalize_age("3.5 years") == "3.5"

    def test_none(self):
        assert normalize_age(None) is None


class TestNormalizeTissue:
    def test_known_tissue(self):
        assert normalize_tissue("colon") == "colon"
        assert normalize_tissue("blood") == "blood"
        assert normalize_tissue("PBMC") == "peripheral blood mononuclear cell"

    def test_unknown_tissue(self):
        assert normalize_tissue("some tissue") == "some tissue"

    def test_none(self):
        assert normalize_tissue(None) is None


class TestNormalizeDisease:
    def test_known_disease(self):
        assert normalize_disease("UC") == "ulcerative colitis"
        assert normalize_disease("IBD") == "inflammatory bowel disease"
        assert normalize_disease("crohn's disease") == "Crohn's disease"

    def test_healthy(self):
        assert normalize_disease("healthy") == "healthy"
        assert normalize_disease("control") == "healthy"
        assert normalize_disease("normal") == "healthy"

    def test_none(self):
        assert normalize_disease(None) is None


class TestNormalizeTimepoint:
    def test_week(self):
        assert normalize_timepoint("W8") == "W8"
        assert normalize_timepoint("Week 4") == "W4"

    def test_day(self):
        assert normalize_timepoint("D7") == "D7"
        assert normalize_timepoint("Day 14") == "D14"

    def test_baseline(self):
        assert normalize_timepoint("baseline") == "baseline"

    def test_none(self):
        assert normalize_timepoint(None) is None


class TestHarmonizeGSM:
    def test_harmonizes_all_fields(self, sample_gsm: GSMRecord):
        result = harmonize_gsm(sample_gsm)
        assert result.gender_harmonized == "male"
        assert result.age_harmonized == "45"
        assert result.tissue_harmonized == "colon"
        assert result.disease_harmonized == "ulcerative colitis"
