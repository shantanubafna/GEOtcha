"""Pydantic data models for GEO metadata."""

from __future__ import annotations

from typing import Optional

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
    tissue: Optional[str] = Field(default=None)
    cell_type: Optional[str] = Field(default=None)
    disease: Optional[str] = Field(default=None)
    disease_status: Optional[str] = Field(default=None, description="e.g., healthy, diseased")
    gender: Optional[str] = Field(default=None)
    age: Optional[str] = Field(default=None)
    treatment: Optional[str] = Field(default=None)
    timepoint: Optional[str] = Field(default=None)
    responder_status: Optional[str] = Field(
        default=None,
        description="responder, non-responder, partial responder, or None",
    )
    sample_acquisition: Optional[str] = Field(default=None, description="e.g., biopsy, blood draw")
    clinical_severity: Optional[str] = Field(default=None, description="Clinical severity endpoint")
    description: str = Field(default="")

    # Harmonized fields (populated after harmonization)
    tissue_harmonized: Optional[str] = Field(default=None)
    cell_type_harmonized: Optional[str] = Field(default=None)
    disease_harmonized: Optional[str] = Field(default=None)
    gender_harmonized: Optional[str] = Field(default=None)
    age_harmonized: Optional[str] = Field(default=None)
    treatment_harmonized: Optional[str] = Field(default=None)
    timepoint_harmonized: Optional[str] = Field(default=None)


class GSERecord(BaseModel):
    """Series-level metadata from a GEO GSE entry."""

    gse_id: str = Field(description="GSE accession ID")
    title: str = Field(default="")
    summary: str = Field(default="")
    overall_design: str = Field(default="")
    organism: list[str] = Field(default_factory=list)
    experiment_type: list[str] = Field(default_factory=list, description="e.g., Expression profiling by high throughput sequencing")
    platform: list[str] = Field(default_factory=list, description="GPL IDs")
    total_samples: int = Field(default=0)
    human_rnaseq_samples: int = Field(default=0, description="Count of human RNA-seq samples")
    pubmed_ids: list[str] = Field(default_factory=list)
    gse_url: str = Field(default="")

    # Extracted from summary/overall_design/characteristics
    tissue: Optional[str] = Field(default=None)
    cell_type: Optional[str] = Field(default=None)
    disease: Optional[str] = Field(default=None)
    disease_status: Optional[str] = Field(default=None)
    treatment: Optional[str] = Field(default=None)
    timepoint: Optional[str] = Field(default=None)
    gender: Optional[str] = Field(default=None)
    age: Optional[str] = Field(default=None)
    sample_acquisition: Optional[str] = Field(default=None)
    clinical_severity: Optional[str] = Field(default=None)
    has_responder_info: bool = Field(default=False, description="Whether any samples have responder/non-responder status")
    num_responders: int = Field(default=0, description="Count of responder samples")
    num_non_responders: int = Field(default=0, description="Count of non-responder samples")

    # Sample records
    samples: list[GSMRecord] = Field(default_factory=list, exclude=True)

    # Publication info
    publication_title: Optional[str] = Field(default=None)
    publication_authors: Optional[str] = Field(default=None)
    publication_url: Optional[str] = Field(default=None)

    # Harmonized fields
    tissue_harmonized: Optional[str] = Field(default=None)
    disease_harmonized: Optional[str] = Field(default=None)
    treatment_harmonized: Optional[str] = Field(default=None)
    timepoint_harmonized: Optional[str] = Field(default=None)
