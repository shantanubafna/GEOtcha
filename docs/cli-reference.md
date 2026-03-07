# CLI Reference

## Commands

### `geotcha search`

Search GEO for datasets matching a disease keyword.

```bash
geotcha search "breast cancer"
geotcha search "IBD" --limit 50
```

### `geotcha run`

Run the full pipeline: search → filter → extract → export.

```bash
geotcha run "IBD" --subset 5 --harmonize
geotcha run "breast cancer" --pack oncology --harmonize --ml-mode hybrid
geotcha run "IBD" --yes --non-interactive --output ./results/
```

| Option | Description |
|--------|-------------|
| `--subset N` | Process N datasets first for validation |
| `--harmonize` | Apply harmonization rules |
| `--llm` | Enable LLM harmonization |
| `--llm-provider` | LLM provider: openai, anthropic, ollama |
| `--ml-mode` | ML mode: off, hybrid, full |
| `--pack NAME` | Use a disease pack |
| `--format` | Output format: csv, tsv, parquet |
| `--output` | Output directory |
| `--include-scrna` | Include single-cell RNA-seq datasets |
| `--yes` / `--non-interactive` | Skip all prompts |
| `--log-json` | Structured JSON logging |

### `geotcha extract`

Extract metadata from specific GSE IDs.

```bash
geotcha extract GSE12345 GSE67890 --harmonize
geotcha extract GSE12345 -f parquet -o ./results/
```

### `geotcha resume`

Resume an interrupted pipeline run.

```bash
geotcha resume <run_id>
```

### `geotcha benchmark`

Benchmark harmonization quality against curated fixtures.

```bash
geotcha benchmark
geotcha benchmark --ml-mode hybrid
geotcha benchmark --input ./my_fixtures/ --output ./report.json
```

### `geotcha report`

View a summary report for a completed run.

```bash
geotcha report <run_id>
geotcha report <run_id> --output ./reports/
```

### `geotcha packs`

List available disease packs.

```bash
geotcha packs
```

### `geotcha config`

Manage configuration.

```bash
geotcha config set ncbi_api_key "YOUR_KEY"
geotcha config show
geotcha config validate
```

### `geotcha ml`

ML model management.

```bash
geotcha ml status          # Show index status
geotcha ml build-index     # Build FAISS ontology indices
geotcha ml download        # Download pre-built indices
```
