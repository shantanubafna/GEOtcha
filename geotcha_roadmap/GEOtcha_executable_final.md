# GEOtcha Unified Execution Plan

## Context

GEOtcha is at v0.1.1 with a functional but alpha-stage pipeline (62 tests, sequential extraction, CSV/TSV output). Two roadmap documents outline the path forward: a suggestion codex (5-phase core hardening) and an ML plan codex (hybrid PubMedBERT + SapBERT layer). This plan unifies both into a single executable sequence with clear milestones, version bumps, and acceptance criteria.

**Current state:** Sequential pipeline works end-to-end. Resume has a correctness bug (overwrites with partial data). LLM settings aren't propagated. No parallelism, no provenance fields, no Parquet output, no ML.

---

## Version Progression

| Version | Milestone | Branch | Key Deliverable |
|---------|-----------|--------|-----------------|
| 0.1.1 | Current | `main` | Working alpha |
| 0.2.0 | Reliability | `feat/reliability-0.2.0` | Resume fix, atomic writes, LLM propagation, manifest |
| 0.3.0 | Performance | `feat/performance-0.3.0` | Parallel extraction, Entrez caching, streaming output |
| 0.4.0 | Metadata Quality | `feat/metadata-quality-0.4.0` | Field provenance, ontology confidence tiers, review queue |
| 0.5.0 | UX & SDK | `feat/ux-sdk-0.5.0` | Non-interactive mode, Parquet, `geotcha report`, Python SDK |
| 0.6.0 | ML Layer | `feat/ml-layer-0.6.0` | Hybrid PubMedBERT+SapBERT inference, training pipeline |

---

## Milestone 0.2.0 — Reliability and Correctness

### Objectives
Fix three correctness bugs and add run manifest for auditability.

### Implementation Steps

1. **Atomic state writes** — `src/geotcha/pipeline.py`
   - Change `_save_state` to write to `state.json.tmp` then `os.replace()` (POSIX-atomic)

2. **Run manifest** — `src/geotcha/pipeline.py`
   - Write `manifest.json` alongside `state.json` at each checkpoint
   - Fields: `run_id`, `query`, `started_at`, `completed_at`, `pipeline_version`, `total_ids`, `filtered_ids`, `processed_ids`, `failed_ids`, `output_paths`, `settings_snapshot` (API keys masked)

3. **Resume merge correctness** — `src/geotcha/pipeline.py`
   - In `resume_run`: load existing `gse_summary.csv` rows, merge with newly extracted records (dedup by `gse_id`), write merged set
   - GSM files are per-GSE so no merge needed

4. **LLM settings propagation** — `src/geotcha/pipeline.py`, `src/geotcha/harmonize/llm.py`
   - Add `settings: Settings` parameter to `_harmonize_record`
   - Thread `settings.llm_provider`, `settings.llm_api_key`, `settings.llm_model` through to all `llm_*` calls
   - Fix `llm_harmonize_record` to use passed args instead of hardcoded defaults

5. **Dynamic retry count** — `src/geotcha/search/entrez.py`
   - Replace hardcoded `stop_after_attempt(3)` with `settings.max_retries`
   - Apply consistently to `_esearch` and `_esummary_batch`

6. **Non-interactive config fields** — `src/geotcha/config.py`, `src/geotcha/cli.py`
   - Add `non_interactive: bool = False` and `yes: bool = False` to `Settings`
   - Add `--yes` / `--non-interactive` flags to `run` command
   - Gate `typer.confirm`/`typer.prompt` calls on these settings

### Files Modified
- `src/geotcha/pipeline.py`, `src/geotcha/harmonize/llm.py`, `src/geotcha/config.py`, `src/geotcha/search/entrez.py`, `src/geotcha/cli.py`, `pyproject.toml`, `src/geotcha/__init__.py`

### New Test Files
- `tests/test_pipeline.py` — resume merge, LLM propagation, atomic write, manifest, `--yes` behavior
- `tests/test_cache.py` — get/set/expiry/clear
- `tests/test_config.py` — Settings.load() precedence, save_config round-trip, API key masking

