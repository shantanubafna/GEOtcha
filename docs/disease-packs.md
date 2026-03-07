# Disease Packs

Disease packs are pre-configured TOML bundles that optimize GEOtcha for specific research areas. They provide curated search terms, relevance keywords, and expected tissue/treatment lists.

## Available Packs

| Pack | Diseases | Search Terms | Tissues | Treatments |
|------|----------|-------------|---------|------------|
| `ibd` | IBD, UC, Crohn's | 5 | 13 | 14 |
| `oncology` | Cancer types | 10 | 17 | 19 |
| `neurodegeneration` | AD, PD, ALS, HD, MS | 11 | 13 | 10 |
| `autoimmune` | RA, SLE, psoriasis, AS | 11 | 9 | 15 |
| `metabolic` | T2D, T1D, NAFLD, obesity | 10 | 9 | 9 |

## Usage

### CLI

```bash
# List available packs
geotcha packs

# Use a pack with the run command
geotcha run "IBD" --pack ibd --harmonize

# Packs augment the query with optimized search terms
geotcha run "breast cancer" --pack oncology --subset 10 --harmonize
```

### Python SDK

```python
from geotcha.packs import load_pack, list_packs

# List all packs
print(list_packs())

# Load pack details
pack = load_pack("ibd")
print(pack.display_name)      # "Inflammatory Bowel Disease"
print(pack.search_terms)       # ["inflammatory bowel disease", "ulcerative colitis", ...]
print(pack.expected_tissues)   # ["colon", "ileum", "rectum", ...]
print(pack.expected_treatments)# ["infliximab", "adalimumab", ...]
```

## Pack Format

Packs are TOML files in `src/geotcha/data/packs/`:

```toml
[pack]
name = "ibd"
display_name = "Inflammatory Bowel Disease"
description = "IBD, Crohn's disease, and ulcerative colitis"

[search]
terms = ["inflammatory bowel disease", "ulcerative colitis", ...]
relevance_keywords = ["UC", "CD", "colitis", ...]

[filters]
expected_tissues = ["colon", "ileum", "rectum", ...]
expected_treatments = ["infliximab", "adalimumab", ...]
```

## Creating Custom Packs

You can create custom packs by adding TOML files to the packs directory or by providing them programmatically:

```python
from geotcha.packs import DiseasePack

my_pack = DiseasePack(
    name="custom",
    display_name="My Custom Pack",
    description="Custom research focus",
    search_terms=["my disease", "my disease subtype"],
    expected_tissues=["liver", "blood"],
)
```
