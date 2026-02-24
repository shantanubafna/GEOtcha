"""Deterministic rule-based normalization for metadata fields."""

from __future__ import annotations

import re
from typing import NamedTuple

from geotcha.harmonize.ontology import (
    lookup_disease_with_confidence,
    lookup_tissue_with_confidence,
)
from geotcha.models import GSERecord, GSMRecord


class NormResult(NamedTuple):
    """Result of a normalization operation with provenance metadata."""

    value: str | None
    source: str  # "rule" or "raw_fallback"
    confidence: float  # 1.0, 0.85, 0.70, or 0.50
    ontology_id: str | None


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


def normalize_gender(raw: str | None) -> NormResult | None:
    """Normalize gender to male/female/unknown."""
    if not raw:
        return None
    result = GENDER_MAP.get(raw.strip().lower())
    if result:
        return NormResult(result, "rule", 1.0, None)
    return NormResult(raw.strip().lower(), "raw_fallback", 0.50, None)


def normalize_age(raw: str | None) -> NormResult | None:
    """Normalize age to numeric years format."""
    if not raw:
        return None
    match = AGE_PATTERN.search(raw.strip())
    if match:
        age_val = float(match.group(1))
        if age_val == int(age_val):
            return NormResult(str(int(age_val)), "rule", 1.0, None)
        return NormResult(str(age_val), "rule", 1.0, None)
    return NormResult(raw.strip(), "raw_fallback", 0.50, None)


def normalize_tissue(raw: str | None) -> NormResult | None:
    """Normalize tissue using UBERON ontology lookup with confidence tiers."""
    if not raw:
        return None
    result = lookup_tissue_with_confidence(raw)
    if result:
        return NormResult(result[0], "rule", result[2], result[1])
    return NormResult(raw.strip().lower(), "raw_fallback", 0.50, None)


def normalize_disease(raw: str | None) -> NormResult | None:
    """Normalize disease using disease ontology lookup with confidence tiers."""
    if not raw:
        return None
    result = lookup_disease_with_confidence(raw)
    if result:
        return NormResult(result[0], "rule", result[2], result[1])
    return NormResult(raw.strip().lower(), "raw_fallback", 0.50, None)


def normalize_timepoint(raw: str | None) -> NormResult | None:
    """Normalize timepoint to standard format (e.g., W4, D7)."""
    if not raw:
        return None
    raw = raw.strip()
    for pattern, prefix in TIMEPOINT_PATTERNS:
        match = pattern.match(raw)
        if match:
            if prefix is None:
                return NormResult(raw.lower(), "rule", 1.0, None)
            return NormResult(f"{prefix}{match.group(1)}", "rule", 1.0, None)
    return NormResult(raw, "raw_fallback", 0.50, None)


def normalize_treatment(raw: str | None) -> NormResult | None:
    """Normalize treatment string."""
    if not raw:
        return None
    cleaned = " ".join(raw.strip().split())
    return NormResult(cleaned, "rule", 0.70, None)


def _apply_norm(record, field: str, result: NormResult | None) -> None:
    """Apply a NormResult to a record's harmonized + provenance fields."""
    if result:
        setattr(record, f"{field}_harmonized", result.value)
        setattr(record, f"{field}_source", result.source)
        setattr(record, f"{field}_confidence", result.confidence)
        setattr(record, f"{field}_ontology_id", result.ontology_id)


def harmonize_gsm(record: GSMRecord) -> GSMRecord:
    """Apply harmonization rules to a GSM record."""
    _apply_norm(record, "gender", normalize_gender(record.gender))
    _apply_norm(record, "age", normalize_age(record.age))
    _apply_norm(record, "tissue", normalize_tissue(record.tissue))
    _apply_norm(record, "disease", normalize_disease(record.disease))
    _apply_norm(record, "treatment", normalize_treatment(record.treatment))
    _apply_norm(record, "timepoint", normalize_timepoint(record.timepoint))

    # Cell type: pass-through with raw_fallback provenance
    if record.cell_type:
        record.cell_type_harmonized = record.cell_type
        record.cell_type_source = "raw_fallback"
        record.cell_type_confidence = 0.50
        record.cell_type_ontology_id = None

    return record


def harmonize_gse(record: GSERecord) -> GSERecord:
    """Apply harmonization rules to a GSE record."""
    _apply_norm(record, "tissue", normalize_tissue(record.tissue))
    _apply_norm(record, "disease", normalize_disease(record.disease))
    _apply_norm(record, "treatment", normalize_treatment(record.treatment))
    _apply_norm(record, "timepoint", normalize_timepoint(record.timepoint))
    return record
