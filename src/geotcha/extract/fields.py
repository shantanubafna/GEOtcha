"""Field extraction utilities for treatment, responder status, timepoint detection."""

from __future__ import annotations

import re
from collections import Counter
from typing import Optional


# Patterns for responder status detection
RESPONDER_PATTERNS = [
    (re.compile(r"\bnon[-\s]?responder\b", re.IGNORECASE), "non-responder"),
    (re.compile(r"\bpartial[-\s]?responder\b", re.IGNORECASE), "partial responder"),
    (re.compile(r"\bresponder\b", re.IGNORECASE), "responder"),
    (re.compile(r"\bNR\b"), "non-responder"),
    (re.compile(r"\bPR\b"), "partial responder"),
    (re.compile(r"\bresponse:\s*yes\b", re.IGNORECASE), "responder"),
    (re.compile(r"\bresponse:\s*no\b", re.IGNORECASE), "non-responder"),
    (re.compile(r"\bprimary response:\s*non[-\s]?responder\b", re.IGNORECASE), "non-responder"),
    (re.compile(r"\bprimary response:\s*responder\b", re.IGNORECASE), "responder"),
    (re.compile(r"\bremission\b", re.IGNORECASE), "responder"),
    (re.compile(r"\brefractory\b", re.IGNORECASE), "non-responder"),
]

# Patterns for timepoint extraction from free text
TIMEPOINT_PATTERNS = [
    # Week patterns: W4, week 4, Week4, wk4, "weeks from/fron start of treatment: 2"
    (re.compile(r"\bweeks?\s+(?:from|fron)\s+\w+\s+(?:of\s+)?\w+:\s*(\d+)\b", re.IGNORECASE), "W"),
    (re.compile(r"\b(?:week|wk|w)\s*(\d+)\b", re.IGNORECASE), "W"),
    # Day patterns: D7, day 7, Day7, d7
    (re.compile(r"\b(?:day|d)\s*(\d+)\b", re.IGNORECASE), "D"),
    # Month patterns: M3, month 3, mo3
    (re.compile(r"\b(?:month|mo)\s*(\d+)\b", re.IGNORECASE), "M"),
    # Hour patterns: 24h, 24hr, 24 hours
    (re.compile(r"\b(\d+)\s*(?:hr|hour|h)\b", re.IGNORECASE), "H"),
    # Baseline/pre-treatment
    (re.compile(r"\bbefore\s+(?:initiation\s+of\s+)?treatment\b", re.IGNORECASE), "baseline"),
    (re.compile(r"\bbaseline\b", re.IGNORECASE), "baseline"),
    (re.compile(r"\bpre[-\s]?treatment\b", re.IGNORECASE), "baseline"),
    (re.compile(r"\bpost[-\s]?treatment\b", re.IGNORECASE), "post-treatment"),
]

# Known drug names for clean treatment extraction
KNOWN_DRUGS = [
    "infliximab", "adalimumab", "vedolizumab", "ustekinumab",
    "tofacitinib", "filgotinib", "ozanimod", "risankizumab",
    "golimumab", "certolizumab", "natalizumab", "rituximab",
    "tocilizumab", "secukinumab", "ixekizumab", "guselkumab",
    "prednisone", "prednisolone", "budesonide", "dexamethasone",
    "hydrocortisone", "methylprednisolone",
    "mesalamine", "mesalazine", "sulfasalazine",
    "azathioprine", "6-mercaptopurine", "methotrexate",
    "cyclosporine", "tacrolimus", "mycophenolate",
    "anti-tnf", "anti-il-12", "anti-il-23", "anti-integrin",
    "jak inhibitor", "s1p modulator",
    "placebo", "vehicle", "dmso",
]

# Characteristic keys that indicate treatment
TREATMENT_CHAR_KEYS = [
    "treatment", "drug", "therapy", "agent", "medication",
    "anti-tnf", "biologic", "compound", "stimulus", "stimulation",
    "dose", "dosage",
]

# Characteristic keys that indicate timepoint
TIMEPOINT_CHAR_KEYS = [
    "timepoint", "time point", "time", "visit", "sampling time",
    "weeks fron start of treatment", "weeks from start of treatment",
    "collection time", "time of collection", "day", "week",
]

# Characteristic keys that indicate sample acquisition
ACQUISITION_CHAR_KEYS = [
    "sample acquisition", "acquisition method", "collection method",
    "biopsy", "isolation", "sampling method", "specimen type",
    "sample type", "material type",
]

# Characteristic keys that indicate clinical severity
SEVERITY_CHAR_KEYS = [
    "clinical severity", "severity", "mayo score", "mayo",
    "cdai", "harvey-bradshaw", "hbi", "sccai", "pucai",
    "endoscopic score", "ses-cd", "uceis", "disease activity",
    "activity score", "clinical score",
]

