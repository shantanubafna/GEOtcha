# GEOtcha

**Extract and harmonize RNA-seq metadata from NCBI GEO.**

GEOtcha is a CLI tool and Python SDK that helps researchers:

- **Search** GEO by disease keyword with automatic term expansion
- **Filter** to human RNA-seq datasets (excluding single-cell by default)
- **Extract** structured metadata at both series (GSE) and sample (GSM) levels
- **Harmonize** using rules, ML, and LLM — with ontology IDs and confidence scores
- **Export** to CSV, TSV, or Parquet

## Why GEOtcha?

Existing tools (GEOquery, pysradb, ffq) are pure retrieval — they download metadata but don't normalize it. GEOtcha's competitive moat is **harmonization quality**: 90%+ fields harmonized with confidence ≥ 0.85 on our 100-dataset benchmark.

## Quick Install

```bash
pip install geotcha
```

## Quick Example

```bash
# Search and extract IBD datasets
geotcha run "IBD" --subset 5 --harmonize

# Use a disease pack for optimized search
geotcha run "IBD" --pack ibd --harmonize

# Extract specific datasets
geotcha extract GSE12345 GSE67890 --output ./results/
```

## Pipeline

```
Search → Filter → Extract → Harmonize → Export
                              ↓
                    Rules → ML → LLM
```

Each harmonization layer is optional. Rules are always on with `--harmonize`. ML and LLM are opt-in.
