"""Filtering search results to human RNA-seq datasets."""

from __future__ import annotations

import logging
import re
from typing import Any

from geotcha.config import Settings
from geotcha.search.entrez import get_summaries
from geotcha.search.query_builder import get_relevance_keywords

logger = logging.getLogger(__name__)

# Patterns indicating single-cell RNA-seq datasets
SCRNA_PATTERNS = re.compile(
    r"single[\s\-]?cell|scRNA|snRNA|scATAC|10x\s*genomics|10x\s*chromium|"
    r"chromium|drop[\s\-]?seq|smart[\s\-]?seq2?|cel[\s\-]?seq|"
    r"plate[\s\-]?based\s*single|inDrop|sci[\s\-]?RNA|MARS[\s\-]?seq|"
    r"single[\s\-]?nucleus|single[\s\-]?nuclei",
    re.IGNORECASE,
)

# Valid data types for RNA-seq
RNASEQ_TYPES = {
    "Expression profiling by high throughput sequencing",
}

# Target organism
TARGET_ORGANISM = "Homo sapiens"


def _extract_gse_accession(summary: dict[str, Any]) -> str | None:
    """Extract the GSE accession from an eSummary record.

    GDS database entries may have different formats. The GSE accession
    might be in the 'Accession' field (for GSE entries) or 'GSE' field.
    """
    accession = str(summary.get("Accession", ""))
    if accession.startswith("GSE"):
        return accession

    gse = str(summary.get("GSE", ""))
    if gse:
        return f"GSE{gse}" if not gse.startswith("GSE") else gse

    return None


def _is_human_rnaseq(summary: dict[str, Any]) -> bool:
    """Check if an eSummary record is human RNA-seq."""
    taxon = str(summary.get("taxon", ""))
    gds_type = str(summary.get("gdsType", ""))

    # Check organism - must include Homo sapiens (can be multi-organism)
    is_human = TARGET_ORGANISM.lower() in taxon.lower()

    # Check data type
    is_rnaseq = any(rt.lower() in gds_type.lower() for rt in RNASEQ_TYPES)

    return is_human and is_rnaseq


def _is_relevant_to_query(summary: dict[str, Any], query: str) -> bool:
    """Check if an eSummary record is relevant to the disease query.

    Examines title and summary fields for disease-related keywords.
    For short abbreviations (<=3 chars), requires word-boundary matching
    to avoid substring false positives (e.g., "CD" shouldn't match "CDA"
    or "encoded").
    """
    keywords = get_relevance_keywords(query)
    title = str(summary.get("title", ""))
    description = str(summary.get("summary", ""))
    text = f"{title} {description}"

    for keyword in keywords:
        if len(keyword) <= 3:
            # Word-boundary matching for short abbreviations
            pattern = rf"\b{re.escape(keyword)}\b"
            if re.search(pattern, text, re.IGNORECASE):
                return True
        else:
            # Simple case-insensitive substring match for longer terms
            if keyword.lower() in text.lower():
                return True

    return False


def _is_single_cell(summary: dict[str, Any]) -> bool:
    """Check if an eSummary record looks like a single-cell RNA-seq dataset."""
    title = str(summary.get("title", ""))
    description = str(summary.get("summary", ""))
    text = f"{title} {description}"
    return bool(SCRNA_PATTERNS.search(text))


def filter_results(
    raw_ids: list[str], settings: Settings, query: str | None = None
) -> list[str]:
    """Filter search results to human RNA-seq datasets.

    Takes raw GDS IDs from eSearch, fetches eSummary for each,
    and returns GSE accessions that pass organism + data type filters
    and optionally disease relevance checks.

    Args:
        raw_ids: Raw GDS IDs from eSearch.
        settings: Application settings.
        query: Original disease query for relevance filtering.
            If None, skips relevance check (backward compatible).
    """
    if not raw_ids:
        return []

    summaries = get_summaries(raw_ids, settings)

    filtered_gse_ids: list[str] = []
    seen: set[str] = set()
    relevance_rejected = 0
    scrna_rejected = 0

    for summary in summaries:
        if not _is_human_rnaseq(summary):
            continue

        # Single-cell filter: skip scRNA-seq unless opted in
        if not settings.include_scrna and _is_single_cell(summary):
            gse_id = _extract_gse_accession(summary)
            logger.debug(
                f"Single-cell filter rejected {gse_id}: "
                f"title={summary.get('title', '')!r}"
            )
            scrna_rejected += 1
            continue

        # Relevance filter: check if the dataset is about the queried disease
        if query and not _is_relevant_to_query(summary, query):
            gse_id = _extract_gse_accession(summary)
            logger.debug(
                f"Relevance filter rejected {gse_id}: "
                f"title={summary.get('title', '')!r}"
            )
            relevance_rejected += 1
            continue

        gse_id = _extract_gse_accession(summary)
        if gse_id and gse_id not in seen:
            seen.add(gse_id)
            filtered_gse_ids.append(gse_id)

    logger.info(
        f"Filtered {len(raw_ids)} raw IDs down to {len(filtered_gse_ids)} human RNA-seq GSE IDs"
        f" ({relevance_rejected} rejected by relevance filter,"
        f" {scrna_rejected} rejected as single-cell)"
    )
    return filtered_gse_ids
