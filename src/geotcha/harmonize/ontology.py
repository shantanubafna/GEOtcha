"""Curated lookup tables for ontology mapping (UBERON, DOID, CL)."""

from __future__ import annotations

import json
from importlib import resources


def _load_ontology(filename: str) -> dict[str, tuple[str, str]]:
    """Load an ontology JSON file from package data."""
    data_files = resources.files("geotcha.data") / "ontology" / filename
    raw = json.loads(data_files.read_text(encoding="utf-8"))
    return {k: (v[0], v[1]) for k, v in raw.items()}


def _load_synonyms(category: str) -> dict[str, str]:
    """Load synonym map for a given category from synonyms.json."""
    data_files = resources.files("geotcha.data") / "ontology" / "synonyms.json"
    raw = json.loads(data_files.read_text(encoding="utf-8"))
    return raw.get(category, {})


# UBERON tissue mappings
TISSUE_ONTOLOGY: dict[str, tuple[str, str]] = _load_ontology("tissue.json")
TISSUE_SYNONYMS: dict[str, str] = _load_synonyms("tissue")

# Disease ontology mappings
DISEASE_ONTOLOGY: dict[str, tuple[str, str]] = _load_ontology("disease.json")
DISEASE_SYNONYMS: dict[str, str] = _load_synonyms("disease")

# Cell Ontology mappings
CELL_TYPE_ONTOLOGY: dict[str, tuple[str, str]] = _load_ontology("cell_type.json")
CELL_TYPE_SYNONYMS: dict[str, str] = _load_synonyms("cell_type")

# Treatment mappings
TREATMENT_ONTOLOGY: dict[str, tuple[str, str]] = _load_ontology("treatment.json")
TREATMENT_SYNONYMS: dict[str, str] = _load_synonyms("treatment")


def lookup_tissue(raw: str) -> tuple[str, str] | None:
    """Look up standardized tissue name and UBERON ID."""
    return TISSUE_ONTOLOGY.get(raw.lower().strip())


def lookup_disease(raw: str) -> tuple[str, str] | None:
    """Look up standardized disease name and ontology ID."""
    return DISEASE_ONTOLOGY.get(raw.lower().strip())


def _substring_match(ontology_key: str, text: str) -> bool:
    """Check if an ontology key appears as a meaningful substring in text.

    Short keys (<=3 chars) are skipped to avoid false positives
    (e.g., "ra" matching "rare", "uc" matching "sauce").
    """
    if len(ontology_key) <= 3:
        return False
    return ontology_key in text


def _lookup_with_confidence(
    raw: str,
    ontology: dict[str, tuple[str, str]],
    synonyms: dict[str, str],
) -> tuple[str, str, float] | None:
    """Generic 3-tier lookup: exact -> synonym -> substring.

    Returns (standardized_name, ontology_id, confidence) or None.
    """
    key = raw.lower().strip()
    # Tier 1: exact match
    result = ontology.get(key)
    if result:
        return (result[0], result[1], 1.0)
    # Tier 2: synonym match
    canonical = synonyms.get(key)
    if canonical:
        result = ontology.get(canonical)
        if result:
            return (result[0], result[1], 0.85)
    # Tier 3: substring heuristic
    for ontology_key, (name, ont_id) in ontology.items():
        if _substring_match(ontology_key, key):
            return (name, ont_id, 0.70)
    return None


def lookup_tissue_with_confidence(raw: str) -> tuple[str, str, float] | None:
    """Look up tissue with confidence tier.

    Returns (standardized_name, ontology_id, confidence) or None.
    Tiers: exact=1.0, synonym=0.85, substring heuristic=0.70.
    """
    return _lookup_with_confidence(raw, TISSUE_ONTOLOGY, TISSUE_SYNONYMS)


def lookup_disease_with_confidence(raw: str) -> tuple[str, str, float] | None:
    """Look up disease with confidence tier.

    Returns (standardized_name, ontology_id, confidence) or None.
    Tiers: exact=1.0, synonym=0.85, substring heuristic=0.70.
    """
    return _lookup_with_confidence(raw, DISEASE_ONTOLOGY, DISEASE_SYNONYMS)


def lookup_cell_type_with_confidence(raw: str) -> tuple[str, str, float] | None:
    """Look up cell type with confidence tier.

    Returns (standardized_name, ontology_id, confidence) or None.
    Tiers: exact=1.0, synonym=0.85, substring heuristic=0.70.
    """
    return _lookup_with_confidence(raw, CELL_TYPE_ONTOLOGY, CELL_TYPE_SYNONYMS)


def lookup_treatment_with_confidence(raw: str) -> tuple[str, str, float] | None:
    """Look up treatment with confidence tier.

    Returns (standardized_name, ontology_id, confidence) or None.
    Tiers: exact=1.0, synonym=0.85, substring heuristic=0.70.
    """
    return _lookup_with_confidence(raw, TREATMENT_ONTOLOGY, TREATMENT_SYNONYMS)
