"""URL generation and publication formatting."""

from __future__ import annotations


def gse_url(gse_id: str) -> str:
    """Generate GEO URL for a GSE accession."""
    return f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={gse_id}"


def gsm_url(gsm_id: str) -> str:
    """Generate GEO URL for a GSM accession."""
    return f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={gsm_id}"


def pubmed_url(pubmed_id: str) -> str:
    """Generate PubMed URL for a PubMed ID."""
    return f"https://pubmed.ncbi.nlm.nih.gov/{pubmed_id}/"


def format_pubmed_ids(pubmed_ids: list[str]) -> str:
    """Format PubMed IDs as a semicolon-separated list of URLs."""
    if not pubmed_ids:
        return ""
    return "; ".join(pubmed_url(pid) for pid in pubmed_ids)
