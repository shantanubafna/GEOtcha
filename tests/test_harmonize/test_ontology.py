"""Tests for ontology confidence tiers and synonym resolution."""

from geotcha.harmonize.ontology import (
    DISEASE_SYNONYMS,
    TISSUE_ONTOLOGY,
    TISSUE_SYNONYMS,
    lookup_disease_with_confidence,
    lookup_tissue_with_confidence,
)


class TestTissueOntologyEntries:
    def test_transverse_colon(self):
        assert "transverse colon" in TISSUE_ONTOLOGY
        name, ont_id = TISSUE_ONTOLOGY["transverse colon"]
        assert name == "transverse colon"
        assert ont_id == "UBERON:0001157"

    def test_ascending_colon(self):
        assert "ascending colon" in TISSUE_ONTOLOGY
        assert TISSUE_ONTOLOGY["ascending colon"][1] == "UBERON:0001156"

    def test_descending_colon(self):
        assert "descending colon" in TISSUE_ONTOLOGY
        assert TISSUE_ONTOLOGY["descending colon"][1] == "UBERON:0001158"


class TestTissueSynonyms:
    def test_gut_synonym(self):
        assert TISSUE_SYNONYMS["gut"] == "intestine"

    def test_bowel_synonym(self):
        assert TISSUE_SYNONYMS["bowel"] == "intestine"

    def test_gi_tract_synonym(self):
        assert TISSUE_SYNONYMS["gi tract"] == "intestine"


class TestLookupTissueWithConfidence:
    def test_exact_match_confidence_1(self):
        result = lookup_tissue_with_confidence("colon")
        assert result is not None
        name, ont_id, confidence = result
        assert name == "colon"
        assert ont_id == "UBERON:0001155"
        assert confidence == 1.0

    def test_exact_match_case_insensitive(self):
        result = lookup_tissue_with_confidence("COLON")
        assert result is not None
        assert result[2] == 1.0

    def test_synonym_match_confidence_085(self):
        result = lookup_tissue_with_confidence("gut")
        assert result is not None
        name, ont_id, confidence = result
        assert name == "intestine"
        assert ont_id == "UBERON:0000160"
        assert confidence == 0.85

    def test_synonym_bowel(self):
        result = lookup_tissue_with_confidence("bowel")
        assert result is not None
        assert result[0] == "intestine"
        assert result[2] == 0.85

    def test_substring_heuristic_confidence_070(self):
        result = lookup_tissue_with_confidence("inflamed colon tissue")
        assert result is not None
        assert result[2] == 0.70

    def test_no_match_returns_none(self):
        result = lookup_tissue_with_confidence("unknown organ xyz")
        assert result is None

    def test_transverse_colon_exact(self):
        result = lookup_tissue_with_confidence("transverse colon")
        assert result is not None
        assert result[0] == "transverse colon"
        assert result[1] == "UBERON:0001157"
        assert result[2] == 1.0


class TestDiseaseSynonyms:
    def test_crohns_synonym(self):
        assert DISEASE_SYNONYMS["crohns"] == "crohn's disease"


class TestLookupDiseaseWithConfidence:
    def test_exact_match_confidence_1(self):
        result = lookup_disease_with_confidence("ulcerative colitis")
        assert result is not None
        name, ont_id, confidence = result
        assert name == "ulcerative colitis"
        assert ont_id == "DOID:8577"
        assert confidence == 1.0

    def test_synonym_match_confidence_085(self):
        result = lookup_disease_with_confidence("crohns")
        assert result is not None
        name, ont_id, confidence = result
        assert name == "Crohn's disease"
        assert ont_id == "DOID:8778"
        assert confidence == 0.85

    def test_substring_heuristic_confidence_070(self):
        result = lookup_disease_with_confidence("severe ulcerative colitis case")
        assert result is not None
        assert result[2] == 0.70

    def test_no_match_returns_none(self):
        result = lookup_disease_with_confidence("unknown rare disease xyz")
        assert result is None
