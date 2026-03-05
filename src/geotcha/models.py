"""Pydantic data models for GEO metadata."""

from __future__ import annotations

from pydantic import BaseModel, Field


class GSMRecord(BaseModel):
    """Sample-level metadata from a GEO GSM entry."""

    gsm_id: str = Field(description="GSM accession ID")
    gse_id: str = Field(description="Parent GSE accession ID")
    title: str = Field(default="")
    source_name: str = Field(default="", description="Source name (tissue/cell)")
    organism: str = Field(default="")
    molecule: str = Field(default="", description="e.g., total RNA")
    platform_id: str = Field(default="", description="GPL platform ID")
    instrument: str = Field(default="", description="Sequencing instrument")
    library_strategy: str = Field(default="", description="e.g., RNA-Seq")
    library_source: str = Field(default="", description="e.g., transcriptomic")
    characteristics: dict[str, str] = Field(
        default_factory=dict,
        description="Parsed characteristics_ch1 key-value pairs",
    )

    # Extracted fields
    tissue: str | None = Field(default=None)
    cell_type: str | None = Field(default=None)
    disease: str | None = Field(default=None)
    disease_status: str | None = Field(default=None, description="e.g., healthy, diseased")
    gender: str | None = Field(default=None)
    age: str | None = Field(default=None)
    treatment: str | None = Field(default=None)
    timepoint: str | None = Field(default=None)
    responder_status: str | None = Field(
        default=None,
        description="responder, non-responder, partial responder, or None",
    )
    sample_acquisition: str | None = Field(default=None, description="e.g., biopsy, blood draw")
    clinical_severity: str | None = Field(default=None, description="Clinical severity endpoint")
    description: str = Field(default="")

    needs_review: bool = Field(default=False, description="Flagged for manual review by ML")

    # Harmonized fields (populated after harmonization)
    tissue_harmonized: str | None = Field(default=None)
    cell_type_harmonized: str | None = Field(default=None)
    disease_harmonized: str | None = Field(default=None)
    gender_harmonized: str | None = Field(default=None)
    age_harmonized: str | None = Field(default=None)
    treatment_harmonized: str | None = Field(default=None)
    timepoint_harmonized: str | None = Field(default=None)

    # Provenance fields (source, confidence, ontology_id per harmonized field)
    tissue_source: str | None = Field(default=None)
    tissue_confidence: float | None = Field(default=None)
    tissue_ontology_id: str | None = Field(default=None)
    cell_type_source: str | None = Field(default=None)
    cell_type_confidence: float | None = Field(default=None)
    cell_type_ontology_id: str | None = Field(default=None)
    disease_source: str | None = Field(default=None)
    disease_confidence: float | None = Field(default=None)
    disease_ontology_id: str | None = Field(default=None)
    gender_source: str | None = Field(default=None)
    gender_confidence: float | None = Field(default=None)
    gender_ontology_id: str | None = Field(default=None)
    age_source: str | None = Field(default=None)
    age_confidence: float | None = Field(default=None)
    age_ontology_id: str | None = Field(default=None)
    treatment_source: str | None = Field(default=None)
    treatment_confidence: float | None = Field(default=None)
    treatment_ontology_id: str | None = Field(default=None)
    timepoint_source: str | None = Field(default=None)
    timepoint_confidence: float | None = Field(default=None)
    timepoint_ontology_id: str | None = Field(default=None)


class GSERecord(BaseModel):
    """Series-level metadata from a GEO GSE entry."""

    gse_id: str = Field(description="GSE accession ID")
    title: str = Field(default="")
    summary: str = Field(default="")
    overall_design: str = Field(default="")
    organism: list[str] = Field(default_factory=list)
    experiment_type: list[str] = Field(
        default_factory=list,
        description="e.g., Expression profiling by high throughput sequencing",
    )
    platform: list[str] = Field(default_factory=list, description="GPL IDs")
    total_samples: int = Field(default=0)
    human_rnaseq_samples: int = Field(default=0, description="Count of human RNA-seq samples")
    pubmed_ids: list[str] = Field(default_factory=list)
    gse_url: str = Field(default="")

    # Extracted from summary/overall_design/characteristics
    tissue: str | None = Field(default=None)
    cell_type: str | None = Field(default=None)
    disease: str | None = Field(default=None)
    disease_status: str | None = Field(default=None)
    treatment: str | None = Field(default=None)
    timepoint: str | None = Field(default=None)
    gender: str | None = Field(default=None)
    age: str | None = Field(default=None)
    sample_acquisition: str | None = Field(default=None)
    clinical_severity: str | None = Field(default=None)
    has_responder_info: bool = Field(
        default=False,
        description="Whether any samples have responder/non-responder status",
    )
    num_responders: int = Field(default=0, description="Count of responder samples")
    num_non_responders: int = Field(default=0, description="Count of non-responder samples")

    needs_review: bool = Field(default=False, description="Flagged for manual review by ML")

    # Sample records
    samples: list[GSMRecord] = Field(default_factory=list, exclude=True)

    # Publication info
    publication_title: str | None = Field(default=None)
    publication_authors: str | None = Field(default=None)
    publication_url: str | None = Field(default=None)

    # Harmonized fields
    tissue_harmonized: str | None = Field(default=None)
    disease_harmonized: str | None = Field(default=None)
    treatment_harmonized: str | None = Field(default=None)
    timepoint_harmonized: str | None = Field(default=None)

    # Provenance fields (source, confidence, ontology_id per harmonized field)
    tissue_source: str | None = Field(default=None)
    tissue_confidence: float | None = Field(default=None)
    tissue_ontology_id: str | None = Field(default=None)
    disease_source: str | None = Field(default=None)
    disease_confidence: float | None = Field(default=None)
    disease_ontology_id: str | None = Field(default=None)
    treatment_source: str | None = Field(default=None)
    treatment_confidence: float | None = Field(default=None)
    treatment_ontology_id: str | None = Field(default=None)
    timepoint_source: str | None = Field(default=None)
    timepoint_confidence: float | None = Field(default=None)
    timepoint_ontology_id: str | None = Field(default=None)
