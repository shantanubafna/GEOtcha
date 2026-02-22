"""Deterministic rule-based normalization for metadata fields."""

from __future__ import annotations

import re
from typing import Optional

from geotcha.harmonize.ontology import lookup_disease, lookup_tissue
from geotcha.models import GSERecord, GSMRecord

# Gender normalization
GENDER_MAP: dict[str, str] = {
    "male": "male",
    "m": "male",
    "man": "male",
    "boy": "male",
    "female": "female",
    "f": "female",
    "woman": "female",
    "girl": "female",
    "unknown": "unknown",
    "na": "unknown",
    "n/a": "unknown",
    "not available": "unknown",
    "undetermined": "unknown",
}

# Age normalization patterns
AGE_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?|y\.?o\.?|yo)?\s*(?:old)?",
    re.IGNORECASE,
)

# Timepoint normalization
TIMEPOINT_PATTERNS = [
    (re.compile(r"^[Ww](?:eek|k)?\s*(\d+)$"), "W"),
    (re.compile(r"^[Dd](?:ay)?\s*(\d+)$"), "D"),
    (re.compile(r"^[Mm](?:onth|o)?\s*(\d+)$"), "M"),
    (re.compile(r"^(\d+)\s*[Hh](?:our|r)?s?$"), "H"),
    (re.compile(r"^baseline$", re.IGNORECASE), None),
    (re.compile(r"^pre[-\s]?treatment$", re.IGNORECASE), None),
    (re.compile(r"^post[-\s]?treatment$", re.IGNORECASE), None),
]


def normalize_gender(raw: Optional[str]) -> Optional[str]:
    """Normalize gender to male/female/unknown."""
    if not raw:
        return None
    return GENDER_MAP.get(raw.strip().lower())


def normalize_age(raw: Optional[str]) -> Optional[str]:
    """Normalize age to numeric years format."""
    if not raw:
        return None
    match = AGE_PATTERN.search(raw.strip())
    if match:
        age_val = float(match.group(1))
        if age_val == int(age_val):
            return str(int(age_val))
        return str(age_val)
    return raw.strip()


def normalize_tissue(raw: Optional[str]) -> Optional[str]:
    """Normalize tissue using UBERON ontology lookup."""
    if not raw:
        return None
    result = lookup_tissue(raw)
    if result:
        return result[0]
    return raw.strip().lower()


def normalize_disease(raw: Optional[str]) -> Optional[str]:
    """Normalize disease using disease ontology lookup."""
    if not raw:
        return None
    result = lookup_disease(raw)
    if result:
        return result[0]
    return raw.strip().lower()


def normalize_timepoint(raw: Optional[str]) -> Optional[str]:
    """Normalize timepoint to standard format (e.g., W4, D7)."""
    if not raw:
        return None
    raw = raw.strip()
    for pattern, prefix in TIMEPOINT_PATTERNS:
        match = pattern.match(raw)
        if match:
            if prefix is None:
                return raw.lower()
            return f"{prefix}{match.group(1)}"
    return raw


def normalize_treatment(raw: Optional[str]) -> Optional[str]:
    """Normalize treatment string.

    For now, just clean up whitespace and standardize casing.
    More sophisticated normalization (drug name standardization)
    can be added later.
    """
    if not raw:
        return None
    cleaned = " ".join(raw.strip().split())
    return cleaned


def harmonize_gsm(record: GSMRecord) -> GSMRecord:
    """Apply harmonization rules to a GSM record."""
    record.gender_harmonized = normalize_gender(record.gender)
    record.age_harmonized = normalize_age(record.age)
    record.tissue_harmonized = normalize_tissue(record.tissue)
    record.cell_type_harmonized = record.cell_type  # Pass through for now
    record.disease_harmonized = normalize_disease(record.disease)
    record.treatment_harmonized = normalize_treatment(record.treatment)
    record.timepoint_harmonized = normalize_timepoint(record.timepoint)
    return record


def harmonize_gse(record: GSERecord) -> GSERecord:
    """Apply harmonization rules to a GSE record."""
    record.tissue_harmonized = normalize_tissue(record.tissue)
    record.disease_harmonized = normalize_disease(record.disease)
    record.treatment_harmonized = normalize_treatment(record.treatment)
    record.timepoint_harmonized = normalize_timepoint(record.timepoint)
    return record
