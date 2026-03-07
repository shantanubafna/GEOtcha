"""Curated lookup tables for ontology mapping (UBERON, DOID, CL)."""

from __future__ import annotations

import json
import re
from functools import lru_cache
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


# ── Fuzzy matching helpers ───────────────────────────────────────────

_STRIP_SUFFIXES = re.compile(
    r"\s+(tissue|tissues|cells?|disease|syndrome|disorder|type|carcinoma|"
    r"adenocarcinoma|cancer|tumor|tumour|infection|positive|negative)$"
)
_NORMALIZE_RE = re.compile(r"[\s\-_/+]+")


@lru_cache(maxsize=8192)
def _normalize_key(text: str) -> str:
    """Normalize a lookup key: strip common suffixes, collapse whitespace/hyphens."""
    t = text.lower().strip()
    t = _STRIP_SUFFIXES.sub("", t)
    t = _NORMALIZE_RE.sub(" ", t).strip()
    return t


@lru_cache(maxsize=8192)
def _tokenize(text: str) -> frozenset[str]:
    """Split text into a set of lowercase tokens (>1 char)."""
    return frozenset(tok for tok in _NORMALIZE_RE.split(text.lower()) if len(tok) > 1)


def _token_set_match(query_tokens: frozenset[str], key_tokens: frozenset[str]) -> bool:
    """Return True if all tokens of the shorter set appear in the longer set.

    Requires at least 2 tokens in the shorter set to avoid trivial matches.
    """
    if not query_tokens or not key_tokens:
        return False
    shorter, longer = (
        (query_tokens, key_tokens)
        if len(query_tokens) <= len(key_tokens)
        else (key_tokens, query_tokens)
    )
    if len(shorter) < 2:
        return False
    return shorter.issubset(longer)


# ── Main lookup ──────────────────────────────────────────────────────


def _lookup_with_confidence(
    raw: str,
    ontology: dict[str, tuple[str, str]],
    synonyms: dict[str, str],
) -> tuple[str, str, float] | None:
    """5-tier lookup with confidence scoring.

    Tiers:
        1. Exact match (1.0)
        2. Synonym match (0.85)
        3. Normalized exact (0.80) — strip suffixes, normalize whitespace/hyphens
        4. Token-set overlap (0.75) — all tokens of shorter set in longer set
        5. Substring heuristic (0.70) — ontology key appears in query text

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

    # Tier 3: normalized exact match
    norm_key = _normalize_key(key)
    if norm_key != key:
        result = ontology.get(norm_key)
        if result:
            return (result[0], result[1], 0.80)
        # Also check synonyms with the normalized key
        canonical = synonyms.get(norm_key)
        if canonical:
            result = ontology.get(canonical)
            if result:
                return (result[0], result[1], 0.80)

    # Tier 4: token-set overlap
    query_tokens = _tokenize(key)
    if len(query_tokens) >= 2:
        for ont_key, (name, ont_id) in ontology.items():
            key_tokens = _tokenize(ont_key)
            if _token_set_match(query_tokens, key_tokens):
                return (name, ont_id, 0.75)

    # Tier 5: substring heuristic
    for ontology_key, (name, ont_id) in ontology.items():
        if _substring_match(ontology_key, key):
            return (name, ont_id, 0.70)

    return None


def lookup_tissue_with_confidence(raw: str) -> tuple[str, str, float] | None:
    """Look up tissue with confidence tier."""
    return _lookup_with_confidence(raw, TISSUE_ONTOLOGY, TISSUE_SYNONYMS)


def lookup_disease_with_confidence(raw: str) -> tuple[str, str, float] | None:
    """Look up disease with confidence tier."""
    return _lookup_with_confidence(raw, DISEASE_ONTOLOGY, DISEASE_SYNONYMS)


def lookup_cell_type_with_confidence(raw: str) -> tuple[str, str, float] | None:
    """Look up cell type with confidence tier."""
    return _lookup_with_confidence(raw, CELL_TYPE_ONTOLOGY, CELL_TYPE_SYNONYMS)


def lookup_treatment_with_confidence(raw: str) -> tuple[str, str, float] | None:
    """Look up treatment with confidence tier."""
    return _lookup_with_confidence(raw, TREATMENT_ONTOLOGY, TREATMENT_SYNONYMS)
