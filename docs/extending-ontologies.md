# Extending Ontologies

GEOtcha ships ~27,000 ontology terms from four sources. You can regenerate or extend them using the build script.

## Shipped Ontologies

| File | Source | Entries | Description |
|------|--------|---------|-------------|
| `tissue.json` | UBERON | ~4,000 | Human anatomical structures |
| `disease.json` | DOID | ~12,000 | Disease Ontology (all non-obsolete) |
| `cell_type.json` | CL | ~3,000 | Cell Ontology (CL: prefix) |
| `treatment.json` | Curated | ~300 | Drugs with ChEBI IDs |
| `synonyms.json` | All | ~27,000 | EXACT synonyms from OBO sources |

## Regenerating Ontologies

```bash
python scripts/build_ontologies.py
```

This downloads OBO files from official sources, parses them, and generates the JSON files in `src/geotcha/data/ontology/`.

### Source Configuration

Each ontology has a config file in `scripts/sources/`:

- `uberon_config.json` — UBERON OBO URL, BFS roots, excluded terms
- `doid_config.json` — DOID OBO URL, filtering rules
- `cl_config.json` — CL OBO URL, CL: prefix filter
- `treatments_curated.json` — Hand-curated drug list with ChEBI IDs

### Adding Custom Terms

To add custom ontology entries, edit the relevant JSON file directly:

```json
{
  "my custom tissue": ["my custom tissue", "UBERON:9999999"]
}
```

Or add entries to the `extra_entries` section in the source config.

## JSON Format

Each ontology file is a JSON dict mapping lowercase keys to `[canonical_name, ontology_id]` tuples:

```json
{
  "colon": ["colon", "UBERON:0001155"],
  "liver": ["liver", "UBERON:0002107"]
}
```

The synonyms file maps synonyms to their canonical keys:

```json
{
  "hepatocyte": "hepatocyte",
  "liver cell": "hepatocyte"
}
```

## Rebuilding ML Indices

After updating ontologies, rebuild the FAISS indices for ML entity linking:

```bash
geotcha ml build-index
```
