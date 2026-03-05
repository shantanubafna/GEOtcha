# Changelog

All notable changes to GEOtcha are documented here.

## [0.6.0] – 2026-03-05

### Added
- **ML harmonization scaffold**: new `src/geotcha/ml/` module with `MLHarmonizer`, GLiNER NER, and SapBERT entity linking (all lazy-imported).
- **`--ml-mode` flag**: `off` (default), `hybrid` (ML fills gaps), or `full` (ML runs on all fields). Available on `run` and `extract` commands.
- **`--ml-device`**, **`--ml-batch-size`**, **`--ml-threshold`** CLI flags for ML tuning.
- **`needs_review` field** on `GSMRecord` and `GSERecord`: flagged when ML produces low-confidence predictions.
- **`config validate` command**: validates ML mode, threshold, device, and review threshold settings.
- **Python SDK** (`geotcha.api.GEOtchaClient`): programmatic interface with `search()`, `extract()`, `harmonize(ml_mode=...)`, `export()`, and `run()`.
- **`ml` optional dependency group**: `pip install geotcha[ml]` installs GLiNER, sentence-transformers, and ONNX Runtime.
- 7 new ML config fields in `Settings` (all with sensible defaults).
- Three-tier harmonization chain: rules → ML → LLM, each layer only upgrading low-confidence fields.

### Internal
- 298 tests passing (all existing + new ML/config tests).
- `_harmonize_record` gains `ml_harmonizer` parameter; all existing callers unchanged when ML is off.

## [0.4.0] – 2026-02-28

### Added
- **Per-field provenance**: every harmonized field now tracks `_source`, `_confidence`, and `_ontology_id`.
- **Confidence tiers**: exact match (1.0), synonym (0.85), substring (0.70), raw fallback (0.50).
- **UBERON tissue ontology** and **Disease Ontology** lookups with confidence scoring.
- **Review queue**: `review_queue.csv` written for records with confidence < 0.65.
- `NormResult` NamedTuple and `_apply_norm` helper in `rules.py`.

## [0.3.0] – 2026-02-26

### Added
- **Parallel extraction**: `ThreadPoolExecutor` with `--max-workers` (capped at 2 without API key, 6 with).
- **Streaming GSM writes**: sample files written as each GSE completes.
- **Order preservation**: records returned in original submission order.
- **Entrez response caching**: `--cache-ttl-days` for reducing repeat API calls.
- **Relevance filtering**: disease keyword matching with word-boundary awareness.

## [0.2.0] – 2026-02-24

### Fixed
- `geotcha resume` now correctly merges prior `gse_summary.csv` rows with newly extracted records (dedup by gse_id). Previously, resuming overwrote the summary with only the remaining records.
- LLM provider/key/model settings are now correctly threaded from `--llm-provider` / config into harmonization and relevance calls instead of defaulting to OpenAI.
- State writes are now atomic (write to `.tmp` then `os.replace`) — a process kill mid-write no longer corrupts `state.json`.

### Added
- **Run manifest**: each run writes `manifest.json` in the run state directory with run_id, query, timestamps, counts, output paths, and a masked settings snapshot.
- **`--yes` / `-y` flag**: auto-confirms all prompts for non-interactive use.
- **`--non-interactive` flag**: same as `--yes`, disables all interactive prompts and uses defaults.
- **Dynamic retry count**: `max_retries` setting now controls NCBI Entrez retry attempts (was hardcoded to 3).

### Internal
- 101 new tests (`tests/test_pipeline.py`, `tests/test_cache.py`, `tests/test_config.py`) — 163 total.

## [0.1.1] – 2026-02-20

- Hotfix: Python 3.10 support (`tomli` fallback), coverage config fix, CI/badge additions.

## [0.1.0] – 2026-02-20

- Initial release: search → filter → extract → harmonize → CSV/TSV pipeline.
