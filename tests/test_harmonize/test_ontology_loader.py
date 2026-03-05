"""Tests for JSON ontology loading and schema validation."""

from __future__ import annotations

import json
from importlib import resources

import pytest

from geotcha.harmonize.ontology import (
    CELL_TYPE_ONTOLOGY,
    CELL_TYPE_SYNONYMS,
    DISEASE_ONTOLOGY,
    DISEASE_SYNONYMS,
    TISSUE_ONTOLOGY,
    TISSUE_SYNONYMS,
    TREATMENT_ONTOLOGY,
    TREATMENT_SYNONYMS,
)


class TestJsonFileExistence:
    def test_tissue_json_exists(self):
        data = resources.files("geotcha.data") / "ontology" / "tissue.json"
        assert data.is_file()

    def test_disease_json_exists(self):
        data = resources.files("geotcha.data") / "ontology" / "disease.json"
        assert data.is_file()

    def test_cell_type_json_exists(self):
        data = resources.files("geotcha.data") / "ontology" / "cell_type.json"
        assert data.is_file()

    def test_treatment_json_exists(self):
        data = resources.files("geotcha.data") / "ontology" / "treatment.json"
        assert data.is_file()

    def test_synonyms_json_exists(self):
        data = resources.files("geotcha.data") / "ontology" / "synonyms.json"
        assert data.is_file()


class TestJsonSchemaValidation:
    @pytest.mark.parametrize(
        "filename",
        ["tissue.json", "disease.json", "cell_type.json", "treatment.json"],
    )
    def test_ontology_schema_valid(self, filename):
        """Each entry must be [standardized_name, ontology_id_or_empty]."""
        data = resources.files("geotcha.data") / "ontology" / filename
        raw = json.loads(data.read_text(encoding="utf-8"))
        assert isinstance(raw, dict)
        for key, val in raw.items():
            assert isinstance(key, str), f"Key {key!r} is not a string"
            assert isinstance(val, list), f"Value for {key!r} is not a list"
            assert len(val) == 2, f"Value for {key!r} has {len(val)} elements, expected 2"
            assert isinstance(val[0], str), f"First element for {key!r} is not a string"
            assert isinstance(val[1], str), f"Second element for {key!r} is not a string"

    def test_synonyms_schema_valid(self):
        data = resources.files("geotcha.data") / "ontology" / "synonyms.json"
        raw = json.loads(data.read_text(encoding="utf-8"))
        assert isinstance(raw, dict)
        for category in ("tissue", "disease", "cell_type", "treatment"):
            assert category in raw, f"Missing category: {category}"
            assert isinstance(raw[category], dict)
            for key, val in raw[category].items():
                assert isinstance(key, str)
                assert isinstance(val, str)


class TestRoundTripFidelity:
    def test_tissue_count_matches(self):
        assert len(TISSUE_ONTOLOGY) == 43

    def test_disease_count_matches(self):
        assert len(DISEASE_ONTOLOGY) == 34

    def test_tissue_colon_entry(self):
        name, ont_id = TISSUE_ONTOLOGY["colon"]
        assert name == "colon"
        assert ont_id == "UBERON:0001155"

    def test_disease_uc_entry(self):
        name, ont_id = DISEASE_ONTOLOGY["uc"]
        assert name == "ulcerative colitis"
        assert ont_id == "DOID:8577"

    def test_cell_type_loads(self):
        assert len(CELL_TYPE_ONTOLOGY) >= 40
        assert "t cell" in CELL_TYPE_ONTOLOGY
        name, ont_id = CELL_TYPE_ONTOLOGY["t cell"]
        assert name == "T cell"
        assert ont_id == "CL:0000084"

    def test_treatment_loads(self):
        assert len(TREATMENT_ONTOLOGY) >= 60
        assert "infliximab" in TREATMENT_ONTOLOGY

    def test_tissue_synonyms(self):
        assert TISSUE_SYNONYMS["gut"] == "intestine"

    def test_disease_synonyms(self):
        assert DISEASE_SYNONYMS["crohns"] == "crohn's disease"

    def test_cell_type_synonyms(self):
        assert CELL_TYPE_SYNONYMS["nk"] == "natural killer cell"
        assert CELL_TYPE_SYNONYMS["treg"] == "regulatory t cell"

    def test_treatment_synonyms(self):
        assert TREATMENT_SYNONYMS["remicade"] == "infliximab"
        assert TREATMENT_SYNONYMS["humira"] == "adalimumab"
