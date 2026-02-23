"""CSV/TSV output generation."""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from geotcha.export.formatters import format_pubmed_ids, gse_url
from geotcha.models import GSERecord, GSMRecord

logger = logging.getLogger(__name__)

# GSE summary fields for output
GSE_FIELDS = [
    "gse_id",
    "gse_url",
    "title",
    "organism",
    "experiment_type",
    "platform",
    "total_samples",
    "human_rnaseq_samples",
    "pubmed_links",
    "tissue",
    "cell_type",
    "disease",
    "disease_status",
    "treatment",
    "timepoint",
    "gender",
    "age",
    "sample_acquisition",
    "clinical_severity",
    "has_responder_info",
    "num_responders",
    "num_non_responders",
    "summary",
    "overall_design",
]

GSE_HARMONIZED_EXTRA_FIELDS = [
    "tissue_harmonized",
    "disease_harmonized",
    "treatment_harmonized",
    "timepoint_harmonized",
]

# GSM fields for per-GSE sample files
GSM_FIELDS = [
    "gsm_id",
    "gse_id",
    "title",
    "source_name",
    "organism",
    "platform_id",
    "instrument",
    "library_strategy",
    "tissue",
    "cell_type",
    "disease",
    "disease_status",
    "gender",
    "age",
    "treatment",
    "timepoint",
    "responder_status",
    "sample_acquisition",
    "clinical_severity",
    "description",
]

GSM_HARMONIZED_EXTRA_FIELDS = [
    "tissue_harmonized",
    "cell_type_harmonized",
    "disease_harmonized",
    "gender_harmonized",
    "age_harmonized",
    "treatment_harmonized",
    "timepoint_harmonized",
]


def _get_delimiter(fmt: str) -> str:
    return "\t" if fmt == "tsv" else ","


def _get_extension(fmt: str) -> str:
    return ".tsv" if fmt == "tsv" else ".csv"


def gse_to_row(record: GSERecord, harmonized: bool = False) -> dict:
    """Convert a GSERecord to a flat dict for CSV output."""
    row = {
        "gse_id": record.gse_id,
        "gse_url": gse_url(record.gse_id),
        "title": record.title,
        "organism": "; ".join(record.organism),
        "experiment_type": "; ".join(record.experiment_type),
        "platform": "; ".join(record.platform),
        "total_samples": record.total_samples,
        "human_rnaseq_samples": record.human_rnaseq_samples,
        "pubmed_links": format_pubmed_ids(record.pubmed_ids),
        "tissue": record.tissue or "",
        "cell_type": record.cell_type or "",
        "disease": record.disease or "",
        "disease_status": record.disease_status or "",
        "treatment": record.treatment or "",
        "timepoint": record.timepoint or "",
        "gender": record.gender or "",
        "age": record.age or "",
        "sample_acquisition": record.sample_acquisition or "",
        "clinical_severity": record.clinical_severity or "",
        "has_responder_info": record.has_responder_info,
        "num_responders": record.num_responders,
        "num_non_responders": record.num_non_responders,
        "summary": record.summary,
        "overall_design": record.overall_design,
    }
    if harmonized:
        row["tissue_harmonized"] = record.tissue_harmonized or ""
        row["disease_harmonized"] = record.disease_harmonized or ""
        row["treatment_harmonized"] = record.treatment_harmonized or ""
        row["timepoint_harmonized"] = record.timepoint_harmonized or ""
    return row


