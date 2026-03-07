"""Tests for field extraction utilities and GSM-level filtering."""

from geotcha.extract.fields import (
    detect_responder_status,
    detect_sample_acquisition,
    detect_tissue,
    detect_treatment,
    extract_age_from_characteristics,
    extract_disease_from_characteristics,
    extract_disease_status_from_characteristics,
    extract_gender_from_characteristics,
    extract_responder_from_characteristics,
    extract_timepoint,
    extract_timepoint_from_characteristics,
    extract_tissue_from_characteristics,
    extract_treatment_from_characteristics,
    parse_characteristics,
    parse_source_name,
)
from geotcha.extract.gsm_parser import _filter_human_rnaseq, _is_single_cell_sample
from geotcha.models import GSMRecord


class TestDetectResponderStatus:
    def test_responder(self):
        assert detect_responder_status("patient is a responder") == "responder"

    def test_non_responder(self):
        assert detect_responder_status("non-responder to treatment") == "non-responder"

    def test_partial_responder(self):
        assert detect_responder_status("partial responder") == "partial responder"

    def test_no_status(self):
        assert detect_responder_status("normal healthy control") is None

    def test_remission(self):
        assert detect_responder_status("patient in remission") == "responder"

    def test_refractory(self):
        assert detect_responder_status("refractory to treatment") == "non-responder"

    def test_primary_response_responder(self):
        assert detect_responder_status("primary response: Responder") == "responder"

    def test_primary_response_non_responder(self):
        assert detect_responder_status("primary response: Non-responder") == "non-responder"


class TestExtractResponderFromCharacteristics:
    def test_response_key(self):
        chars = {"response": "Responder"}
        assert extract_responder_from_characteristics(chars) == "responder"

    def test_primary_response_key(self):
        chars = {"primary response": "Non-responder"}
        assert extract_responder_from_characteristics(chars) == "non-responder"

    def test_no_responder_key(self):
        chars = {"tissue": "blood"}
        assert extract_responder_from_characteristics(chars) is None


class TestExtractTimepoint:
    def test_week(self):
        assert extract_timepoint("week 8 post treatment") == "W8"

    def test_day(self):
        assert extract_timepoint("day 7") == "D7"

    def test_hour(self):
        assert extract_timepoint("24h stimulation") == "H24"

    def test_baseline(self):
        assert extract_timepoint("baseline sample") == "baseline"

    def test_before_treatment(self):
        assert extract_timepoint("before initiation of treatment") == "baseline"

    def test_no_timepoint(self):
        assert extract_timepoint("normal colon biopsy") is None

    def test_zero_weeks(self):
        assert extract_timepoint("weeks fron start of treatment: 0") == "baseline"

    def test_two_weeks(self):
        assert extract_timepoint("weeks fron start of treatment: 2") == "W2"


class TestExtractTimepointFromCharacteristics:
    def test_weeks_key(self):
        chars = {"weeks fron start of treatment": "2"}
        assert extract_timepoint_from_characteristics(chars) == "W2"

    def test_zero_is_baseline(self):
        chars = {"weeks fron start of treatment": "0"}
        assert extract_timepoint_from_characteristics(chars) == "baseline"

    def test_timepoint_key(self):
        chars = {"timepoint": "week 8"}
        assert extract_timepoint_from_characteristics(chars) == "W8"

    def test_time_before(self):
        chars = {"time": "before initiation of treatment"}
        assert extract_timepoint_from_characteristics(chars) == "baseline"


class TestDetectTissue:
    def test_colon(self):
        assert detect_tissue("colonic biopsy") == "colon"

    def test_blood(self):
        assert detect_tissue("peripheral blood sample") == "peripheral blood"

    def test_pbmc(self):
        assert detect_tissue("pbmc isolation") == "PBMC"

    def test_no_tissue(self):
        assert detect_tissue("some random text") is None


class TestDetectTreatment:
    def test_drug_name(self):
        result = detect_treatment("treated with infliximab 5mg/kg")
        assert result == "infliximab"

    def test_anti_tnf(self):
        result = detect_treatment("anti-TNF therapy was administered")
        assert result == "anti-tnf"

    def test_no_treatment(self):
        assert detect_treatment("normal healthy subject") is None


class TestExtractTreatmentFromCharacteristics:
    def test_anti_tnf_key(self):
        chars = {"anti-tnf": "Infliximab"}
        assert extract_treatment_from_characteristics(chars) == "Infliximab"

    def test_treatment_key(self):
        chars = {"treatment": "Anti-TNF"}
        assert extract_treatment_from_characteristics(chars) == "Anti-TNF"

    def test_drug_in_value(self):
        chars = {"agent": "adalimumab 40mg"}
        assert extract_treatment_from_characteristics(chars) == "adalimumab 40mg"

    def test_no_treatment(self):
        chars = {"tissue": "blood", "gender": "male"}
        assert extract_treatment_from_characteristics(chars) is None


