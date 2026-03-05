"""Tests for cell type normalization."""

from __future__ import annotations

from geotcha.harmonize.ontology import lookup_cell_type_with_confidence
from geotcha.harmonize.rules import normalize_cell_type


class TestNormalizeCellTypeExact:
    def test_t_cell(self):
        result = normalize_cell_type("T cell")
        assert result.value == "T cell"
        assert result.confidence == 1.0
        assert result.ontology_id == "CL:0000084"
        assert result.source == "rule"

    def test_macrophage(self):
        result = normalize_cell_type("macrophage")
        assert result.value == "macrophage"
        assert result.confidence == 1.0
        assert result.ontology_id == "CL:0000235"

    def test_epithelial_cell(self):
        result = normalize_cell_type("epithelial cell")
        assert result.value == "epithelial cell"
        assert result.ontology_id == "CL:0000066"

    def test_fibroblast(self):
        result = normalize_cell_type("fibroblast")
        assert result.value == "fibroblast"
        assert result.ontology_id == "CL:0000057"

    def test_neuron(self):
        result = normalize_cell_type("neuron")
        assert result.value == "neuron"
        assert result.ontology_id == "CL:0000540"


class TestNormalizeCellTypeSynonym:
    def test_nk_synonym(self):
        result = normalize_cell_type("NK")
        assert result.value == "natural killer cell"
        assert result.confidence == 0.85
        assert result.ontology_id == "CL:0000623"

    def test_treg_exact(self):
        # "treg" is in the ontology directly
        result = normalize_cell_type("Treg")
        assert result.value == "regulatory T cell"
        assert result.confidence == 1.0
        assert result.ontology_id == "CL:0000815"

    def test_tregs_synonym(self):
        # "tregs" → synonym → "regulatory t cell"
        result = normalize_cell_type("Tregs")
        assert result.value == "regulatory T cell"
        assert result.confidence == 0.85

    def test_dc_synonym(self):
        result = normalize_cell_type("DC")
        assert result.value == "dendritic cell"
        assert result.confidence == 0.85

    def test_epithelial_synonym(self):
        result = normalize_cell_type("epithelial")
        assert result.value == "epithelial cell"
        assert result.confidence == 0.85


class TestNormalizeCellTypeSubstring:
    def test_activated_macrophage(self):
        result = normalize_cell_type("activated macrophage")
        assert result is not None
        assert result.confidence == 0.70
        assert result.ontology_id == "CL:0000235"

    def test_cd4_positive_t_cell_variant(self):
        result = normalize_cell_type("sorted fibroblast population")
        assert result is not None
        assert result.confidence == 0.70


class TestNormalizeCellTypeFallback:
    def test_unknown_cell(self):
        result = normalize_cell_type("rare progenitor xyz")
        assert result.value == "rare progenitor xyz"
        assert result.source == "raw_fallback"
        assert result.confidence == 0.50
        assert result.ontology_id is None

    def test_obscure_cell_type(self):
        result = normalize_cell_type("type II pneumocyte")
        assert result.source == "raw_fallback"
        assert result.confidence == 0.50


class TestNormalizeCellTypeEdgeCases:
    def test_none(self):
        assert normalize_cell_type(None) is None

    def test_empty(self):
        assert normalize_cell_type("") is None


class TestLookupCellTypeWithConfidence:
    def test_exact(self):
        result = lookup_cell_type_with_confidence("B cell")
        assert result is not None
        assert result[0] == "B cell"
        assert result[1] == "CL:0000236"
        assert result[2] == 1.0

    def test_synonym(self):
        result = lookup_cell_type_with_confidence("monocytes")
        assert result is not None
        assert result[0] == "monocyte"
        assert result[2] == 0.85

    def test_no_match(self):
        result = lookup_cell_type_with_confidence("alien cells from mars")
        assert result is None
