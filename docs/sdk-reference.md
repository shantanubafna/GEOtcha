# Python SDK

The `GEOtchaClient` provides a programmatic API with no Typer/Rich dependency — safe for notebooks, scripts, and downstream pipelines.

## Basic Usage

```python
from geotcha import GEOtchaClient

client = GEOtchaClient(ncbi_api_key="...")
ids = client.search("ulcerative colitis")
records = client.extract(ids[:5])
records = client.harmonize(records, ml_mode="hybrid")
client.export(records, output_dir="./results", fmt="parquet")
```

## Search

```python
ids = client.search("breast cancer")
# Returns list of GSE IDs
```

## Extract

```python
records = client.extract(["GSE12345", "GSE67890"])
# Returns list of GSERecord objects
# Failed GSE parses are silently skipped
```

## Harmonize

```python
records = client.harmonize(records)                    # Rules only
records = client.harmonize(records, ml_mode="hybrid")  # Rules + ML
records = client.harmonize(records, use_llm=True)      # Rules + LLM
```

## Export

```python
client.export(records, output_dir="./results")             # CSV
client.export(records, output_dir="./results", fmt="tsv")  # TSV
client.export(records, output_dir="./results", fmt="parquet")  # Parquet
```

## Benchmark

```python
report = client.benchmark()
print(report["summary"]["overall_exact_match"])  # e.g., 1.0
print(report["summary"]["overall_completeness"])  # e.g., 1.0
```

## Disease Packs

```python
from geotcha.packs import load_pack, list_packs

# List available packs
print(list_packs())  # ['autoimmune', 'ibd', 'metabolic', ...]

# Load a pack
pack = load_pack("ibd")
print(pack.search_terms)
print(pack.expected_tissues)
```

## Data Models

### GSERecord

Series-level metadata. Key fields:

- `gse_id`, `title`, `summary`, `overall_design`
- `organism`, `experiment_type`, `platform`
- `tissue`, `disease`, `treatment`, `timepoint`
- `samples` — list of `GSMRecord`
- Harmonized fields: `tissue_harmonized`, `disease_harmonized`, etc.
- Provenance: `tissue_source`, `tissue_confidence`, `tissue_ontology_id`, etc.

### GSMRecord

Sample-level metadata. Key fields:

- `gsm_id`, `gse_id`, `title`, `source_name`
- `tissue`, `cell_type`, `disease`, `gender`, `age`, `treatment`
- `characteristics` — dict of parsed GEO characteristics
- Harmonized + provenance fields (same pattern as GSERecord)
