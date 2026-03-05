"""CSV/TSV output generation."""

from __future__ import annotations

import csv
import logging
from collections.abc import Callable, Generator
from contextlib import contextmanager
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

GSE_PROVENANCE_FIELDS = [
    "tissue_source", "tissue_confidence", "tissue_ontology_id",
    "disease_source", "disease_confidence", "disease_ontology_id",
    "treatment_source", "treatment_confidence", "treatment_ontology_id",
    "timepoint_source", "timepoint_confidence", "timepoint_ontology_id",
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

GSM_PROVENANCE_FIELDS = [
    "tissue_source", "tissue_confidence", "tissue_ontology_id",
    "cell_type_source", "cell_type_confidence", "cell_type_ontology_id",
    "disease_source", "disease_confidence", "disease_ontology_id",
    "gender_source", "gender_confidence", "gender_ontology_id",
    "age_source", "age_confidence", "age_ontology_id",
    "treatment_source", "treatment_confidence", "treatment_ontology_id",
    "timepoint_source", "timepoint_confidence", "timepoint_ontology_id",
]

REVIEW_QUEUE_FIELDS = [
    "gsm_id", "gse_id", "field_name", "raw_value",
    "harmonized_value", "confidence", "source",
]


def _get_delimiter(fmt: str) -> str:
    return "\t" if fmt == "tsv" else ","


def _get_extension(fmt: str) -> str:
    if fmt == "tsv":
        return ".tsv"
    if fmt == "parquet":
        return ".parquet"
    return ".csv"


def _build_gse_fields(harmonized: bool) -> list[str]:
    """Build the GSE field list, including provenance when harmonized."""
    fields = GSE_FIELDS[:]
    if harmonized:
        fields.extend(GSE_HARMONIZED_EXTRA_FIELDS)
        fields.extend(GSE_PROVENANCE_FIELDS)
    return fields


def _build_gsm_fields(harmonized: bool) -> list[str]:
    """Build the GSM field list, including provenance when harmonized."""
    fields = GSM_FIELDS[:]
    if harmonized:
        fields.extend(GSM_HARMONIZED_EXTRA_FIELDS)
        fields.extend(GSM_PROVENANCE_FIELDS)
    return fields


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
        for field in GSE_PROVENANCE_FIELDS:
            row[field] = getattr(record, field, None) or ""
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
        for field in GSM_PROVENANCE_FIELDS:
            row[field] = getattr(record, field, None) or ""
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

    fields = _build_gse_fields(harmonized)
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

    fields = _build_gse_fields(harmonized)
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

    fields = _build_gsm_fields(harmonized)
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


@contextmanager
def open_gse_summary_writer(
    output_dir: Path,
    fmt: str = "csv",
    harmonized: bool = False,
) -> Generator[Callable[[GSERecord], None], None, None]:
    """Context manager that opens the GSE summary file and yields a row-writer callable.

    The yielded callable accepts a GSERecord and immediately writes + flushes the row,
    enabling streaming output as records complete rather than buffering all in memory.

    Usage::

        with open_gse_summary_writer(output_dir, fmt, harmonized) as write_row:
            for record in records:
                write_row(record)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    ext = _get_extension(fmt)
    filepath = output_dir / f"gse_summary{ext}"

    fields = _build_gse_fields(harmonized)
    delimiter = _get_delimiter(fmt)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter=delimiter, extrasaction="ignore")
        writer.writeheader()

        def write_row(record: GSERecord) -> None:
            writer.writerow(gse_to_row(record, harmonized))
            f.flush()

        yield write_row

    logger.info(f"Closed streaming GSE summary writer: {filepath}")


def write_review_queue(
    records: list[GSERecord],
    output_dir: Path,
    fmt: str = "csv",
    confidence_threshold: float = 0.65,
) -> Path | None:
    """Write a review queue CSV of low-confidence harmonized fields.

    Returns the file path, or None if no rows need review.
    """
    rows: list[dict] = []

    gse_prov_fields = ["tissue", "disease", "treatment", "timepoint"]
    gsm_prov_fields = [
        "tissue", "cell_type", "disease", "gender", "age", "treatment", "timepoint",
    ]

    for record in records:
        # GSE-level provenance
        for field in gse_prov_fields:
            confidence = getattr(record, f"{field}_confidence", None)
            if confidence is not None and confidence < confidence_threshold:
                rows.append({
                    "gsm_id": "",
                    "gse_id": record.gse_id,
                    "field_name": field,
                    "raw_value": getattr(record, field, "") or "",
                    "harmonized_value": getattr(record, f"{field}_harmonized", "") or "",
                    "confidence": confidence,
                    "source": getattr(record, f"{field}_source", "") or "",
                })

        # GSM-level provenance
        for sample in record.samples:
            for field in gsm_prov_fields:
                confidence = getattr(sample, f"{field}_confidence", None)
                if confidence is not None and confidence < confidence_threshold:
                    rows.append({
                        "gsm_id": sample.gsm_id,
                        "gse_id": sample.gse_id,
                        "field_name": field,
                        "raw_value": getattr(sample, field, "") or "",
                        "harmonized_value": getattr(sample, f"{field}_harmonized", "") or "",
                        "confidence": confidence,
                        "source": getattr(sample, f"{field}_source", "") or "",
                    })

    if not rows:
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    ext = _get_extension(fmt)
    filepath = output_dir / f"review_queue{ext}"
    delimiter = _get_delimiter(fmt)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=REVIEW_QUEUE_FIELDS, delimiter=delimiter)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    logger.info(f"Wrote review queue: {filepath} ({len(rows)} rows)")
    return filepath


def write_gse_parquet(
    records: list[GSERecord],
    output_dir: Path,
    harmonized: bool = False,
) -> Path:
    """Write GSE summary as a Parquet file (requires pyarrow)."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    rows = [gse_to_row(r, harmonized) for r in records]
    table = pa.Table.from_pylist(rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / "gse_summary.parquet"
    pq.write_table(table, filepath)
    logger.info(f"Wrote GSE parquet: {filepath} ({len(records)} records)")
    return filepath


def write_gsm_parquet(
    gse_record: GSERecord,
    output_dir: Path,
    harmonized: bool = False,
) -> Path:
    """Write per-GSE GSM samples as a Parquet file (requires pyarrow)."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    rows = [_gsm_to_row(s, harmonized) for s in gse_record.samples]
    table = pa.Table.from_pylist(rows)
    gsm_dir = output_dir / "gsm"
    gsm_dir.mkdir(parents=True, exist_ok=True)
    filepath = gsm_dir / f"{gse_record.gse_id}_samples.parquet"
    pq.write_table(table, filepath)
    logger.info(f"Wrote GSM parquet: {filepath} ({len(gse_record.samples)} samples)")
    return filepath


def write_all(
    records: list[GSERecord],
    output_dir: Path,
    fmt: str = "csv",
    harmonized: bool = False,
) -> dict[str, Path]:
    """Write all output files: GSE summary + per-GSE GSM files + review queue."""
    paths: dict[str, Path] = {}

    if fmt == "parquet":
        paths["gse_summary"] = write_gse_parquet(records, output_dir, harmonized)
        for record in records:
            if record.samples:
                paths[record.gse_id] = write_gsm_parquet(record, output_dir, harmonized)
    else:
        paths["gse_summary"] = write_gse_summary(records, output_dir, fmt, harmonized)
        for record in records:
            if record.samples:
                path = write_gsm_file(record, output_dir, fmt, harmonized)
                paths[record.gse_id] = path

    # Review queue always CSV (human-readable)
    if harmonized:
        review_path = write_review_queue(records, output_dir, "csv")
        if review_path:
            paths["review_queue"] = review_path

    return paths
