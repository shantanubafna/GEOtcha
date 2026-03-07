# GEOtcha

[![CI](https://github.com/shantanubafna/GEOtcha/actions/workflows/ci.yml/badge.svg)](https://github.com/shantanubafna/GEOtcha/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/geotcha)](https://pypi.org/project/geotcha/)
[![Python](https://img.shields.io/pypi/pyversions/geotcha)](https://pypi.org/project/geotcha/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Extract and harmonize RNA-seq metadata from NCBI GEO.

GEOtcha is a CLI tool that helps researchers search GEO by disease keyword, filter to human RNA-seq datasets, extract structured metadata at both series (GSE) and sample (GSM) levels, and harmonize the results into standardized output files.

## Installation

```bash
pip install geotcha
```

With optional extras:

```bash
pip install geotcha[ml]       # ML harmonization (GLiNER + SapBERT + FAISS)
pip install geotcha[parquet]  # Parquet export support
pip install geotcha[llm]      # LLM harmonization
```

For development:

```bash
git clone https://github.com/shantanubafna/GEOtcha.git
cd geotcha
pip install -e ".[dev]"
```

## Quick Start

### Search for datasets

```bash
geotcha search "inflammatory bowel disease"
```

### Full pipeline with subset testing

```bash
geotcha run "IBD" --subset 5 --output ./results/ --harmonize
```

### Extract from specific GSE IDs

```bash
geotcha extract GSE12345 GSE67890 --output ./results/
```

### Output format selection

```bash
# CSV (default), TSV, or Parquet
geotcha run "IBD" --harmonize --format csv
geotcha extract GSE12345 -f tsv
geotcha run "IBD" -f parquet --output ./results/
```

Parquet requires `pip install geotcha[parquet]`.

### Include single-cell RNA-seq datasets (excluded by default)

```bash
geotcha run "IBD" --subset 5 --include-scrna
```

### Disease packs

```bash
# List available packs
geotcha packs

# Use a pack for optimized search
geotcha run "IBD" --pack ibd --harmonize
geotcha run "breast cancer" --pack oncology --harmonize
```

Available packs: `ibd`, `oncology`, `neurodegeneration`, `autoimmune`, `metabolic`.

### With ML harmonization (zero-shot NER + entity linking)

```bash
pip install geotcha[ml]

# Build FAISS ontology indices (one-time)
geotcha ml build-index

# Run with ML
geotcha run "IBD" --harmonize --ml-mode hybrid
```

ML fills in missing or low-confidence fields using GLiNER biomedical NER and SapBERT entity linking. Use `--ml-mode full` to let ML run on all fields.

### With LLM harmonization

```bash
pip install geotcha[llm]
geotcha run "IBD" --harmonize --llm --llm-provider anthropic
```

### Combined: rules + ML + LLM

```bash
pip install "geotcha[ml,llm]"
geotcha run "IBD" --harmonize --ml-mode hybrid --llm
```

The harmonization chain runs in order: **rules → ML → LLM**. Each layer only upgrades fields that are still missing or low-confidence.

### Structured JSON logging

```bash
geotcha run "IBD" --log-json --output ./results/
geotcha extract GSE12345 --log-json
```

Emits structured JSON log lines to stderr — useful for log aggregation in production pipelines.

### Benchmark harmonization quality

```bash
# Run against bundled fixtures (100 curated datasets)
geotcha benchmark

# Custom fixtures and output
geotcha benchmark --input ./my_fixtures/ --output ./report.json

# Benchmark with ML enabled
geotcha benchmark --ml-mode hybrid
```

Produces a JSON report with per-field exact match, completeness, ontology coverage, and confidence metrics.

### Run report

```bash
# After a pipeline run completes, view a summary:
geotcha report <run_id>

# Write report.json to a custom directory:
geotcha report <run_id> --output ./reports/
```

Prints run metadata (query, ID counts, failures, stage timings) and writes a `report.json` file.

### CI / non-interactive mode

```bash
geotcha run "IBD" --non-interactive --output ./results/
geotcha run "IBD" --yes --subset 10 --harmonize
```

## Python SDK

```python
from geotcha import GEOtchaClient

client = GEOtchaClient(ncbi_api_key="...")
ids = client.search("ulcerative colitis")
records = client.extract(ids[:5])
records = client.harmonize(records, ml_mode="hybrid")
client.export(records, output_dir="./results", fmt="parquet")

# Benchmark harmonization quality
report = client.benchmark()
print(report["summary"]["overall_exact_match"])
```

The SDK has no Typer/Rich dependency — safe for notebooks, scripts, and downstream pipelines. Failed GSE parses are silently skipped.

## Configuration

```bash
# Set your NCBI API key (recommended for higher rate limits)
geotcha config set ncbi_api_key "YOUR_KEY"

# Set your email for NCBI Entrez
geotcha config set ncbi_email "you@example.com"

# View current configuration
geotcha config show

# Validate configuration
geotcha config validate
```

Configuration priority: CLI flags > environment variables (`GEOTCHA_*`) > config file (`~/.config/geotcha/config.toml`) > defaults.

## Output

GEOtcha produces:
- **`gse_summary.csv`** — One row per GSE with series-level metadata (or `.tsv` / `.parquet` with `--format`)
- **`gsm/<GSE_ID>_samples.csv`** — Per-GSE file with sample-level metadata
- **`manifest.json`** (in run state dir) — Audit trail: run_id, query, timestamps, stage timings, counts, masked settings
- **`review_queue.csv`** — Low-confidence harmonized fields flagged for manual review (always CSV)
- With `--harmonize`: additional `_harmonized`, `_source`, `_confidence`, and `_ontology_id` columns

### Fields extracted

| Level | Fields |
|-------|--------|
| GSE | ID, URL, title, organism, experiment type, platform, sample counts, PubMed links, tissue, disease, treatment, timepoint, gender, age, responder info |
| GSM | ID, title, source, organism, platform, instrument, library strategy, tissue, cell type, disease, gender, age, treatment, timepoint, responder status |

## Interactive Flow

```
$ geotcha run "IBD"
Searching GEO for: IBD, ulcerative colitis, Crohn's disease...
Found 347 datasets. After filtering (Homo sapiens + RNA-seq): 182 datasets.

Run on a subset first? [Y/n]: Y
Subset size [5]: 5

Processing 5/182 datasets...
 [████████████████] 5/5 complete

Results: ./output/gse_summary.csv (5 rows), ./output/gsm/ (5 files)

Proceed with remaining 177 datasets? [Y/n]:
```

Use `--yes` or `--non-interactive` to skip all prompts (useful for CI and scripted workflows).

## Resume

Interrupted runs can be resumed with `geotcha resume <run_id>`. Resume correctly merges previously extracted rows in `gse_summary.csv` with newly extracted records, deduplicating by `gse_id`.

## Disease Expansion

GEOtcha automatically expands disease keywords to capture related terms using two sources:

1. **Hand-curated aliases** for common abbreviations (IBD, SLE, RA, COPD, etc.)
2. **DOID ontology subtypes** — any disease in the 12,000-term Disease Ontology is auto-expanded with its subtypes (e.g., "breast cancer" also searches "breast carcinoma", "triple-negative breast cancer", etc.)

Examples:
- **IBD** → inflammatory bowel disease, ulcerative colitis, Crohn's disease + DOID subtypes
- **breast cancer** → breast cancer, breast carcinoma, male/female breast cancer, luminal breast carcinoma, ...
- **melanoma** → melanoma, skin melanoma, uveal melanoma, mucosal melanoma, ...

Short ambiguous abbreviations (UC, CD) are excluded from Entrez search queries but used for post-search relevance filtering.

## Filtering

GEOtcha automatically filters search results to human RNA-seq datasets. By default, **single-cell RNA-seq datasets are excluded** (scRNA-seq, snRNA-seq, 10x Genomics, Drop-seq, etc.) since most bulk RNA-seq meta-analyses don't want these mixed in.

Single-cell filtering happens at two levels:
- **Search level**: eSummary title/summary scanned for scRNA-seq keywords
- **Sample level**: GSM `library_source` checked for "single cell"

To include single-cell datasets, use the `--include-scrna` flag:

```bash
geotcha run "IBD" --include-scrna
geotcha extract GSE12345 --include-scrna
```

Or set it in config:

```bash
geotcha config set include_scrna true
```

## Harmonization

Three-tier harmonization pipeline (each layer is optional):

### 1. Rules (always on with `--harmonize`)
- **Gender**: male/M/man → "male"
- **Age**: "45 years", "45yo" → "45"
- **Tissue**: mapped to UBERON ontology (~4,000 terms from OBO Foundry)
- **Disease**: mapped to Disease Ontology (~12,000 DOID terms + common abbreviations like UC, IBD, COPD)
- **Cell type**: mapped to Cell Ontology (~3,000 CL terms)
- **Treatment**: ~300 drugs/stimuli with ChEBI IDs, brand name synonyms (e.g., Remicade → infliximab)
- **Timepoint**: "week 8", "W8" → "W8"

Five confidence tiers: exact (1.0) → synonym (0.85) → normalized-exact (0.80) → token-set overlap (0.75) → substring (0.70). Fields below the review threshold are flagged for manual review.

Extraction uses 40+ GEO characteristic keys (tissue, disease, cell type, treatment) and a `source_name` parser that splits concatenated metadata (e.g., "colon, ulcerative colitis, male, 45y") into structured fields.

Ontology mappings are shipped as JSON package data (`src/geotcha/data/ontology/`) with ~27,000 synonyms extracted from official OBO sources. To regenerate from upstream ontologies:

```bash
python scripts/build_ontologies.py
```

### 2. ML (`--ml-mode hybrid` or `--ml-mode full`)
- **GLiNER-BioMed**: zero-shot biomedical NER for disease, tissue, cell type, treatment, gender
- **SapBERT + FAISS**: entity linking to UBERON/DOID/CL/ChEBI ontology terms via pre-built FAISS indices
- Build indices once with `geotcha ml build-index`, check status with `geotcha ml status`
- In `hybrid` mode, ML only fills fields where rules produced low confidence or no value
- Low-confidence ML predictions flag records with `needs_review=True`

### 3. LLM (`--llm`)
- Optional LLM-assisted harmonization for ambiguous free-text values
- Supports OpenAI, Anthropic, and Ollama providers

Each field tracks provenance: `_harmonized`, `_source` (rule/ml/llm), `_confidence`, and `_ontology_id`.

## Documentation

Full documentation: install `pip install geotcha[docs]` and run `mkdocs serve`, or see the `docs/` directory:

- [Getting Started](docs/getting-started.md)
- [CLI Reference](docs/cli-reference.md)
- [Python SDK](docs/sdk-reference.md)
- [Harmonization Guide](docs/harmonization.md)
- [Disease Packs](docs/disease-packs.md)
- [ML & LLM](docs/ml-llm.md)
- [Extending Ontologies](docs/extending-ontologies.md)

## License

MIT