class TestDetectSampleAcquisition:
    def test_biopsy(self):
        assert detect_sample_acquisition("endoscopic biopsy of colon") == "endoscopic biopsy"

    def test_blood_draw(self):
        assert detect_sample_acquisition("blood draw from patient") == "blood draw"

    def test_no_acquisition(self):
        assert detect_sample_acquisition("some random text") is None


class TestParseCharacteristics:
    def test_colon_separator(self):
        chars = parse_characteristics(["tissue: colon", "gender: male"])
        assert chars["tissue"] == "colon"
        assert chars["gender"] == "male"

    def test_equals_separator(self):
        chars = parse_characteristics(["tissue=colon"])
        assert chars["tissue"] == "colon"

    def test_no_separator(self):
        chars = parse_characteristics(["some value"])
        assert "field_0" in chars

    def test_real_geo_characteristics(self):
        """Test with real characteristics from GSE159034."""
        chars = parse_characteristics([
            "tissue: Blood",
            "primary response: Responder",
            "weeks fron start of treatment: 0",
            "anti-tnf: Infliximab",
            "disease state: pediatric inflammatory bowel disease",
        ])
        assert chars["tissue"] == "Blood"
        assert chars["primary response"] == "Responder"
        assert chars["weeks fron start of treatment"] == "0"
        assert chars["anti-tnf"] == "Infliximab"
        assert chars["disease state"] == "pediatric inflammatory bowel disease"


class TestExtractFromCharacteristics:
    def test_gender(self):
        chars = {"gender": "male", "age": "45"}
        assert extract_gender_from_characteristics(chars) == "male"

    def test_gender_sex_key(self):
        chars = {"sex": "female"}
        assert extract_gender_from_characteristics(chars) == "female"

    def test_age(self):
        chars = {"age": "45 years"}
        assert extract_age_from_characteristics(chars) == "45 years"

    def test_disease(self):
        chars = {"disease": "ulcerative colitis"}
        assert extract_disease_from_characteristics(chars) == "ulcerative colitis"


# --- GSM-level single-cell filtering tests ---


def _make_gsm(
    library_source: str = "transcriptomic",
    organism: str = "Homo sapiens",
    library_strategy: str = "RNA-Seq",
) -> GSMRecord:
    """Helper to create a minimal GSMRecord for testing."""
    return GSMRecord(
        gsm_id="GSM000001",
        gse_id="GSE000001",
        title="test sample",
        source_name="test",
        organism=organism,
        library_strategy=library_strategy,
        library_source=library_source,
    )


class TestIsSingleCellSample:
    def test_transcriptomic_single_cell(self):
        """library_source 'transcriptomic single cell' should be detected."""
        gsm = _make_gsm(library_source="transcriptomic single cell")
        assert _is_single_cell_sample(gsm) is True

    def test_transcriptomic_passes(self):
        """Standard 'transcriptomic' library_source should NOT be flagged."""
        gsm = _make_gsm(library_source="transcriptomic")
        assert _is_single_cell_sample(gsm) is False

    def test_empty_library_source(self):
        """Empty/missing library_source should NOT be flagged."""
        gsm = _make_gsm(library_source="")
        assert _is_single_cell_sample(gsm) is False


class TestFilterHumanRnaseqSingleCell:
    def test_single_cell_filtered_by_default(self):
        """Single-cell samples should be excluded when include_scrna=False."""
        records = [
            _make_gsm(library_source="transcriptomic single cell"),
            _make_gsm(library_source="transcriptomic"),
        ]
        filtered = _filter_human_rnaseq(records, include_scrna=False)
        assert len(filtered) == 1
        assert filtered[0].library_source == "transcriptomic"

    def test_single_cell_included_with_flag(self):
        """Single-cell samples should pass when include_scrna=True."""
        records = [
            _make_gsm(library_source="transcriptomic single cell"),
            _make_gsm(library_source="transcriptomic"),
        ]
        filtered = _filter_human_rnaseq(records, include_scrna=True)
        assert len(filtered) == 2

    def test_mixed_gse_keeps_bulk_only(self):
        """In a mixed GSE, only bulk samples survive when include_scrna=False."""
        records = [
            _make_gsm(library_source="transcriptomic single cell"),
            _make_gsm(library_source="transcriptomic single cell"),
            _make_gsm(library_source="transcriptomic"),
        ]
        filtered = _filter_human_rnaseq(records, include_scrna=False)
        assert len(filtered) == 1
        assert filtered[0].library_source == "transcriptomic"


