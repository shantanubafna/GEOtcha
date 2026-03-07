# Ontology Build Scripts

Build GEOtcha's ontology JSON files from official OBO Foundry sources.

## Quick Start

```bash
# Build all ontologies (downloads ~110 MB of OBO files on first run)
python scripts/build_ontologies.py

# Build specific ontology
python scripts/build_ontologies.py --only tissue

# Show stats without writing
python scripts/build_ontologies.py --dry-run
```

## Sources

| Ontology | Source | File | Description |
|----------|--------|------|-------------|
| Tissue | [UBERON](http://obofoundry.org/ontology/uberon) | `tissue.json` | Anatomical structures, organs, body fluids |
| Disease | [DOID](http://obofoundry.org/ontology/doid) | `disease.json` | Human diseases |
| Cell Type | [CL](http://obofoundry.org/ontology/cl) | `cell_type.json` | Cell types |
| Treatment | Curated | `treatment.json` | Drugs, stimuli, reagents (with ChEBI IDs) |

## How It Works

1. Downloads OBO files from OBO Foundry (cached in `scripts/.obo_cache/`)
2. Parses term blocks (id, name, synonyms, is_a hierarchy)
3. BFS from configured root terms with depth limits
4. Filters out obsolete/irrelevant terms (embryonic, non-mammalian, etc.)
5. Writes JSON to `src/geotcha/data/ontology/`

## Configuration

Source configs are in `scripts/sources/`:

- `uberon_config.json` — UBERON roots, depth, exclude patterns
- `doid_config.json` — DOID roots, depth, exclude patterns
- `cl_config.json` — CL roots, depth, exclude patterns
- `treatments_curated.json` — Curated drug entries with ChEBI IDs and synonyms

## Regenerating

After modifying configs or updating to new OBO releases:

```bash
# Clear cache to force fresh download
rm -rf scripts/.obo_cache/

# Rebuild
python scripts/build_ontologies.py
```

## No External Dependencies

The build script uses only Python stdlib (no pronto or other OBO libraries).
It includes a lightweight OBO parser that extracts term ID, name, synonyms,
and is_a relationships — everything needed for GEOtcha's lookup tables.
