"""Query construction with ontology-aware disease expansion."""

from __future__ import annotations

from functools import lru_cache

# Disease expansion mappings with two tiers:
# - search_terms: safe for Entrez queries (full names + unambiguous abbreviations)
# - relevance_keywords: all terms including ambiguous short abbreviations,
#   used for post-search relevance checking only
DISEASE_EXPANSIONS: dict[str, dict[str, list[str]]] = {
    "ibd": {
        "search_terms": [
            "inflammatory bowel disease",
            "ulcerative colitis",
            "crohn's disease",
            "crohn disease",
            "IBD",
        ],
        "relevance_keywords": [
            "inflammatory bowel disease",
            "ulcerative colitis",
            "crohn's disease",
            "crohn disease",
            "IBD",
            "UC",
            "CD",
        ],
    },
    "inflammatory bowel disease": {
        "search_terms": [
            "inflammatory bowel disease",
            "ulcerative colitis",
            "crohn's disease",
            "crohn disease",
            "IBD",
        ],
        "relevance_keywords": [
            "inflammatory bowel disease",
            "ulcerative colitis",
            "crohn's disease",
            "crohn disease",
            "IBD",
            "UC",
            "CD",
        ],
    },
    "ulcerative colitis": {
        "search_terms": [
            "ulcerative colitis",
        ],
        "relevance_keywords": [
            "ulcerative colitis",
            "UC",
        ],
    },
    "crohn's disease": {
        "search_terms": [
            "crohn's disease",
            "crohn disease",
        ],
        "relevance_keywords": [
            "crohn's disease",
            "crohn disease",
            "CD",
        ],
    },
    "als": {
        "search_terms": [
            "amyotrophic lateral sclerosis",
            "ALS",
            "motor neuron disease",
            "Lou Gehrig's disease",
        ],
        "relevance_keywords": [
            "amyotrophic lateral sclerosis",
            "ALS",
            "motor neuron disease",
            "Lou Gehrig's disease",
        ],
    },
    "amyotrophic lateral sclerosis": {
        "search_terms": [
            "amyotrophic lateral sclerosis",
            "ALS",
            "motor neuron disease",
        ],
        "relevance_keywords": [
            "amyotrophic lateral sclerosis",
            "ALS",
            "motor neuron disease",
        ],
    },
    "ms": {
        "search_terms": [
            "multiple sclerosis",
        ],
        "relevance_keywords": [
            "multiple sclerosis",
            "MS",
        ],
    },
    "multiple sclerosis": {
        "search_terms": [
            "multiple sclerosis",
        ],
        "relevance_keywords": [
            "multiple sclerosis",
            "MS",
        ],
    },
    "ra": {
        "search_terms": [
            "rheumatoid arthritis",
        ],
        "relevance_keywords": [
            "rheumatoid arthritis",
            "RA",
        ],
    },
    "rheumatoid arthritis": {
        "search_terms": [
            "rheumatoid arthritis",
        ],
        "relevance_keywords": [
            "rheumatoid arthritis",
            "RA",
        ],
    },
    "sle": {
        "search_terms": [
            "systemic lupus erythematosus",
            "SLE",
            "lupus",
        ],
        "relevance_keywords": [
            "systemic lupus erythematosus",
            "SLE",
            "lupus",
        ],
    },
    "lupus": {
        "search_terms": [
            "systemic lupus erythematosus",
            "SLE",
            "lupus",
        ],
        "relevance_keywords": [
            "systemic lupus erythematosus",
            "SLE",
            "lupus",
        ],
    },
    "copd": {
        "search_terms": [
            "chronic obstructive pulmonary disease",
            "COPD",
        ],
        "relevance_keywords": [
            "chronic obstructive pulmonary disease",
            "COPD",
        ],
    },
    "t2d": {
        "search_terms": [
            "type 2 diabetes",
            "type 2 diabetes mellitus",
        ],
        "relevance_keywords": [
            "type 2 diabetes",
            "type 2 diabetes mellitus",
            "T2D",
        ],
    },
    "t1d": {
        "search_terms": [
            "type 1 diabetes",
            "type 1 diabetes mellitus",
        ],
        "relevance_keywords": [
            "type 1 diabetes",
            "type 1 diabetes mellitus",
            "T1D",
        ],
    },
    "ad": {
        "search_terms": [
            "Alzheimer's disease",
            "Alzheimer disease",
        ],
        "relevance_keywords": [
            "Alzheimer's disease",
            "Alzheimer disease",
            "AD",
        ],
    },
    "pd": {
        "search_terms": [
            "Parkinson's disease",
            "Parkinson disease",
        ],
        "relevance_keywords": [
            "Parkinson's disease",
            "Parkinson disease",
            "PD",
        ],
    },
}