### Acceptance Criteria
1. `resume_run` after subset produces complete `gse_summary.csv` (subset + remaining rows)
2. `--llm --llm-provider anthropic` routes LLM calls to Anthropic, not OpenAI
3. Process kill mid-write leaves valid prior state
4. `manifest.json` present after any run with correct counts
5. `--yes` completes without interactive prompts

---

## Milestone 0.3.0 — Performance and Scalability

### Objectives
2-3x speedup on large runs via parallel extraction and Entrez caching.

### Implementation Steps

1. **Bounded parallel extraction** — `src/geotcha/pipeline.py`
   - Replace for-loop in `_extract_batch` with `ThreadPoolExecutor`
   - Add `max_workers` to Settings (default 4; capped to 2 without API key, 6 with)
   - Preserve output ordering (map future→index, sort)

2. **Entrez response caching** — `src/geotcha/search/entrez.py`
   - Cache `esearch` results (key: `esearch:{query}`) and `esummary` results
   - Use existing `Cache` class pointed at `cache_dir/entrez/`
   - Add `enable_entrez_cache: bool = True` to Settings

3. **Adaptive backoff for GEOparse** — `src/geotcha/extract/gse_parser.py`
   - Wrap `GEOparse.get_GEO()` with tenacity retry (exponential backoff, `settings.max_retries`)

4. **Streaming output** — `src/geotcha/export/writers.py`
   - Split `write_gse_summary` into `open_gse_summary_writer` (context manager) + `write_gse_row`
   - Write GSM files immediately per-GSE as extraction completes

5. **Batch GSE summary enrichment** — `src/geotcha/search/entrez.py`
   - Batch esearch queries (50 IDs per call) instead of individual round trips

### Files Modified
- `src/geotcha/pipeline.py`, `src/geotcha/config.py`, `src/geotcha/search/entrez.py`, `src/geotcha/extract/gse_parser.py`, `src/geotcha/export/writers.py`, `src/geotcha/cli.py` (add `--max-workers`, `--cache-ttl-days`)

### New Test Files
- `tests/test_pipeline_parallel.py` — order preservation, failed-GSE isolation, worker capping
- `tests/test_entrez_cache.py` — cache hit/miss, warm cache reduces API calls

### Acceptance Criteria
1. 50-GSE run with API key is ≥2x faster than sequential (mockable)
2. Same query re-run with warm cache makes zero new Entrez API calls
3. Individual GSE failure doesn't abort batch

---

## Milestone 0.4.0 — Metadata Quality

### Objectives
Per-field provenance and confidence for every harmonized field. Review queue for ambiguous records.

### Implementation Steps

1. **Provenance fields on models** — `src/geotcha/models.py`
   - Add to `GSMRecord` and `GSERecord` for each harmonized field:
     - `<field>_source: str | None` (`rule`, `llm`, `ml`, `raw`)
     - `<field>_confidence: float | None` (0.0–1.0)
     - `<field>_ontology_id: str | None` (for tissue, disease)
   - All `default=None` for backward compat

2. **Ontology confidence tiers** — `src/geotcha/harmonize/ontology.py`, `src/geotcha/harmonize/rules.py`
   - Change lookups to return `(canonical_name, ontology_id, confidence)`
   - Tiers: exact=1.0, synonym=0.85, heuristic=0.70, raw_fallback=0.50
   - Add synonym dict to ontology.py
   - `harmonize_gsm`/`harmonize_gse` populate `_source="rule"` + confidence + ontology_id

3. **Expanded scRNA detection** — `src/geotcha/extract/gsm_parser.py`
   - Check `library_strategy`, sample `title`/`description`, characteristics dict
   - Reuse `SCRNA_PATTERNS` from `src/geotcha/search/filters.py`

4. **Expanded extraction patterns** — `src/geotcha/extract/fields.py`
   - Centralize `extract_disease_status_from_characteristics` with controlled vocab
   - Add tissue synonyms (sigmoid/transverse/ascending/descending colon)
   - Return `tuple[str | None, float]` (value + confidence) from extraction functions

5. **Export provenance columns** — `src/geotcha/export/writers.py`
   - Add `_source`, `_confidence`, `_ontology_id` to CSV/TSV output