def _gsm_to_row(record: GSMRecord, harmonized: bool = False) -> dict:
    """Convert a GSMRecord to a flat dict for CSV output."""
    row = {
        "gsm_id": record.gsm_id,
        "gse_id": record.gse_id,
        "title": record.title,
        "source_name": record.source_name,
        "organism": record.organism,
        "platform_id": record.platform_id,
        "instrument": record.instrument,
        "library_strategy": record.library_strategy,
        "tissue": record.tissue or "",
        "cell_type": record.cell_type or "",
        "disease": record.disease or "",
        "disease_status": record.disease_status or "",
        "gender": record.gender or "",
        "age": record.age or "",
        "treatment": record.treatment or "",
        "timepoint": record.timepoint or "",
        "responder_status": record.responder_status or "",
        "sample_acquisition": record.sample_acquisition or "",
        "clinical_severity": record.clinical_severity or "",
        "description": record.description,
    }
    if harmonized:
        row["tissue_harmonized"] = record.tissue_harmonized or ""
        row["cell_type_harmonized"] = record.cell_type_harmonized or ""
        row["disease_harmonized"] = record.disease_harmonized or ""
        row["gender_harmonized"] = record.gender_harmonized or ""
        row["age_harmonized"] = record.age_harmonized or ""
        row["treatment_harmonized"] = record.treatment_harmonized or ""
        row["timepoint_harmonized"] = record.timepoint_harmonized or ""
    return row


def write_gse_summary(
    records: list[GSERecord],
    output_dir: Path,
    fmt: str = "csv",
    harmonized: bool = False,
) -> Path:
    """Write GSE summary file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    ext = _get_extension(fmt)
    filename = f"gse_summary{ext}"
    filepath = output_dir / filename

    fields = GSE_FIELDS[:]
    if harmonized:
        fields.extend(GSE_HARMONIZED_EXTRA_FIELDS)

    delimiter = _get_delimiter(fmt)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter=delimiter, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            writer.writerow(gse_to_row(record, harmonized))

    logger.info(f"Wrote GSE summary: {filepath} ({len(records)} records)")
    return filepath


def read_gse_summary(output_dir: Path, fmt: str = "csv") -> list[dict]:
    """Read an existing GSE summary file as a list of raw dict rows."""
    ext = _get_extension(fmt)
    filepath = output_dir / f"gse_summary{ext}"
    if not filepath.exists():
        return []
    delimiter = _get_delimiter(fmt)
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        return list(reader)


def write_gse_summary_rows(
    rows: list[dict],
    output_dir: Path,
    fmt: str = "csv",
    harmonized: bool = False,
) -> Path:
    """Write pre-formatted GSE summary dict rows (used by resume merge)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    ext = _get_extension(fmt)
    filepath = output_dir / f"gse_summary{ext}"

    fields = GSE_FIELDS[:]
    if harmonized:
        fields.extend(GSE_HARMONIZED_EXTRA_FIELDS)

    delimiter = _get_delimiter(fmt)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter=delimiter, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    logger.info(f"Wrote GSE summary (merged): {filepath} ({len(rows)} rows)")
    return filepath


def write_gsm_file(
    gse_record: GSERecord,
    output_dir: Path,
    fmt: str = "csv",
    harmonized: bool = False,
) -> Path:
    """Write per-GSE GSM sample file."""
    gsm_dir = output_dir / "gsm"
    gsm_dir.mkdir(parents=True, exist_ok=True)
    ext = _get_extension(fmt)
    filepath = gsm_dir / f"{gse_record.gse_id}_samples{ext}"

    fields = GSM_FIELDS[:]
    if harmonized:
        fields.extend(GSM_HARMONIZED_EXTRA_FIELDS)

    delimiter = _get_delimiter(fmt)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter=delimiter, extrasaction="ignore")
        writer.writeheader()
        for sample in gse_record.samples:
            writer.writerow(_gsm_to_row(sample, harmonized))

    logger.info(
        f"Wrote GSM file: {filepath} ({len(gse_record.samples)} samples)"
    )
    return filepath


def write_all(
    records: list[GSERecord],
    output_dir: Path,
    fmt: str = "csv",
    harmonized: bool = False,
) -> dict[str, Path]:
    """Write all output files: GSE summary + per-GSE GSM files."""
    paths: dict[str, Path] = {}

    paths["gse_summary"] = write_gse_summary(records, output_dir, fmt, harmonized)

    for record in records:
        if record.samples:
            path = write_gsm_file(record, output_dir, fmt, harmonized)
            paths[record.gse_id] = path

    return paths
