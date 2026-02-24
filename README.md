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

### Include single-cell RNA-seq datasets (excluded by default)

```bash
geotcha run "IBD" --subset 5 --include-scrna
```

### With LLM harmonization

```bash
pip install geotcha[llm]
geotcha run "IBD" --harmonize --llm --llm-provider anthropic
```

### CI / non-interactive mode

```bash
geotcha run "IBD" --non-interactive --output ./results/
geotcha run "IBD" --yes --subset 10 --harmonize
```

## Configuration

```bash
# Set your NCBI API key (recommended for higher rate limits)
geotcha config set ncbi_api_key "YOUR_KEY"

# Set your email for NCBI Entrez
geotcha config set ncbi_email "you@example.com"

# View current configuration
geotcha config show
```

Configuration priority: CLI flags > environment variables (`GEOTCHA_*`) > config file (`~/.config/geotcha/config.toml`) > defaults.

## Output

GEOtcha produces:
- **`gse_summary.csv`** — One row per GSE with series-level metadata
- **`gsm/<GSE_ID>_samples.csv`** — Per-GSE file with sample-level metadata
- **`manifest.json`** (in run state dir) — Audit trail: run_id, query, timestamps, counts, masked settings
- With `--harmonize`: additional `_harmonized` columns with standardized values

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

GEOtcha automatically expands disease keywords to capture related terms:
- **IBD** → inflammatory bowel disease, ulcerative colitis, Crohn's disease (abbreviations like UC, CD are used for relevance filtering)
- **SLE** → systemic lupus erythematosus, lupus
- **RA** → rheumatoid arthritis

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

Rule-based normalization for:
- **Gender**: male/M/man → "male"
- **Age**: "45 years", "45yo" → "45"
- **Tissue**: mapped to UBERON ontology terms
- **Disease**: mapped to Disease Ontology terms
- **Timepoint**: "week 8", "W8" → "W8"

Optional LLM-assisted harmonization (`--llm`) for ambiguous free-text values.

## License

MIT
