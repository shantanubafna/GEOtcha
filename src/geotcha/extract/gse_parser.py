"""GSE-level metadata extraction via GEOparse."""

from __future__ import annotations

import logging

import GEOparse

from geotcha.config import Settings
from geotcha.extract.fields import (
    aggregate_sample_field,
    detect_tissue,
    detect_treatment,
    extract_timepoint,
)
from geotcha.extract.gsm_parser import parse_gsm_samples
from geotcha.models import GSERecord

logger = logging.getLogger(__name__)


def parse_gse(gse_id: str, settings: Settings) -> GSERecord:
    """Parse a GSE entry into a structured GSERecord.

    Downloads the SOFT file (cached) and extracts series-level metadata.
    Also parses all GSM samples within the series.
    """
    cache_dir = settings.get_cache_dir()

    logger.info(f"Downloading/parsing SOFT file for {gse_id}")
    gse = GEOparse.get_GEO(geo=gse_id, destdir=str(cache_dir), silent=True)

    metadata = gse.metadata

    # Extract basic fields
    title = _get_first(metadata, "title")
    summary = _get_first(metadata, "summary")
    overall_design = _get_first(metadata, "overall_design")
    organism = metadata.get("platform_organism", metadata.get("sample_organism", []))
    experiment_type = metadata.get("type", [])
    platform = list(gse.gpls.keys()) if gse.gpls else []
    pubmed_ids = metadata.get("pubmed_id", [])

    # Combine text fields for extraction
    combined_text = f"{title} {summary} {overall_design}"

    # Parse all GSM samples first — we'll aggregate fields from them
    samples = parse_gsm_samples(gse, gse_id, settings)

    # Count human RNA-seq samples
    human_rnaseq_count = sum(
        1 for s in samples
        if "homo sapiens" in s.organism.lower()
        and _is_rnaseq_sample(s.library_strategy)
    )

    # Responder counts
    has_responder = any(s.responder_status is not None for s in samples)
    num_responders = sum(1 for s in samples if s.responder_status == "responder")
    num_non_responders = sum(1 for s in samples if s.responder_status == "non-responder")

    # Extract GSE-level fields: try GSE text first, then aggregate from samples
    tissue = detect_tissue(combined_text) or aggregate_sample_field(samples, "tissue")
    treatment = detect_treatment(combined_text) or aggregate_sample_field(samples, "treatment")
    timepoint = extract_timepoint(combined_text) or aggregate_sample_field(samples, "timepoint")

    # These fields are best aggregated from samples
    disease = aggregate_sample_field(samples, "disease")
    disease_status = aggregate_sample_field(samples, "disease_status")
    gender = aggregate_sample_field(samples, "gender")
    age = aggregate_sample_field(samples, "age")
    cell_type = aggregate_sample_field(samples, "cell_type")
    sample_acquisition = aggregate_sample_field(samples, "sample_acquisition")
    clinical_severity = aggregate_sample_field(samples, "clinical_severity")

    # Organism: prefer from metadata, fall back to sample aggregation
    if not organism or organism == []:
        organism_agg = aggregate_sample_field(samples, "organism")
        if organism_agg:
            organism = [o.strip() for o in organism_agg.split(";")]

    # Build GSE URL
    gse_url = f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={gse_id}"

    record = GSERecord(
        gse_id=gse_id,
        title=title,
        summary=summary,
        overall_design=overall_design,
        organism=organism if isinstance(organism, list) else [organism],
        experiment_type=experiment_type,
        platform=platform,
        total_samples=len(gse.gsms),
        human_rnaseq_samples=human_rnaseq_count,
        pubmed_ids=pubmed_ids,
        gse_url=gse_url,
        tissue=tissue,
        cell_type=cell_type,
        disease=disease,
        disease_status=disease_status,
        treatment=treatment,
        timepoint=timepoint,
        gender=gender,
        age=age,
        sample_acquisition=sample_acquisition,
        clinical_severity=clinical_severity,
        has_responder_info=has_responder,
        num_responders=num_responders,
        num_non_responders=num_non_responders,
        samples=samples,
    )

    return record


def _get_first(metadata: dict, key: str, default: str = "") -> str:
    """Get the first value from a metadata list field."""
    values = metadata.get(key, [])
    if isinstance(values, list) and values:
        return str(values[0])
    if isinstance(values, str):
        return values
    return default


def _is_rnaseq_sample(library_strategy: str) -> bool:
    """Check if a sample's library strategy indicates RNA-seq."""
    if not library_strategy:
        return True  # If not specified, don't filter out
    return "rna" in library_strategy.lower() or "rna-seq" in library_strategy.lower()
