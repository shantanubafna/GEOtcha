# Harmonization Guide

GEOtcha's three-tier harmonization pipeline normalizes raw GEO metadata into standardized, ontology-mapped values.

## Pipeline Order

```
Rules → ML → LLM
```

Each layer only upgrades fields that are still missing or low-confidence. Higher layers never downgrade a confident result from a lower layer.

## Tier 1: Rules (always on with `--harmonize`)

Deterministic normalization using ontology lookups and pattern matching.

### Field Normalizers

| Field | Normalization | Ontology |
|-------|--------------|----------|
| Gender | male/M/man → "male", female/F/woman → "female" | — |
| Age | "45 years", "45yo", "45y" → "45" | — |
| Tissue | ~4,000 terms from UBERON | UBERON IDs |
| Disease | ~12,000 terms from Disease Ontology | DOID IDs |
| Cell type | ~3,000 terms from Cell Ontology | CL IDs |
| Treatment | ~300 drugs with brand name synonyms | ChEBI IDs |
| Timepoint | "week 8", "W8", "8 weeks" → "W8" | — |

### Confidence Tiers

Each lookup returns a confidence score based on how the match was found:

| Tier | Confidence | Method |
|------|-----------|--------|
| Exact | 1.0 | Exact lowercase key match in ontology |
| Synonym | 0.85 | Match via synonym dictionary |
| Normalized exact | 0.80 | Match after stripping suffixes (tissue, cells, disease) |
| Token-set overlap | 0.75 | All tokens from shorter set found in longer set |
| Substring | 0.70 | Ontology key is a substring of the query (keys > 3 chars) |
| Raw fallback | 0.50 | No match found, raw value preserved |

### Provenance Tracking

Each harmonized field gets four provenance columns:

- `{field}_harmonized` — the normalized value
- `{field}_source` — "rule", "ml", or "llm"
- `{field}_confidence` — float 0.0–1.0
- `{field}_ontology_id` — e.g., "UBERON:0001155", "DOID:8577"

### Review Queue

Fields with confidence below 0.65 are flagged in `review_queue.csv` for manual review. This threshold is configurable.

## Tier 2: ML (`--ml-mode hybrid` or `--ml-mode full`)

```bash
pip install geotcha[ml]
geotcha run "IBD" --harmonize --ml-mode hybrid
```

- **GLiNER-BioMed**: zero-shot biomedical NER for disease, tissue, cell type, treatment, gender
- **SapBERT**: entity linking to ontology terms via FAISS index

In `hybrid` mode, ML only fills fields where rules produced low confidence or no value. In `full` mode, ML runs on all fields.

### Building ML Indices

SapBERT entity linking requires pre-built FAISS indices:

```bash
geotcha ml build-index
geotcha ml status
```

## Tier 3: LLM (`--llm`)

```bash
pip install geotcha[llm]
geotcha run "IBD" --harmonize --llm --llm-provider anthropic
```

LLM harmonization sends ambiguous free-text values to an LLM for structured normalization. Supports OpenAI, Anthropic, and Ollama.

## Extraction

GEOtcha extracts metadata from 40+ GEO characteristic keys across four categories:

- **Tissue**: tissue, organ, body site, anatomical location, biopsy site, etc.
- **Disease**: disease, disease state, diagnosis, tumor type, cancer type, etc.
- **Cell type**: cell type, cell line, sorted population, flow sorted, etc.
- **Treatment**: treatment, drug, agent, stimulus, compound, etc.

A `source_name` parser splits concatenated metadata (e.g., "colon, ulcerative colitis, male, 45y") into structured fields by matching each segment against ontology terms.
