# ML & LLM Harmonization

## ML Harmonization

ML harmonization uses biomedical NLP models to handle the long tail of metadata that rules can't cover.

### Setup

```bash
pip install geotcha[ml]
```

This installs GLiNER, SentenceTransformers, and FAISS.

### Building Ontology Indices

SapBERT entity linking requires pre-built FAISS indices that encode ontology terms:

```bash
# Build indices (one-time setup, ~5 minutes)
geotcha ml build-index

# Check status
geotcha ml status
```

Indices are stored in `~/.cache/geotcha/ml/v1/indices/`.

### Usage

```bash
# Hybrid: ML only fills gaps left by rules
geotcha run "IBD" --harmonize --ml-mode hybrid

# Full: ML runs on all fields
geotcha run "IBD" --harmonize --ml-mode full
```

### How It Works

1. **GLiNER NER**: Zero-shot biomedical named entity recognition extracts disease, tissue, cell type, treatment, and gender mentions from sample titles and descriptions.

2. **SapBERT Entity Linking**: Extracted entities are encoded with SapBERT and matched to the nearest ontology term via FAISS cosine similarity search.

3. **Confidence Thresholds**:
   - Score ≥ `ml_threshold` (default 0.65): prediction accepted
   - Score between `ml_review_threshold` and `ml_threshold`: no action (gray zone)
   - Score < `ml_review_threshold` (default 0.50): flagged for manual review

### Configuration

```bash
geotcha config set ml_mode "hybrid"
geotcha config set ml_threshold "0.70"
geotcha config set ml_device "cpu"
```

Or via environment variables: `GEOTCHA_ML_MODE`, `GEOTCHA_ML_THRESHOLD`, `GEOTCHA_ML_DEVICE`.

## LLM Harmonization

LLM harmonization sends ambiguous free-text values to a language model for structured normalization.

### Setup

```bash
pip install geotcha[llm]
```

### Providers

| Provider | Model Default | Env Var |
|----------|--------------|---------|
| OpenAI | gpt-4o-mini | `OPENAI_API_KEY` |
| Anthropic | claude-haiku-4-5 | `ANTHROPIC_API_KEY` |
| Ollama | — | Local server |

### Usage

```bash
# OpenAI
geotcha run "IBD" --harmonize --llm --llm-provider openai

# Anthropic
geotcha run "IBD" --harmonize --llm --llm-provider anthropic

# Local Ollama
geotcha run "IBD" --harmonize --llm --llm-provider ollama
```

### Combined Pipeline

```bash
pip install "geotcha[ml,llm]"
geotcha run "IBD" --harmonize --ml-mode hybrid --llm
```

The chain runs: **rules → ML → LLM**. Each layer only upgrades fields still missing or low-confidence.