6. **Review queue** — `src/geotcha/export/writers.py`, `src/geotcha/pipeline.py`
   - Write `review_queue.csv` for fields with `confidence < 0.65`
   - Columns: `gsm_id`, `gse_id`, field_name, raw, harmonized, confidence, source

### Files Modified
- `src/geotcha/models.py`, `src/geotcha/harmonize/ontology.py`, `src/geotcha/harmonize/rules.py`, `src/geotcha/harmonize/llm.py` (set `_source="llm"`), `src/geotcha/extract/fields.py`, `src/geotcha/extract/gsm_parser.py`, `src/geotcha/export/writers.py`, `src/geotcha/pipeline.py`

### New Test Files
- `tests/test_extract/test_gsm_parser.py` — scRNA detection, disease_status extraction
- `tests/test_harmonize/test_ontology.py` — confidence tier assignments
- `tests/test_harmonize/test_provenance.py` — provenance fields populated after harmonization

### Acceptance Criteria
1. Every harmonized CSV row has non-null `tissue_source`, `tissue_confidence`, `disease_source`, `disease_confidence`
2. `tissue_ontology_id` is `UBERON:0001155` for "colon"
3. `review_queue.csv` written with ambiguous records
4. Existing non-harmonized CSV output unchanged (backward compat)

---

## Milestone 0.5.0 — UX, Adoption & Python SDK

### Objectives
CI/batch readiness, Parquet output, run reports, and programmatic API.

### Implementation Steps

1. **Parquet output** — `src/geotcha/export/writers.py`, `pyproject.toml`
   - Add `parquet = ["pyarrow>=14.0"]` optional dependency
   - Add `write_gse_parquet`/`write_gsm_parquet` using pyarrow
   - Route in `write_all` based on `fmt` parameter
   - Add `--format csv|tsv|parquet` to CLI

2. **`geotcha report` command** — `src/geotcha/cli.py`
   - Reads `manifest.json`, prints markdown summary to stdout
   - Writes `report.json` with counts, stage timings, failure list

3. **Structured JSON logs** — `src/geotcha/config.py`, `src/geotcha/cli.py`
   - Add `log_json: bool = False` to Settings and `--log-json` flag
   - Configure root logger with JSON formatter when enabled

4. **Stage timings** — `src/geotcha/pipeline.py`
   - Record `time.monotonic()` per stage, store in manifest

5. **Python SDK** — `src/geotcha/api.py` (new file)
   ```python
   class GEOtchaClient:
       def __init__(self, settings: Settings | None = None): ...
       def search(self, query: str) -> list[str]: ...
       def extract(self, gse_ids: list[str]) -> list[GSERecord]: ...
       def harmonize(self, records: list[GSERecord]) -> list[GSERecord]: ...
       def export(self, records: list[GSERecord], output_dir: Path, fmt: str = "csv") -> dict[str, Path]: ...
       def run(self, query: str, **kwargs) -> list[GSERecord]: ...
   ```
   - Delegates to pipeline functions, no Typer/Rich dependency
   - Export via `src/geotcha/__init__.py`: `from geotcha.api import GEOtchaClient`

6. **`config validate` subcommand** — `src/geotcha/cli.py`
   - Print which settings are set vs defaults, warnings for missing email/API key

### New Files
- `src/geotcha/api.py`, `tests/test_api.py`, `tests/test_report.py`, `tests/test_export/test_parquet.py`

### Acceptance Criteria
1. `--non-interactive` completes without prompts
2. `--format parquet` produces readable Parquet files
3. `geotcha report <run_id>` shows stage timings and counts
4. `from geotcha import GEOtchaClient` works without Typer/Rich imports
5. `--log-json` emits valid NDJSON to stderr

---

## Milestone 0.6.0 — ML Layer (Hybrid PubMedBERT + SapBERT)

### Objectives
Optional hybrid ML layer that augments rules for missing/ambiguous fields. Rules remain primary.

### Architecture
1. Rules run first → assign `_source="rule"`, `_confidence`
2. If `ml_mode in (hybrid, full)` and field missing/below `ml_threshold` → ML inference
3. ML output accepted if `confidence >= ml_threshold`; else `_needs_review=True`
4. LLM called only for fields still unresolved after ML (when `use_llm=True`)