# Characteristic keys for cell type
CELL_TYPE_CHAR_KEYS = [
    "cell type", "cell_type", "cell lineage", "cell population",
    "cell subtype", "sorted cell", "facs",
]

# Tissue keywords for detection
TISSUE_KEYWORDS = {
    "colon": "colon",
    "colonic": "colon",
    "ileum": "ileum",
    "ileal": "ileum",
    "rectum": "rectum",
    "rectal": "rectum",
    "intestine": "intestine",
    "intestinal": "intestine",
    "blood": "blood",
    "peripheral blood": "peripheral blood",
    "pbmc": "PBMC",
    "whole blood": "whole blood",
    "serum": "serum",
    "plasma": "plasma",
    "biopsy": "biopsy",
    "liver": "liver",
    "lung": "lung",
    "brain": "brain",
    "skin": "skin",
    "muscle": "muscle",
    "kidney": "kidney",
    "heart": "heart",
    "bone marrow": "bone marrow",
    "lymph node": "lymph node",
    "spleen": "spleen",
    "thymus": "thymus",
    "adipose": "adipose tissue",
    "pancreas": "pancreas",
    "stomach": "stomach",
    "gastric": "stomach",
    "esophagus": "esophagus",
    "duodenum": "duodenum",
    "jejunum": "jejunum",
    "cecum": "cecum",
    "sigmoid": "sigmoid colon",
}

# Sample acquisition keywords
ACQUISITION_KEYWORDS = {
    "biopsy": "biopsy",
    "punch biopsy": "punch biopsy",
    "endoscopic biopsy": "endoscopic biopsy",
    "colonoscopy": "colonoscopy biopsy",
    "blood draw": "blood draw",
    "venipuncture": "venipuncture",
    "surgical resection": "surgical resection",
    "resection": "surgical resection",
    "surgery": "surgical resection",
    "lavage": "lavage",
    "aspiration": "aspiration",
    "fine needle": "fine needle aspiration",
    "swab": "swab",
    "scraping": "scraping",
}


def detect_responder_status(text: str) -> Optional[str]:
    """Detect responder/non-responder status from text."""
    for pattern, status in RESPONDER_PATTERNS:
        if pattern.search(text):
            return status
    return None


def extract_responder_from_characteristics(chars: dict[str, str]) -> Optional[str]:
    """Extract responder status from parsed characteristics."""
    responder_keys = [
        "response", "primary response", "responder", "responder status",
        "treatment response", "clinical response",
    ]
    for key in responder_keys:
        if key in chars:
            val = chars[key].lower().strip()
            if "non" in val or val == "nr":
                return "non-responder"
            if "partial" in val:
                return "partial responder"
            if "responder" in val or val in ("yes", "y", "r"):
                return "responder"
    return None


def extract_timepoint(text: str) -> Optional[str]:
    """Extract timepoint from text and normalize to standard format."""
    for pattern, prefix in TIMEPOINT_PATTERNS:
        match = pattern.search(text)
        if match:
            if prefix in ("baseline", "post-treatment"):
                return prefix
            value = match.group(1)
            # "0" weeks/days = baseline
            if value == "0":
                return "baseline"
            return f"{prefix}{value}"
    return None


def extract_timepoint_from_characteristics(chars: dict[str, str]) -> Optional[str]:
    """Extract timepoint from parsed characteristics."""
    for key in TIMEPOINT_CHAR_KEYS:
        if key in chars:
            val = chars[key].strip()
            # Try to normalize the value
            if val == "0":
                return "baseline"
            # Check if it's a plain number (weeks/days implied by key)
            if val.isdigit():
                if "week" in key:
                    return f"W{val}"
                if "day" in key:
                    return f"D{val}"
                return val
            # Try pattern-based extraction on the value
            tp = extract_timepoint(val)
            if tp:
                return tp
            # Check for "before initiation of treatment" style
            if "before" in val.lower():
                return "baseline"
            return val
    # Also check "time" key with value like "before initiation of treatment"
    for key, val in chars.items():
        if key == "time":
            if "before" in val.lower() or val.strip() == "0":
                return "baseline"
            tp = extract_timepoint(val)
            if tp:
                return tp
            return val
    return None


def extract_treatment_from_characteristics(chars: dict[str, str]) -> Optional[str]:
    """Extract treatment from parsed characteristics.

    Looks for treatment-specific keys and known drug names in values.
    """
    # Check treatment-specific characteristic keys
    for key in TREATMENT_CHAR_KEYS:
        if key in chars:
            return chars[key]

    # Check if any characteristic value contains a known drug name
    for key, val in chars.items():
        val_lower = val.lower()
        for drug in KNOWN_DRUGS:
            if drug in val_lower:
                return val

    return None


