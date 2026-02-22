"""Optional LLM-based harmonization for ambiguous metadata values."""

from __future__ import annotations

import json
import logging

from geotcha.models import GSERecord

logger = logging.getLogger(__name__)

# System prompt for LLM harmonization
HARMONIZATION_PROMPT = """You are a biomedical metadata harmonization expert. Given raw metadata
fields from GEO (Gene Expression Omnibus) datasets, normalize them to standard values.

For each field, return a JSON object with:
- "value": the normalized value
- "confidence": a float between 0 and 1
- "source": "llm"

Rules:
- Gender: normalize to "male", "female", or "unknown"
- Age: normalize to numeric years (e.g., "45")
- Tissue: normalize to standard anatomical terms (UBERON vocabulary)
- Disease: normalize to standard disease names (Disease Ontology vocabulary)
- Treatment: extract drug name, dose if available
- Timepoint: normalize to format like W4 (week 4), D7 (day 7), M3 (month 3)

Respond with valid JSON only."""


def _get_llm_client(provider: str, api_key: str | None = None):
    """Get an LLM client based on provider."""
    if provider == "openai":
        from openai import OpenAI
        return OpenAI(api_key=api_key)
    elif provider == "anthropic":
        import anthropic
        return anthropic.Anthropic(api_key=api_key)
    elif provider == "ollama":
        from openai import OpenAI
        return OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


def _call_llm(client, provider: str, prompt: str, model: str | None = None) -> str:
    """Make an LLM API call."""
    if provider == "anthropic":
        model = model or "claude-haiku-4-5-20251001"
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=HARMONIZATION_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    else:
        # OpenAI-compatible (OpenAI, Ollama)
        model = model or "gpt-4o-mini"
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": HARMONIZATION_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1024,
        )
        return response.choices[0].message.content


RELEVANCE_PROMPT = """You are a biomedical dataset relevance classifier. \
Given a disease query and a list
of GEO dataset summaries, determine whether each dataset is relevant to the disease query.

For each dataset, respond with a JSON object containing:
- "gse_id": the GSE accession
- "relevant": true or false
- "confidence": a float between 0 and 1
- "reason": a brief explanation

Respond with a JSON array only. No additional text."""


def llm_check_relevance(
    datasets: list[dict[str, str]],
    query: str,
    provider: str = "openai",
    api_key: str | None = None,
    model: str | None = None,
) -> list[str]:
    """Use LLM to classify dataset relevance to a disease query.

    Args:
        datasets: List of dicts with keys "gse_id", "title", "summary".
        query: Original disease query string.
        provider: LLM provider name.
        api_key: Optional API key override.
        model: Optional model name override.

    Returns:
        List of GSE IDs classified as relevant.
    """
    if not datasets:
        return []

    # Build the prompt with dataset info
    dataset_lines = []
    for ds in datasets:
        dataset_lines.append(
            f"- {ds['gse_id']}: {ds.get('title', 'N/A')}\n"
            f"  Summary: {ds.get('summary', 'N/A')[:500]}"
        )
    datasets_text = "\n".join(dataset_lines)

    prompt = (
        f"Disease query: {query}\n\n"
        f"Datasets:\n{datasets_text}\n\n"
        f"Classify each dataset as relevant or not relevant to the disease query."
    )

    try:
        client = _get_llm_client(provider, api_key)

        if provider == "anthropic":
            used_model = model or "claude-haiku-4-5-20251001"
            response = client.messages.create(
                model=used_model,
                max_tokens=2048,
                system=RELEVANCE_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            response_text = response.content[0].text
        else:
            used_model = model or "gpt-4o-mini"
            response = client.chat.completions.create(
                model=used_model,
                messages=[
                    {"role": "system", "content": RELEVANCE_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=2048,
            )
            response_text = response.choices[0].message.content

        results = json.loads(response_text)
        relevant_ids = [
            r["gse_id"] for r in results
            if r.get("relevant", False) and r.get("confidence", 0) >= 0.5
        ]
        logger.info(
            f"LLM relevance check: {len(relevant_ids)}/{len(datasets)} "
            f"datasets classified as relevant"
        )
        return relevant_ids
    except Exception as e:
        logger.warning(f"LLM relevance check failed: {e}. Keeping all datasets.")
        return [ds["gse_id"] for ds in datasets]


def llm_harmonize_fields(
    fields: dict[str, str | None],
    provider: str = "openai",
    api_key: str | None = None,
    model: str | None = None,
) -> dict[str, dict]:
    """Use LLM to harmonize a set of metadata fields.

    Returns dict mapping field names to {value, confidence, source}.
    """
    # Only send non-empty fields
    non_empty = {k: v for k, v in fields.items() if v}
    if not non_empty:
        return {}

    prompt = f"Harmonize these metadata fields:\n{json.dumps(non_empty, indent=2)}"

    try:
        client = _get_llm_client(provider, api_key)
        response_text = _call_llm(client, provider, prompt, model)
        result = json.loads(response_text)
        return result
    except Exception as e:
        logger.warning(f"LLM harmonization failed: {e}")
        return {}


def llm_harmonize_record(
    record: GSERecord,
    provider: str = "openai",
    api_key: str | None = None,
    model: str | None = None,
) -> GSERecord:
    """Apply LLM harmonization to a GSERecord.

    Only harmonizes fields that weren't already resolved by rules.
    """
    # Collect unresolved GSE-level fields
    gse_fields = {}
    if record.tissue and not record.tissue_harmonized:
        gse_fields["tissue"] = record.tissue
    if record.disease and not record.disease_harmonized:
        gse_fields["disease"] = record.disease

    if gse_fields:
        result = llm_harmonize_fields(gse_fields, provider, api_key, model)
        if "tissue" in result:
            record.tissue_harmonized = result["tissue"].get("value")
        if "disease" in result:
            record.disease_harmonized = result["disease"].get("value")

    # Harmonize unresolved sample-level fields
    for sample in record.samples:
        sample_fields = {}
        if sample.tissue and not sample.tissue_harmonized:
            sample_fields["tissue"] = sample.tissue
        if sample.disease and not sample.disease_harmonized:
            sample_fields["disease"] = sample.disease
        if sample.gender and not sample.gender_harmonized:
            sample_fields["gender"] = sample.gender

        if sample_fields:
            result = llm_harmonize_fields(sample_fields, provider, api_key, model)
            if "tissue" in result:
                sample.tissue_harmonized = result["tissue"].get("value")
            if "disease" in result:
                sample.disease_harmonized = result["disease"].get("value")
            if "gender" in result:
                sample.gender_harmonized = result["gender"].get("value")

    return record
