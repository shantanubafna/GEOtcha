"""Shared test fixtures for GEOtcha."""

from __future__ import annotations

from pathlib import Path

import pytest

from geotcha.config import Settings
from geotcha.models import GSERecord, GSMRecord


@pytest.fixture
def tmp_output(tmp_path: Path) -> Path:
    """Temporary output directory."""
    out = tmp_path / "output"
    out.mkdir()
    return out


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    """Settings configured for testing."""
    return Settings(
        output_dir=tmp_path / "output",
        cache_dir=tmp_path / "cache",
        data_dir=tmp_path / "data",
    )


@pytest.fixture
def sample_gsm() -> GSMRecord:
    """A sample GSM record for testing."""
    return GSMRecord(
        gsm_id="GSM1234567",
        gse_id="GSE12345",
        title="RNA-seq of colon biopsy, UC patient, responder",
        source_name="colon biopsy",
        organism="Homo sapiens",
        molecule="total RNA",
        platform_id="GPL20301",
        instrument="Illumina HiSeq 2500",
        library_strategy="RNA-Seq",
        library_source="transcriptomic",
        characteristics={
            "tissue": "colon",
            "disease": "ulcerative colitis",
            "gender": "male",
            "age": "45 years",
            "treatment": "infliximab 5mg/kg",
            "timepoint": "week 8",
            "response": "responder",
        },
        tissue="colon",
        cell_type=None,
        disease="ulcerative colitis",
        disease_status="diseased",
        gender="male",
        age="45 years",
        treatment="infliximab 5mg/kg",
        timepoint="week 8",
        responder_status="responder",
        description="Colon biopsy from UC patient",
    )


@pytest.fixture
def sample_gse(sample_gsm: GSMRecord) -> GSERecord:
    """A sample GSE record for testing."""
    return GSERecord(
        gse_id="GSE12345",
        title="Transcriptomic analysis of ulcerative colitis",
        summary="RNA-seq analysis of colon biopsies from UC patients treated with infliximab",
        overall_design="Colon biopsies from UC patients at baseline and week 8",
        organism=["Homo sapiens"],
        experiment_type=["Expression profiling by high throughput sequencing"],
        platform=["GPL20301"],
        total_samples=24,
        human_rnaseq_samples=24,
        pubmed_ids=["12345678"],
        gse_url="https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE12345",
        tissue="colon",
        disease="ulcerative colitis",
        treatment="infliximab",
        timepoint="week 8",
        has_responder_info=True,
        num_responders=1,
        num_non_responders=0,
        samples=[sample_gsm],
    )
