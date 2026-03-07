"""Tests for LLM-based harmonization with mocked API responses."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from geotcha.harmonize.llm import (
    HARMONIZATION_PROMPT,
    RELEVANCE_PROMPT,
    _call_llm,
    _get_llm_client,
    llm_check_relevance,
    llm_harmonize_fields,
    llm_harmonize_record,
)
from geotcha.models import GSERecord, GSMRecord

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def gse_with_samples():
    """GSE record with unharmonized tissue/disease and samples."""
    gsm = GSMRecord(
        gsm_id="GSM100",
        gse_id="GSE100",
        title="colon biopsy UC patient",
        tissue="sigmoid colon biopsy",
        disease="UC",
        gender="M",
    )
    return GSERecord(
        gse_id="GSE100",
        title="Transcriptomics of UC colon",
        summary="RNA-seq of sigmoid colon biopsies from UC patients",
        tissue="sigmoid colon",
        disease="UC",
        samples=[gsm],
    )


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI-style chat completion response."""
    def _make(content: str):
        resp = MagicMock()
        resp.choices = [MagicMock()]
        resp.choices[0].message.content = content
        return resp
    return _make


@pytest.fixture
def mock_anthropic_response():
    """Mock Anthropic messages.create response."""
    def _make(content: str):
        resp = MagicMock()
        resp.content = [MagicMock()]
        resp.content[0].text = content
        return resp
    return _make


# ---------------------------------------------------------------------------
# _get_llm_client
# ---------------------------------------------------------------------------

class TestGetLlmClient:
    def test_openai_client(self):
        mock_openai_mod = MagicMock()
        with patch.dict("sys.modules", {"openai": mock_openai_mod}):
            _get_llm_client("openai", api_key="sk-test")
            mock_openai_mod.OpenAI.assert_called_once_with(api_key="sk-test")

    def test_anthropic_client(self):
        mock_module = MagicMock()
        with patch.dict("sys.modules", {"anthropic": mock_module}):
            _get_llm_client("anthropic", api_key="sk-ant-test")
            mock_module.Anthropic.assert_called_once_with(api_key="sk-ant-test")

    def test_ollama_client(self):
        mock_openai_mod = MagicMock()
        with patch.dict("sys.modules", {"openai": mock_openai_mod}):
            _get_llm_client("ollama")
            mock_openai_mod.OpenAI.assert_called_once_with(
                base_url="http://localhost:11434/v1", api_key="ollama"
            )

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            _get_llm_client("gemini")


# ---------------------------------------------------------------------------
# _call_llm
# ---------------------------------------------------------------------------

class TestCallLlm:
    def test_openai_call(self, mock_openai_response):
        client = MagicMock()
        client.chat.completions.create.return_value = mock_openai_response(
            '{"tissue": {"value": "colon"}}'
        )
        result = _call_llm(client, "openai", "harmonize this", model="gpt-4o-mini")
        assert "colon" in result
        client.chat.completions.create.assert_called_once()
        call_kwargs = client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4o-mini"
        assert call_kwargs["messages"][0]["content"] == HARMONIZATION_PROMPT

    def test_anthropic_call(self, mock_anthropic_response):
        client = MagicMock()
        client.messages.create.return_value = mock_anthropic_response(
            '{"disease": {"value": "ulcerative colitis"}}'
        )
        result = _call_llm(client, "anthropic", "harmonize this")
        assert "ulcerative colitis" in result
        client.messages.create.assert_called_once()
        call_kwargs = client.messages.create.call_args[1]
        assert call_kwargs["system"] == HARMONIZATION_PROMPT
        assert call_kwargs["model"] == "claude-haiku-4-5-20251001"

    def test_openai_default_model(self, mock_openai_response):
        client = MagicMock()
        client.chat.completions.create.return_value = mock_openai_response("{}")
        _call_llm(client, "openai", "test")
        call_kwargs = client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4o-mini"

    def test_anthropic_default_model(self, mock_anthropic_response):
        client = MagicMock()
        client.messages.create.return_value = mock_anthropic_response("{}")
        _call_llm(client, "anthropic", "test")
        call_kwargs = client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-haiku-4-5-20251001"

    def test_ollama_uses_openai_path(self, mock_openai_response):
        client = MagicMock()
        client.chat.completions.create.return_value = mock_openai_response("{}")
        _call_llm(client, "ollama", "test", model="llama3")
        call_kwargs = client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "llama3"