class TestExtractDiseaseStatus:
    def test_healthy_vocab(self):
        chars = {"disease state": "healthy"}
        status, confidence = extract_disease_status_from_characteristics(chars)
        assert status == "healthy"
        assert confidence == 1.0

    def test_normal_maps_to_healthy(self):
        chars = {"disease status": "normal"}
        status, confidence = extract_disease_status_from_characteristics(chars)
        assert status == "healthy"
        assert confidence == 1.0

    def test_control_maps_to_healthy(self):
        chars = {"condition": "control"}
        status, confidence = extract_disease_status_from_characteristics(chars)
        assert status == "healthy"
        assert confidence == 1.0

    def test_diseased_vocab(self):
        chars = {"disease state": "diseased"}
        status, confidence = extract_disease_status_from_characteristics(chars)
        assert status == "diseased"
        assert confidence == 1.0

    def test_active_status(self):
        chars = {"disease state": "active"}
        status, confidence = extract_disease_status_from_characteristics(chars)
        assert status == "active"
        assert confidence == 1.0

    def test_remission_status(self):
        chars = {"disease state": "remission"}
        status, confidence = extract_disease_status_from_characteristics(chars)
        assert status == "remission"
        assert confidence == 1.0

    def test_raw_fallback(self):
        chars = {"disease state": "pediatric inflammatory bowel disease"}
        status, confidence = extract_disease_status_from_characteristics(chars)
        assert status == "pediatric inflammatory bowel disease"
        assert confidence == 0.70

    def test_no_key(self):
        chars = {"tissue": "colon"}
        status, confidence = extract_disease_status_from_characteristics(chars)
        assert status is None
        assert confidence == 0.0


class TestExtractTissueFromCharacteristics:
    def test_tissue_key(self):
        chars = {"tissue": "colon"}
        assert extract_tissue_from_characteristics(chars) == "colon"

    def test_tissue_type_key(self):
        chars = {"tissue type": "liver biopsy"}
        assert extract_tissue_from_characteristics(chars) == "liver biopsy"

    def test_organ_key(self):
        chars = {"organ": "lung"}
        assert extract_tissue_from_characteristics(chars) == "lung"

    def test_body_site_key(self):
        chars = {"body site": "sigmoid colon"}
        assert extract_tissue_from_characteristics(chars) == "sigmoid colon"

    def test_no_tissue_key(self):
        chars = {"disease": "UC", "gender": "male"}
        assert extract_tissue_from_characteristics(chars) is None


class TestExpandedDiseaseKeys:
    def test_disease_type_key(self):
        chars = {"disease type": "melanoma"}
        assert extract_disease_from_characteristics(chars) == "melanoma"

    def test_tumor_type_key(self):
        chars = {"tumor type": "glioblastoma"}
        assert extract_disease_from_characteristics(chars) == "glioblastoma"

    def test_cancer_type_key(self):
        chars = {"cancer type": "breast cancer"}
        assert extract_disease_from_characteristics(chars) == "breast cancer"

    def test_clinical_diagnosis_key(self):
        chars = {"clinical diagnosis": "Crohn's disease"}
        assert extract_disease_from_characteristics(chars) == "Crohn's disease"

    def test_phenotype_key(self):
        chars = {"phenotype": "type 2 diabetes"}
        assert extract_disease_from_characteristics(chars) == "type 2 diabetes"


class TestExpandedTreatmentKeys:
    def test_intervention_key(self):
        chars = {"intervention": "pembrolizumab"}
        assert extract_treatment_from_characteristics(chars) == "pembrolizumab"

    def test_drug_name_key(self):
        chars = {"drug name": "methotrexate 15mg"}
        assert extract_treatment_from_characteristics(chars) == "methotrexate 15mg"

    def test_exposure_key(self):
        chars = {"exposure": "LPS 100ng/ml"}
        assert extract_treatment_from_characteristics(chars) == "LPS 100ng/ml"


class TestParseSourceName:
    def test_tissue_only(self):
        result = parse_source_name("colon")
        assert result.get("tissue") == "colon"

    def test_multi_segment(self):
        result = parse_source_name("colon, ulcerative colitis, male")
        assert result.get("tissue") == "colon"
        assert result.get("disease") == "ulcerative colitis"
        assert result.get("gender") == "male"

    def test_age_detection(self):
        result = parse_source_name("liver, 45y")
        assert result.get("tissue") is not None
        assert result.get("age") == "45"

    def test_semicolon_delimiter(self):
        result = parse_source_name("lung; breast cancer")
        assert result.get("tissue") == "lung"
        assert result.get("disease") is not None

    def test_empty_string(self):
        assert parse_source_name("") == {}

    def test_none(self):
        assert parse_source_name(None) == {}

    def test_treatment_segment(self):
        result = parse_source_name("blood, infliximab")
        assert result.get("tissue") is not None
        assert result.get("treatment") == "infliximab"

    def test_cell_type_segment(self):
        result = parse_source_name("T cell, blood")
        assert result.get("cell_type") is not None

    def test_pipe_delimiter(self):
        result = parse_source_name("colon | male | 30y")
        assert result.get("tissue") == "colon"
        assert result.get("gender") == "male"
        assert result.get("age") == "30"