### Models
- **GSE-MTL**: PubMedBERT backbone, NER + classification + binary heads (512 tokens)
- **GSM-MTL**: PubMedBERT backbone, NER + classification heads (384 tokens)
- **EntityLinker**: SapBERT embeddings + FAISS index for ontology linking

### Data Pipeline (D1–D4)
- `scripts/build_ml_corpus.py` — Extract raw corpus → `data/ml/v1/*.parquet`
- `scripts/generate_silver_labels.py` — Apply rules → silver labels (2,500 GSE + 100K GSM)
- `scripts/export_for_annotation.py` + `scripts/import_annotations.py` — Doccano workflow for gold (500 GSE + 20K GSM)
- `scripts/build_dataset.py` — Merge, split by GSE (70/15/15), write `splits.parquet`

### Training Pipeline (T1–T6)
```
ml/
├── models/          # gse_mtl.py, gsm_mtl.py, entity_linker.py
├── data/            # dataset.py, tokenizer.py
├── training/        # train.py, losses.py, evaluate.py
├── export/          # to_onnx.py, registry.py
└── requirements-ml.txt
```
- T1: Pretrain on silver (3 epochs, lr 2e-5)
- T2: Finetune on gold (6 epochs, early stop patience 2)
- T3: SapBERT linker training + threshold calibration
- T4: Temperature scaling on validation
- T5: ONNX int8 export
- T6: Registry at `ml_artifacts/ml-v1.0.0/`

### GEOtcha Integration
- New: `src/geotcha/ml/` — `inference.py` (MLHarmonizer), `loader.py`, `exceptions.py`
- Config additions: `ml_enabled`, `ml_mode`, `ml_model_dir`, `ml_model_version`, `ml_device`, `ml_batch_size`, `ml_threshold`, `ml_review_threshold`
- CLI additions: `--ml-mode off|hybrid|full`, `--ml-device`, `--ml-batch-size`, `--ml-threshold`
- Lazy imports: no ML deps loaded when `--ml-mode off`

### Dependencies (pyproject.toml)
```toml
ml = ["torch>=2.0", "onnxruntime>=1.17", "transformers>=4.40", "faiss-cpu>=1.8", "mlflow>=2.12"]
```

### Release Gates
- `disease` GSM F1 ≥ 0.90, `tissue` GSM F1 ≥ 0.90
- `responder_status` macro-F1 ≥ 0.88, `timepoint` exact match ≥ 0.90
- `gender` accuracy ≥ 0.96
- Hybrid mode: ≥10% completeness improvement over rules-only, ≤1% precision drop
- Throughput ≥ 65% of rules-only speed
- All existing tests pass with `--ml-mode off`

---

## Sequencing Constraints

```
0.2.0 (Reliability) ─┬─→ 0.3.0 (Performance) ─┐
                      │                          ├─→ 0.5.0 (UX & SDK)
                      └─→ 0.4.0 (Metadata)  ────┘         │
                           │                               │
                           └───────────────────────────────┴─→ 0.6.0 (ML)
```

- **0.2.0 → 0.3.0**: Streaming output depends on corrected resume merge
- **0.2.0 → 0.4.0**: Provenance `_source="llm"` needs LLM propagation fix
- **0.3.0 ∥ 0.4.0**: Can be developed in parallel (different file sets)
- **0.4.0 → 0.6.0**: ML layer uses provenance field schema from 0.4.0
- **ML data (D1–D4) can start after 0.2.0** ships; annotation is the long pole (6-8 weeks)

---

## Git Workflow (Per Milestone)

1. Branch from `main`: `feat/<milestone>-<version>`
2. Implement, write tests, ensure all tests pass (`pytest tests/ -v`)
3. Lint: `ruff check src/ tests/`
4. Bump version in `pyproject.toml` and `src/geotcha/__init__.py`
5. Merge to `main`, tag `v<version>`
6. Push to GitHub, publish to PyPI

---

## Verification

For each milestone, before tagging:
1. `pip install -e ".[dev]"` succeeds
2. `pytest tests/ -v` — all tests pass
3. `ruff check src/ tests/` — no lint errors
4. `geotcha --help` — CLI loads fast
5. Manual smoke test of the primary feature (resume, parallel run, provenance in output, etc.)