def detect_treatment(text: str) -> Optional[str]:
    """Detect treatment from free text, returning a clean drug name or description.

    Prefers returning just the drug name rather than surrounding context.
    """
    text_lower = text.lower()

    # First try to find specific drug names
    found_drugs: list[str] = []
    for drug in KNOWN_DRUGS:
        if drug in text_lower:
            found_drugs.append(drug)

    if found_drugs:
        # Return the most specific (longest) drug match
        found_drugs.sort(key=len, reverse=True)
        return found_drugs[0]

    return None


def detect_tissue(text: str) -> Optional[str]:
    """Detect tissue from text using keyword matching."""
    text_lower = text.lower()
    # Check longer phrases first to avoid partial matches
    for keyword in sorted(TISSUE_KEYWORDS, key=len, reverse=True):
        if keyword in text_lower:
            return TISSUE_KEYWORDS[keyword]
    return None


def detect_sample_acquisition(text: str) -> Optional[str]:
    """Detect sample acquisition method from text."""
    text_lower = text.lower()
    for keyword in sorted(ACQUISITION_KEYWORDS, key=len, reverse=True):
        if keyword in text_lower:
            return ACQUISITION_KEYWORDS[keyword]
    return None


def extract_sample_acquisition_from_characteristics(chars: dict[str, str]) -> Optional[str]:
    """Extract sample acquisition from parsed characteristics."""
    for key in ACQUISITION_CHAR_KEYS:
        if key in chars:
            return chars[key]
    return None


def extract_clinical_severity_from_characteristics(chars: dict[str, str]) -> Optional[str]:
    """Extract clinical severity endpoint from parsed characteristics."""
    for key in SEVERITY_CHAR_KEYS:
        if key in chars:
            return chars[key]
    # Also check partial key matches (e.g., "mayo score" might be "partial mayo score")
    for key, val in chars.items():
        for sev_key in SEVERITY_CHAR_KEYS:
            if sev_key in key:
                return f"{key}: {val}"
    return None


def extract_cell_type_from_characteristics(chars: dict[str, str]) -> Optional[str]:
    """Extract cell type from parsed characteristics."""
    for key in CELL_TYPE_CHAR_KEYS:
        if key in chars:
            return chars[key]
    return None


def parse_characteristics(characteristics_list: list[str]) -> dict[str, str]:
    """Parse GEO characteristics_ch1 into key-value pairs.

    GEO characteristics are typically in "key: value" format.
    """
    parsed: dict[str, str] = {}
    for item in characteristics_list:
        item = item.strip()
        if ": " in item:
            key, value = item.split(": ", 1)
            parsed[key.strip().lower()] = value.strip()
        elif "=" in item:
            key, value = item.split("=", 1)
            parsed[key.strip().lower()] = value.strip()
        else:
            # No clear separator; store with index key
            parsed[f"field_{len(parsed)}"] = item
    return parsed


def extract_gender_from_characteristics(chars: dict[str, str]) -> Optional[str]:
    """Extract gender from parsed characteristics."""
    gender_keys = ["gender", "sex", "Sex", "Gender"]
    for key in gender_keys:
        if key.lower() in chars:
            return chars[key.lower()]
    return None


def extract_age_from_characteristics(chars: dict[str, str]) -> Optional[str]:
    """Extract age from parsed characteristics."""
    age_keys = ["age", "age (years)", "age_years", "patient age", "age at diagnosis"]
    for key in age_keys:
        if key.lower() in chars:
            return chars[key.lower()]
    return None


def extract_disease_from_characteristics(chars: dict[str, str]) -> Optional[str]:
    """Extract disease from parsed characteristics."""
    disease_keys = [
        "disease", "diagnosis", "condition", "disease state",
        "disease status", "pathology", "disease_state",
    ]
    for key in disease_keys:
        if key.lower() in chars:
            return chars[key.lower()]
    return None


def aggregate_sample_field(samples: list, field: str) -> Optional[str]:
    """Aggregate a field across samples into a summary string.

    Returns the most common non-None value, or a semicolon-separated list
    of unique values if there are multiple.
    """
    values = [getattr(s, field) for s in samples if getattr(s, field, None)]
    if not values:
        return None
    counts = Counter(values)
    unique = list(counts.keys())
    if len(unique) == 1:
        return unique[0]
    # Return semicolon-separated unique values sorted by frequency
    sorted_vals = sorted(unique, key=lambda v: -counts[v])
    return "; ".join(sorted_vals)
