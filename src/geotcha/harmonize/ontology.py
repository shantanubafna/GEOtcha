"""Curated lookup tables for ontology mapping (UBERON, MeSH, DO)."""

from __future__ import annotations

# UBERON tissue mappings: raw value -> (standardized name, UBERON ID)
TISSUE_ONTOLOGY: dict[str, tuple[str, str]] = {
    "colon": ("colon", "UBERON:0001155"),
    "colonic mucosa": ("colonic mucosa", "UBERON:0000317"),
    "colonic tissue": ("colon", "UBERON:0001155"),
    "ileum": ("ileum", "UBERON:0002116"),
    "ileal mucosa": ("ileal mucosa", "UBERON:0000331"),
    "rectum": ("rectum", "UBERON:0001052"),
    "rectal mucosa": ("rectal mucosa", "UBERON:0000332"),
    "intestine": ("intestine", "UBERON:0000160"),
    "small intestine": ("small intestine", "UBERON:0002108"),
    "large intestine": ("large intestine", "UBERON:0000059"),
    "blood": ("blood", "UBERON:0000178"),
    "peripheral blood": ("peripheral blood", "UBERON:0000178"),
    "whole blood": ("blood", "UBERON:0000178"),
    "pbmc": ("peripheral blood mononuclear cell", "CL:2000001"),
    "serum": ("blood serum", "UBERON:0001977"),
    "plasma": ("blood plasma", "UBERON:0001969"),
    "liver": ("liver", "UBERON:0002107"),
    "lung": ("lung", "UBERON:0002048"),
    "brain": ("brain", "UBERON:0000955"),
    "skin": ("skin", "UBERON:0002097"),
    "muscle": ("skeletal muscle tissue", "UBERON:0001134"),
    "kidney": ("kidney", "UBERON:0002113"),
    "heart": ("heart", "UBERON:0000948"),
    "bone marrow": ("bone marrow", "UBERON:0002371"),
    "lymph node": ("lymph node", "UBERON:0000029"),
    "spleen": ("spleen", "UBERON:0002106"),
    "thymus": ("thymus", "UBERON:0002370"),
    "adipose tissue": ("adipose tissue", "UBERON:0001013"),
    "adipose": ("adipose tissue", "UBERON:0001013"),
    "pancreas": ("pancreas", "UBERON:0001264"),
    "stomach": ("stomach", "UBERON:0000945"),
    "esophagus": ("esophagus", "UBERON:0001043"),
    "duodenum": ("duodenum", "UBERON:0002114"),
    "jejunum": ("jejunum", "UBERON:0002115"),
    "cecum": ("cecum", "UBERON:0001153"),
    "sigmoid colon": ("sigmoid colon", "UBERON:0001159"),
    "transverse colon": ("transverse colon", "UBERON:0001157"),
    "ascending colon": ("ascending colon", "UBERON:0001156"),
    "descending colon": ("descending colon", "UBERON:0001158"),
    "biopsy": ("biopsy", ""),
    "synovial tissue": ("synovial membrane", "UBERON:0000042"),
    "synovium": ("synovial membrane", "UBERON:0000042"),
    "tonsil": ("palatine tonsil", "UBERON:0002373"),
}