# ---------------------------------------------------------------------------
# llm_check_relevance
# ---------------------------------------------------------------------------

class TestLlmCheckRelevance:
    def test_empty_datasets(self):
        result = llm_check_relevance([], "IBD")
        assert result == []

    def test_relevant_datasets_returned(self, mock_openai_response):
        datasets = [
            {"gse_id": "GSE1", "title": "UC colon", "summary": "RNA-seq UC"},
            {"gse_id": "GSE2", "title": "Healthy brain", "summary": "Normal brain"},
        ]
        llm_response = json.dumps([
            {"gse_id": "GSE1", "relevant": True, "confidence": 0.95, "reason": "UC study"},
            {"gse_id": "GSE2", "relevant": False, "confidence": 0.10, "reason": "Unrelated"},
        ])
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_openai_response(llm_response)

        with patch("geotcha.harmonize.llm._get_llm_client", return_value=mock_client):
            result = llm_check_relevance(datasets, "IBD", provider="openai")

        assert result == ["GSE1"]

    def test_low_confidence_filtered(self, mock_openai_response):
        datasets = [{"gse_id": "GSE1", "title": "t", "summary": "s"}]
        llm_response = json.dumps([
            {"gse_id": "GSE1", "relevant": True, "confidence": 0.30, "reason": "Maybe"},
        ])
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_openai_response(llm_response)

        with patch("geotcha.harmonize.llm._get_llm_client", return_value=mock_client):
            result = llm_check_relevance(datasets, "IBD", provider="openai")

        assert result == []

    def test_api_failure_returns_all(self, mock_openai_response):
        datasets = [
            {"gse_id": "GSE1", "title": "t", "summary": "s"},
            {"gse_id": "GSE2", "title": "t2", "summary": "s2"},
        ]
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = RuntimeError("API down")

        with patch("geotcha.harmonize.llm._get_llm_client", return_value=mock_client):
            result = llm_check_relevance(datasets, "IBD", provider="openai")

        assert set(result) == {"GSE1", "GSE2"}

    def test_anthropic_provider(self, mock_anthropic_response):
        datasets = [{"gse_id": "GSE1", "title": "UC study", "summary": "IBD RNA-seq"}]
        llm_response = json.dumps([
            {"gse_id": "GSE1", "relevant": True, "confidence": 0.90, "reason": "IBD study"},
        ])
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response(llm_response)

        with patch("geotcha.harmonize.llm._get_llm_client", return_value=mock_client):
            result = llm_check_relevance(
                datasets, "IBD", provider="anthropic", api_key="sk-ant"
            )

        assert result == ["GSE1"]
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["system"] == RELEVANCE_PROMPT

    def test_malformed_json_returns_all(self):
        datasets = [{"gse_id": "GSE1", "title": "t", "summary": "s"}]
        mock_client = MagicMock()
        resp = MagicMock()
        resp.choices = [MagicMock()]
        resp.choices[0].message.content = "not valid json"
        mock_client.chat.completions.create.return_value = resp

        with patch("geotcha.harmonize.llm._get_llm_client", return_value=mock_client):
            result = llm_check_relevance(datasets, "IBD", provider="openai")

        assert result == ["GSE1"]

    def test_summary_truncated(self, mock_openai_response):
        """Long summaries are truncated to 500 chars in prompt."""
        datasets = [{"gse_id": "GSE1", "title": "t", "summary": "x" * 1000}]
        llm_response = json.dumps([
            {"gse_id": "GSE1", "relevant": True, "confidence": 0.80, "reason": "ok"},
        ])
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_openai_response(llm_response)

        with patch("geotcha.harmonize.llm._get_llm_client", return_value=mock_client):
            llm_check_relevance(datasets, "test", provider="openai")

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        prompt_text = call_kwargs["messages"][1]["content"]
        # The x*1000 summary should be truncated
        assert prompt_text.count("x") <= 500


