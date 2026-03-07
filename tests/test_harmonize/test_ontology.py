"""Tests for ontology confidence tiers and synonym resolution."""

from geotcha.harmonize.ontology import (
    DISEASE_SYNONYMS,
    TISSUE_ONTOLOGY,
    TISSUE_SYNONYMS,
    _normalize_key,
    _token_set_match,
    _tokenize,
    lookup_cell_type_with_confidence,
    lookup_disease_with_confidence,
    lookup_tissue_with_confidence,
    lookup_treatment_with_confidence,
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

    def test_token_set_overlap_confidence_075(self):
        # Tokens {severe, ulcerative, colitis, case} overlap {ulcerative, colitis}
        result = lookup_disease_with_confidence("severe ulcerative colitis case")
        assert result is not None
        assert result[2] == 0.75

    def test_no_match_returns_none(self):
        result = lookup_disease_with_confidence("unknown rare disease xyz")
        assert result is None


# ── Helper function tests ────────────────────────────────────────────


class TestNormalizeKey:
    def test_strip_tissue_suffix(self):
        assert _normalize_key("colon tissue") == "colon"

    def test_strip_cells_suffix(self):
        assert _normalize_key("lung cells") == "lung"

    def test_strip_cancer_suffix(self):
        assert _normalize_key("breast cancer") == "breast"

    def test_strip_disease_suffix(self):
        assert _normalize_key("ulcerative colitis disease") == "ulcerative colitis"

    def test_no_suffix_unchanged(self):
        assert _normalize_key("colon") == "colon"

    def test_normalize_hyphens(self):
        assert _normalize_key("T-cell") == "t cell"

    def test_normalize_plus(self):
        # CD4+ → "cd4 " → stripped to "cd4"
        assert _normalize_key("CD4+") == "cd4"


class TestTokenize:
    def test_basic(self):
        tokens = _tokenize("activated macrophage")
        assert tokens == frozenset({"activated", "macrophage"})

    def test_skips_single_char(self):
        # Single-char tokens (like "a") should be excluded
        tokens = _tokenize("a large neuron")
        assert "a" not in tokens
        assert "large" in tokens
        assert "neuron" in tokens

    def test_case_insensitive(self):
        tokens = _tokenize("Ulcerative Colitis")
        assert tokens == frozenset({"ulcerative", "colitis"})


class TestTokenSetMatch:
    def test_subset_match(self):
        query = frozenset({"severe", "ulcerative", "colitis"})
        key = frozenset({"ulcerative", "colitis"})
        assert _token_set_match(query, key) is True

    def test_single_token_key_rejected(self):
        # Shorter set must have ≥2 tokens
        query = frozenset({"inflamed", "colon", "tissue"})
        key = frozenset({"colon"})
        assert _token_set_match(query, key) is False

    def test_no_overlap(self):
        query = frozenset({"foo", "bar"})
        key = frozenset({"baz", "qux"})
        assert _token_set_match(query, key) is False

    def test_empty_sets(self):
        assert _token_set_match(frozenset(), frozenset({"a", "b"})) is False
        assert _token_set_match(frozenset({"a", "b"}), frozenset()) is False


# ── Tier 3: Normalized exact match (0.80) ────────────────────────────


class TestNormalizedExactTier:
    def test_tissue_colon_tissue(self):
        # "colon tissue" → normalize → "colon" → exact match at 0.80
        result = lookup_tissue_with_confidence("colon tissue")
        assert result is not None
        assert result[0] == "colon"
        assert result[1] == "UBERON:0001155"
        assert result[2] == 0.80

    def test_tissue_lung_cells(self):
        # "lung cells" → normalize → "lung" → exact match at 0.80
        result = lookup_tissue_with_confidence("lung cells")
        assert result is not None
        assert result[0] == "lung"
        assert result[1] == "UBERON:0002048"
        assert result[2] == 0.80

    def test_disease_with_suffix(self):
        # "ulcerative colitis disease" → normalize → "ulcerative colitis"
        result = lookup_disease_with_confidence("ulcerative colitis disease")
        assert result is not None
        assert result[0] == "ulcerative colitis"
        assert result[1] == "DOID:8577"
        assert result[2] == 0.80

    def test_cell_type_macrophage_cells(self):
        # "macrophage cells" → normalize → "macrophage"
        result = lookup_cell_type_with_confidence("macrophage cells")
        assert result is not None
        assert result[0] == "macrophage"
        assert result[1] == "CL:0000235"
        assert result[2] == 0.80

    def test_hyphen_normalization_t_cell(self):
        # "T-cell" → synonym "t cell" → synonym match at 0.85 (tier 2, not tier 3)
        result = lookup_cell_type_with_confidence("T-cell")
        assert result is not None
        assert result[0] == "T cell"
        assert result[1] == "CL:0000084"


# ── Tier 4: Token-set overlap (0.75) ────────────────────────────────


class TestTokenSetTier:
    def test_disease_active_ra(self):
        # {active, rheumatoid, arthritis} ⊇ {rheumatoid, arthritis}
        result = lookup_disease_with_confidence("active rheumatoid arthritis")
        assert result is not None
        assert result[0] == "rheumatoid arthritis"
        assert result[1] == "DOID:7148"
        assert result[2] == 0.75

    def test_cell_type_activated_dendritic(self):
        # {activated, dendritic, cell} ⊇ {dendritic, cell}
        result = lookup_cell_type_with_confidence("activated dendritic cell")
        assert result is not None
        assert result[0] == "dendritic cell"
        assert result[1] == "CL:0000451"
        assert result[2] == 0.75


# ── Tier 5: Substring heuristic (0.70) ──────────────────────────────


class TestSubstringTier:
    def test_tissue_inflamed_colon(self):
        # "inflamed colon tissue" → substring "colon" found at tier 5
        result = lookup_tissue_with_confidence("inflamed colon tissue")
        assert result is not None
        assert result[2] == 0.70

    def test_treatment_low_dose(self):
        # "low dose methotrexate treatment" → substring "methotrexate"
        result = lookup_treatment_with_confidence("low dose methotrexate treatment")
        assert result is not None
        assert result[0] == "methotrexate"
        assert result[2] == 0.70


# ── Cross-ontology lookups ───────────────────────────────────────────


class TestCrossOntologyLookups:
    def test_treatment_exact(self):
        result = lookup_treatment_with_confidence("methotrexate")
        assert result is not None
        assert result[0] == "methotrexate"
        assert result[1] == "CHEBI:44185"
        assert result[2] == 1.0

    def test_treatment_synonym(self):
        result = lookup_treatment_with_confidence("Remicade")
        assert result is not None
        assert result[0] == "infliximab"
        assert result[1] == "CHEBI:64357"
        assert result[2] == 0.85

    def test_cell_type_exact(self):
        result = lookup_cell_type_with_confidence("B cell")
        assert result is not None
        assert result[0] == "B cell"
        assert result[1] == "CL:0000236"
        assert result[2] == 1.0

    def test_cell_type_no_match(self):
        result = lookup_cell_type_with_confidence("alien cells from mars")
        assert result is None

    def test_treatment_no_match(self):
        result = lookup_treatment_with_confidence("unobtainium")
        assert result is None