# Disease ontology mappings: raw value -> (standardized name, ontology ID)
DISEASE_ONTOLOGY: dict[str, tuple[str, str]] = {
    "ibd": ("inflammatory bowel disease", "DOID:0050589"),
    "inflammatory bowel disease": ("inflammatory bowel disease", "DOID:0050589"),
    "uc": ("ulcerative colitis", "DOID:8577"),
    "ulcerative colitis": ("ulcerative colitis", "DOID:8577"),
    "cd": ("Crohn's disease", "DOID:8778"),
    "crohn's disease": ("Crohn's disease", "DOID:8778"),
    "crohn disease": ("Crohn's disease", "DOID:8778"),
    "rheumatoid arthritis": ("rheumatoid arthritis", "DOID:7148"),
    "ra": ("rheumatoid arthritis", "DOID:7148"),
    "multiple sclerosis": ("multiple sclerosis", "DOID:2377"),
    "ms": ("multiple sclerosis", "DOID:2377"),
    "systemic lupus erythematosus": ("systemic lupus erythematosus", "DOID:9074"),
    "sle": ("systemic lupus erythematosus", "DOID:9074"),
    "lupus": ("systemic lupus erythematosus", "DOID:9074"),
    "type 2 diabetes": ("type 2 diabetes mellitus", "DOID:9352"),
    "t2d": ("type 2 diabetes mellitus", "DOID:9352"),
    "type 1 diabetes": ("type 1 diabetes mellitus", "DOID:9744"),
    "t1d": ("type 1 diabetes mellitus", "DOID:9744"),
    "alzheimer's disease": ("Alzheimer's disease", "DOID:10652"),
    "alzheimer disease": ("Alzheimer's disease", "DOID:10652"),
    "ad": ("Alzheimer's disease", "DOID:10652"),
    "parkinson's disease": ("Parkinson's disease", "DOID:14330"),
    "parkinson disease": ("Parkinson's disease", "DOID:14330"),
    "pd": ("Parkinson's disease", "DOID:14330"),
    "copd": ("chronic obstructive pulmonary disease", "DOID:3083"),
    "chronic obstructive pulmonary disease": ("chronic obstructive pulmonary disease", "DOID:3083"),
    "asthma": ("asthma", "DOID:2841"),
    "psoriasis": ("psoriasis", "DOID:8893"),
    "atopic dermatitis": ("atopic dermatitis", "DOID:3310"),
    "eczema": ("atopic dermatitis", "DOID:3310"),
    "healthy": ("healthy", ""),
    "normal": ("healthy", ""),
    "control": ("healthy", ""),
    "healthy control": ("healthy", ""),
}


TISSUE_SYNONYMS: dict[str, str] = {
    "gut": "intestine",
    "bowel": "intestine",
    "gi tract": "intestine",
    "gastrointestinal": "intestine",
    "whole blood": "blood",
    "colonic tissue": "colon",
}

DISEASE_SYNONYMS: dict[str, str] = {
    "crohns": "crohn's disease",
    "crohns disease": "crohn's disease",
    "uc disease": "ulcerative colitis",
    "lupus nephritis": "systemic lupus erythematosus",
}


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


def lookup_tissue_with_confidence(raw: str) -> tuple[str, str, float] | None:
    """Look up tissue with confidence tier.

    Returns (standardized_name, ontology_id, confidence) or None.
    Tiers: exact=1.0, synonym=0.85, substring heuristic=0.70.
    """
    key = raw.lower().strip()
    # Tier 1: exact match
    result = TISSUE_ONTOLOGY.get(key)
    if result:
        return (result[0], result[1], 1.0)
    # Tier 2: synonym match
    canonical = TISSUE_SYNONYMS.get(key)
    if canonical:
        result = TISSUE_ONTOLOGY.get(canonical)
        if result:
            return (result[0], result[1], 0.85)
    # Tier 3: substring heuristic (ontology key found in raw)
    for ontology_key, (name, ont_id) in TISSUE_ONTOLOGY.items():
        if _substring_match(ontology_key, key):
            return (name, ont_id, 0.70)
    return None


def lookup_disease_with_confidence(raw: str) -> tuple[str, str, float] | None:
    """Look up disease with confidence tier.

    Returns (standardized_name, ontology_id, confidence) or None.
    Tiers: exact=1.0, synonym=0.85, substring heuristic=0.70.
    """
    key = raw.lower().strip()
    # Tier 1: exact match
    result = DISEASE_ONTOLOGY.get(key)
    if result:
        return (result[0], result[1], 1.0)
    # Tier 2: synonym match
    canonical = DISEASE_SYNONYMS.get(key)
    if canonical:
        result = DISEASE_ONTOLOGY.get(canonical)
        if result:
            return (result[0], result[1], 0.85)
    # Tier 3: substring heuristic (ontology key found in raw)
    for ontology_key, (name, ont_id) in DISEASE_ONTOLOGY.items():
        if _substring_match(ontology_key, key):
            return (name, ont_id, 0.70)
    return None
