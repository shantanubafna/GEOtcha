# Changelog

All notable changes to GEOtcha are documented here.

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