# ---------------------------------------------------------------------------
# llm_harmonize_fields
# ---------------------------------------------------------------------------

class TestLlmHarmonizeFields:
    def test_empty_fields(self):
        result = llm_harmonize_fields({})
        assert result == {}

    def test_all_none_fields(self):
        result = llm_harmonize_fields({"tissue": None, "disease": None})
        assert result == {}

    def test_harmonize_tissue_disease(self, mock_openai_response):
        llm_response = json.dumps({
            "tissue": {"value": "colon", "confidence": 0.90, "source": "llm"},
            "disease": {"value": "ulcerative colitis", "confidence": 0.85, "source": "llm"},
        })
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_openai_response(llm_response)

        with (
            patch("geotcha.harmonize.llm._get_llm_client", return_value=mock_client),
        ):
            result = llm_harmonize_fields(
                {"tissue": "sigmoid colon biopsy", "disease": "UC"},
                provider="openai",
            )

        assert result["tissue"]["value"] == "colon"
        assert result["disease"]["value"] == "ulcerative colitis"

    def test_api_failure_returns_empty(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = RuntimeError("fail")

        with patch("geotcha.harmonize.llm._get_llm_client", return_value=mock_client):
            result = llm_harmonize_fields({"tissue": "colon"}, provider="openai")

        assert result == {}

    def test_malformed_json_returns_empty(self):
        mock_client = MagicMock()
        resp = MagicMock()
        resp.choices = [MagicMock()]
        resp.choices[0].message.content = "I can't parse this"
        mock_client.chat.completions.create.return_value = resp

        with patch("geotcha.harmonize.llm._get_llm_client", return_value=mock_client):
            result = llm_harmonize_fields({"tissue": "colon"}, provider="openai")

        assert result == {}


# ---------------------------------------------------------------------------
# llm_harmonize_record
# ---------------------------------------------------------------------------

class TestLlmHarmonizeRecord:
    def test_skips_already_harmonized_gse(self, gse_with_samples):
        """Fields already harmonized by rules are not sent to LLM."""
        record = gse_with_samples
        record.tissue_harmonized = "colon"
        record.disease_harmonized = "ulcerative colitis"
        # Samples also harmonized
        record.samples[0].tissue_harmonized = "colon"
        record.samples[0].disease_harmonized = "ulcerative colitis"
        record.samples[0].gender_harmonized = "male"

        # If LLM were called, it would raise — proving it's not called
        with patch("geotcha.harmonize.llm.llm_harmonize_fields", side_effect=RuntimeError):
            result = llm_harmonize_record(record)

        assert result.tissue_harmonized == "colon"

    def test_harmonizes_unresolved_gse_fields(self, gse_with_samples, mock_openai_response):
        record = gse_with_samples
        # tissue and disease are set but NOT harmonized
        assert record.tissue_harmonized is None
        assert record.disease_harmonized is None

        # Also make samples already harmonized to isolate GSE test
        record.samples[0].tissue_harmonized = "colon"
        record.samples[0].disease_harmonized = "UC"
        record.samples[0].gender_harmonized = "male"

        llm_response = json.dumps({
            "tissue": {"value": "sigmoid colon", "confidence": 0.88, "source": "llm"},
            "disease": {"value": "ulcerative colitis", "confidence": 0.92, "source": "llm"},
        })
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_openai_response(llm_response)

        with patch("geotcha.harmonize.llm._get_llm_client", return_value=mock_client):
            result = llm_harmonize_record(record, provider="openai")

        assert result.tissue_harmonized == "sigmoid colon"
        assert result.tissue_source == "llm"
        assert result.tissue_confidence == 0.88
        assert result.disease_harmonized == "ulcerative colitis"
        assert result.disease_source == "llm"

    def test_harmonizes_unresolved_sample_fields(self, gse_with_samples, mock_openai_response):
        record = gse_with_samples
        # GSE already harmonized
        record.tissue_harmonized = "colon"
        record.disease_harmonized = "UC"
        # Sample NOT harmonized
        assert record.samples[0].tissue_harmonized is None

        llm_response = json.dumps({
            "tissue": {"value": "sigmoid colon", "confidence": 0.85, "source": "llm"},
            "disease": {"value": "ulcerative colitis", "confidence": 0.90, "source": "llm"},
            "gender": {"value": "male", "confidence": 0.95, "source": "llm"},
        })
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_openai_response(llm_response)

        with patch("geotcha.harmonize.llm._get_llm_client", return_value=mock_client):
            result = llm_harmonize_record(record, provider="openai")

        sample = result.samples[0]
        assert sample.tissue_harmonized == "sigmoid colon"
        assert sample.tissue_source == "llm"
        assert sample.disease_harmonized == "ulcerative colitis"
        assert sample.gender_harmonized == "male"
        assert sample.gender_source == "llm"

    def test_default_confidence_075(self, gse_with_samples, mock_openai_response):
        """If LLM response omits confidence, default to 0.75."""
        record = gse_with_samples

        record.samples[0].tissue_harmonized = "x"
        record.samples[0].disease_harmonized = "x"
        record.samples[0].gender_harmonized = "x"

        llm_response = json.dumps({
            "tissue": {"value": "colon"},  # no confidence key
        })
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_openai_response(llm_response)

        with patch("geotcha.harmonize.llm._get_llm_client", return_value=mock_client):
            result = llm_harmonize_record(record, provider="openai")

        assert result.tissue_confidence == 0.75

    def test_api_failure_preserves_record(self, gse_with_samples):
        """If LLM fails, record is returned unchanged."""
        record = gse_with_samples

        with patch(
            "geotcha.harmonize.llm._get_llm_client",
            side_effect=RuntimeError("API key invalid"),
        ):
            result = llm_harmonize_record(record, provider="openai")

        assert result.tissue_harmonized is None
        assert result.disease_harmonized is None

    def test_passes_provider_and_key(self, gse_with_samples, mock_openai_response):
        record = gse_with_samples
        record.samples[0].tissue_harmonized = "x"
        record.samples[0].disease_harmonized = "x"
        record.samples[0].gender_harmonized = "x"

        llm_response = json.dumps({
            "tissue": {"value": "colon", "confidence": 0.9, "source": "llm"},
        })
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_openai_response(llm_response)

        with patch("geotcha.harmonize.llm._get_llm_client", return_value=mock_client) as mock_get:
            llm_harmonize_record(
                record, provider="openai", api_key="sk-test", model="gpt-4o"
            )

        mock_get.assert_called_with("openai", "sk-test")


# ---------------------------------------------------------------------------
# Prompt content checks
# ---------------------------------------------------------------------------

class TestPrompts:
    def test_harmonization_prompt_has_rules(self):
        assert "Gender" in HARMONIZATION_PROMPT
        assert "Tissue" in HARMONIZATION_PROMPT
        assert "Disease" in HARMONIZATION_PROMPT
        assert "UBERON" in HARMONIZATION_PROMPT
        assert "JSON" in HARMONIZATION_PROMPT

    def test_relevance_prompt_has_structure(self):
        assert "gse_id" in RELEVANCE_PROMPT
        assert "relevant" in RELEVANCE_PROMPT
        assert "confidence" in RELEVANCE_PROMPT
        assert "JSON" in RELEVANCE_PROMPT