# Maximum number of ontology subtypes to include in search expansion
_MAX_ONTOLOGY_SUBTYPES = 8


# Common cancer term equivalences for subtype matching
_CANCER_SYNONYMS = {
    "cancer": ["carcinoma", "neoplasm", "tumor", "tumour", "malignancy"],
    "carcinoma": ["cancer"],
}


@lru_cache(maxsize=256)
def _ontology_subtypes(canonical: str) -> list[str]:
    """Find disease subtypes from the DOID ontology whose names contain the query.

    Returns up to _MAX_ONTOLOGY_SUBTYPES clinically common subtypes,
    sorted shortest-first to prefer the most specific common names.
    """
    from geotcha.harmonize.ontology import DISEASE_ONTOLOGY

    canonical_lower = canonical.lower()
    # Skip very short terms to avoid noisy matches
    if len(canonical_lower) < 4:
        return []

    # Build a set of search stems from the canonical name
    # e.g., "lung cancer" → search for "lung cancer", "lung carcinoma", etc.
    search_terms = {canonical_lower}
    for word, synonyms in _CANCER_SYNONYMS.items():
        if word in canonical_lower:
            for syn in synonyms:
                search_terms.add(canonical_lower.replace(word, syn))

    subtypes: list[str] = []
    for key, (name, _ont_id) in DISEASE_ONTOLOGY.items():
        if key == canonical_lower:
            continue
        for term in search_terms:
            if term in key:
                subtypes.append(name)
                break

    # Sort by length (shorter = more common/clinically relevant), then alphabetical
    subtypes.sort(key=lambda s: (len(s), s))
    return subtypes[:_MAX_ONTOLOGY_SUBTYPES]


def expand_disease_terms(query: str) -> list[str]:
    """Expand a disease keyword into search-safe variants.

    Returns a list of terms safe for use in Entrez queries
    (excludes ambiguous short abbreviations).

    Uses two sources:
    1. Hand-curated DISEASE_EXPANSIONS for well-known abbreviations/aliases
    2. DOID ontology subtypes for any term that matches a disease in the ontology
    """
    key = query.lower().strip()

    # Start with hand-curated expansions if available
    if key in DISEASE_EXPANSIONS:
        base = list(DISEASE_EXPANSIONS[key]["search_terms"])
    else:
        base = [query]

    # Add ontology subtypes for the canonical disease name
    from geotcha.harmonize.ontology import lookup_disease_with_confidence

    match = lookup_disease_with_confidence(query)
    if match and match[2] >= 0.85:
        canonical = match[0]
        subtypes = _ontology_subtypes(canonical)
        # Add subtypes not already in the list
        existing_lower = {t.lower() for t in base}
        for st in subtypes:
            if st.lower() not in existing_lower:
                base.append(st)
                existing_lower.add(st.lower())

    return base


def get_relevance_keywords(query: str) -> list[str]:
    """Get all relevance keywords for a query, including ambiguous abbreviations.

    These are used for post-search relevance filtering, not for the Entrez query.
    """
    key = query.lower().strip()
    if key in DISEASE_EXPANSIONS:
        return DISEASE_EXPANSIONS[key]["relevance_keywords"]
    return [query]


def build_query(query: str) -> str:
    """Build an Entrez search query with disease expansion.

    Constructs a query that searches across GEO DataSets (GDS) database
    combining disease terms with OR, filtered to expression profiling by
    high throughput sequencing.
    """
    terms = expand_disease_terms(query)

    # Build disease part: ("term1" OR "term2" OR ...)
    quoted = [f'"{t}"' for t in terms]
    disease_part = " OR ".join(quoted)

    # Add organism and data type filters
    # gds database search syntax
    full_query = (
        f"({disease_part})"
        ' AND "Homo sapiens"[Organism]'
        ' AND "Expression profiling by high throughput sequencing"[DataSet Type]'
    )
    return full_query
