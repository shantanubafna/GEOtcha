"""GSM sample-level metadata extraction."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from geotcha.config import Settings
from geotcha.extract.fields import (
    detect_responder_status,
    detect_sample_acquisition,
    detect_tissue,
    detect_treatment,
    extract_age_from_characteristics,
    extract_cell_type_from_characteristics,
    extract_clinical_severity_from_characteristics,
    extract_disease_from_characteristics,
    extract_disease_status_from_characteristics,
    extract_gender_from_characteristics,
    extract_responder_from_characteristics,
    extract_sample_acquisition_from_characteristics,
    extract_timepoint,
    extract_timepoint_from_characteristics,
    extract_tissue_from_characteristics,
    extract_treatment_from_characteristics,
    parse_characteristics,
    parse_source_name,
)
from geotcha.models import GSMRecord

if TYPE_CHECKING:
    import GEOparse

logger = logging.getLogger(__name__)


def parse_gsm_samples(
    gse: GEOparse.GEOTypes.GSE,
    gse_id: str,
    settings: Settings,
    include_scrna: bool = False,
) -> list[GSMRecord]:
    """Parse all GSM samples from a GSE object.

    Filters to keep only human RNA-seq samples.
    """
    records: list[GSMRecord] = []

    for gsm_id, gsm in gse.gsms.items():
        metadata = gsm.metadata
        organism = _get_first(metadata, "organism_ch1")

        # Parse characteristics
        chars_raw = metadata.get("characteristics_ch1", [])
        characteristics = parse_characteristics(chars_raw)

        # Build combined text for field extraction
        title = _get_first(metadata, "title")
        source = _get_first(metadata, "source_name_ch1")
        description = _get_first(metadata, "description")
        combined_text = " ".join([title, source, description] + chars_raw)

        # Extract structured fields — prefer characteristics, fall back to text
        gender = extract_gender_from_characteristics(characteristics)
        age = extract_age_from_characteristics(characteristics)
        disease = extract_disease_from_characteristics(characteristics)

        # Tissue: try characteristic keys, then keyword detection, then source_name
        tissue = extract_tissue_from_characteristics(characteristics)
        if not tissue:
            tissue = detect_tissue(source) or detect_tissue(combined_text)

        # Treatment: try characteristics first, then free text
        treatment = extract_treatment_from_characteristics(characteristics)
        if not treatment:
            treatment = detect_treatment(combined_text)

        # Timepoint: try characteristics first, then free text
        timepoint = extract_timepoint_from_characteristics(characteristics)
        if not timepoint:
            timepoint = extract_timepoint(combined_text)

        # Responder: try characteristics first, then free text
        responder = extract_responder_from_characteristics(characteristics)
        if not responder:
            responder = detect_responder_status(combined_text)

        # Cell type from characteristics
        cell_type = extract_cell_type_from_characteristics(characteristics)

        # Fill gaps from source_name parsing (structured segments)
        if source and any(
            f is None for f in [tissue, disease, cell_type, treatment]
        ):
            source_fields = parse_source_name(source)
            if not tissue and "tissue" in source_fields:
                tissue = source_fields["tissue"]
            if not disease and "disease" in source_fields:
                disease = source_fields["disease"]
            if not cell_type and "cell_type" in source_fields:
                cell_type = source_fields["cell_type"]
            if not treatment and "treatment" in source_fields:
                treatment = source_fields["treatment"]
            if not gender and "gender" in source_fields:
                gender = source_fields["gender"]
            if not age and "age" in source_fields:
                age = source_fields["age"]

        # Disease status
        disease_status, _ = extract_disease_status_from_characteristics(characteristics)

        # Sample acquisition: try characteristics, then text
        sample_acq = extract_sample_acquisition_from_characteristics(characteristics)
        if not sample_acq:
            sample_acq = detect_sample_acquisition(combined_text)

        # Clinical severity
        clinical_sev = extract_clinical_severity_from_characteristics(characteristics)

        # Library info
        library_strategy = _get_first(metadata, "library_strategy")
        library_source = _get_first(metadata, "library_source")
        instrument = _get_first(metadata, "instrument_model")
        platform_id = _get_first(metadata, "platform_id")
        molecule = _get_first(metadata, "molecule_ch1")

        record = GSMRecord(
            gsm_id=gsm_id,
            gse_id=gse_id,
            title=title,
            source_name=source,
            organism=organism,
            molecule=molecule,
            platform_id=platform_id,
            instrument=instrument,
            library_strategy=library_strategy,
            library_source=library_source,
            characteristics=characteristics,
            tissue=tissue,
            cell_type=cell_type,
            disease=disease,
            disease_status=disease_status,
            gender=gender,
            age=age,
            treatment=treatment,
            timepoint=timepoint,
            responder_status=responder,
            sample_acquisition=sample_acq,
            clinical_severity=clinical_sev,
            description=description,
        )
        records.append(record)

    # Filter to human RNA-seq samples only
    filtered = _filter_human_rnaseq(records, include_scrna=include_scrna)
    logger.info(
        f"{gse_id}: {len(records)} total samples, {len(filtered)} human RNA-seq samples"
    )
    return filtered


def _is_single_cell_sample(record: GSMRecord) -> bool:
    """Check if a GSM sample is single-cell based on metadata fields.

    Checks library_source, library_strategy, title, description,
    and characteristics values using SCRNA_PATTERNS regex.
    """
    from geotcha.search.filters import SCRNA_PATTERNS

    library_source = (record.library_source or "").lower()
    if "single cell" in library_source:
        return True
    library_strategy = (record.library_strategy or "").lower()
    if "single cell" in library_strategy or "scrna" in library_strategy:
        return True
    text = " ".join([
        record.title or "",
        record.description or "",
        *record.characteristics.values(),
    ])
    if SCRNA_PATTERNS.search(text):
        return True
    return False


def _filter_human_rnaseq(
    records: list[GSMRecord], include_scrna: bool = False,
) -> list[GSMRecord]:
    """Filter to keep only human RNA-seq samples.

    When include_scrna is False, samples with library_source containing
    'single cell' (e.g. 'transcriptomic single cell') are excluded.
    """
    filtered = []
    for r in records:
        is_human = "homo sapiens" in r.organism.lower()
        # Accept if library_strategy is RNA-seq or not specified
        is_rnaseq = (
            not r.library_strategy
            or "rna" in r.library_strategy.lower()
        )
        if not is_human or not is_rnaseq:
            continue
        if not include_scrna and _is_single_cell_sample(r):
            logger.debug(
                f"Single-cell filter rejected {r.gsm_id}: "
                f"library_source={r.library_source!r}"
            )
            continue
        filtered.append(r)
    return filtered


def _get_first(metadata: dict, key: str, default: str = "") -> str:
    values = metadata.get(key, [])
    if isinstance(values, list) and values:
        return str(values[0])
    if isinstance(values, str):
        return values
    return default
