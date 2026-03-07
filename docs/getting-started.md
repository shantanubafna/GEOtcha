# Getting Started

## Installation

### Basic

```bash
pip install geotcha
```

### With optional extras

```bash
pip install geotcha[ml]       # ML harmonization (GLiNER + SapBERT + FAISS)
pip install geotcha[parquet]  # Parquet export support
pip install geotcha[llm]      # LLM harmonization (OpenAI/Anthropic/Ollama)
```

### Development

```bash
git clone https://github.com/shantanubafna/GEOtcha.git
cd GEOtcha
pip install -e ".[dev]"
```

## Configuration

Set your NCBI credentials for higher rate limits:

```bash
geotcha config set ncbi_api_key "YOUR_KEY"
geotcha config set ncbi_email "you@example.com"
geotcha config validate
```

Configuration priority: CLI flags > environment variables (`GEOTCHA_*`) > config file (`~/.config/geotcha/config.toml`) > defaults.

## Your First Search

```bash
geotcha run "inflammatory bowel disease" --subset 5 --harmonize
```

This will:

1. Search GEO for IBD-related datasets (with automatic expansion to UC, Crohn's, etc.)
2. Filter to human RNA-seq only
3. Extract metadata from 5 datasets
4. Harmonize fields with ontology mapping
5. Export to `./output/gse_summary.csv`

## Using Disease Packs

Disease packs provide optimized search configurations for common research areas:

```bash
# List available packs
geotcha packs

# Use a pack
geotcha run "IBD" --pack ibd --harmonize
```

Available packs: `ibd`, `oncology`, `neurodegeneration`, `autoimmune`, `metabolic`.

## Output Files

| File | Description |
|------|-------------|
| `gse_summary.csv` | One row per GSE with series-level metadata |
| `gsm/<GSE_ID>_samples.csv` | Per-GSE file with sample-level metadata |
| `review_queue.csv` | Low-confidence fields flagged for manual review |
| `manifest.json` | Audit trail in the run state directory |

With `--harmonize`, additional columns are added: `_harmonized`, `_source`, `_confidence`, `_ontology_id`.
