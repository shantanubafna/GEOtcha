#!/usr/bin/env python3
"""Build GEOtcha ontology JSON files from official OBO sources.

Downloads UBERON, DOID, and CL ontologies from OBO Foundry, parses them,
filters to RNA-seq-relevant subsets, and generates JSON lookup files.

Treatment ontology is built from a curated source file.
Synonyms are aggregated from all ontology sources.

No external dependencies required (Python 3.10+ stdlib only).

Usage:
    python scripts/build_ontologies.py                   # Build all
    python scripts/build_ontologies.py --only tissue      # Build one
    python scripts/build_ontologies.py --dry-run          # Show stats only
    python scripts/build_ontologies.py --cache-dir /tmp   # Custom cache
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_ROOT / "src" / "geotcha" / "data" / "ontology"
SOURCES_DIR = SCRIPT_DIR / "sources"
DEFAULT_CACHE = SCRIPT_DIR / ".obo_cache"

OBO_SOURCES = {
    "uberon": "http://purl.obolibrary.org/obo/uberon.obo",
    "doid": "http://purl.obolibrary.org/obo/doid.obo",
    "cl": "http://purl.obolibrary.org/obo/cl.obo",
}


# ── OBO Parser ───────────────────────────────────────────────────────


@dataclass
class OBOTerm:
    """A parsed OBO ontology term."""

    id: str
    name: str
    synonyms: list[tuple[str, str]] = field(default_factory=list)
    is_a: list[str] = field(default_factory=list)
    obsolete: bool = False
    namespace: str = ""


def parse_obo(filepath: Path) -> dict[str, OBOTerm]:
    """Parse an OBO file into {term_id: OBOTerm}."""
    terms: dict[str, OBOTerm] = {}
    in_term = False
    cur: dict[str, Any] = {}

    def _flush() -> None:
        if cur.get("id") and cur.get("name"):
            terms[cur["id"]] = OBOTerm(
                id=cur["id"],
                name=cur["name"],
                synonyms=cur.get("synonyms", []),
                is_a=cur.get("is_a", []),
                obsolete=cur.get("obsolete", False),
                namespace=cur.get("namespace", ""),
            )

    with open(filepath, encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")

            if line == "[Term]":
                if in_term:
                    _flush()
                in_term = True
                cur = {"synonyms": [], "is_a": []}
            elif line.startswith("[") and line.endswith("]"):
                if in_term:
                    _flush()
                in_term = False
                cur = {}
            elif in_term:
                if line.startswith("id: "):
                    cur["id"] = line[4:].strip()
                elif line.startswith("name: "):
                    cur["name"] = line[6:].strip()
                elif line.startswith("synonym: "):
                    m = re.match(r'synonym: "(.+?)" (\w+)', line)
                    if m:
                        cur.setdefault("synonyms", []).append(
                            (m.group(1), m.group(2))
                        )
                elif line.startswith("is_a: "):
                    # Strip comment (! ...) and annotation ({...})
                    raw_id = line[6:].split("!")[0].split("{")[0].strip()
                    cur.setdefault("is_a", []).append(raw_id)
                elif line == "is_obsolete: true":
                    cur["obsolete"] = True
                elif line.startswith("namespace: "):
                    cur["namespace"] = line[11:].strip()

    if in_term:
        _flush()

    return terms


# ── Hierarchy Helpers ────────────────────────────────────────────────


def build_children_map(terms: dict[str, OBOTerm]) -> dict[str, set[str]]:
    """Build {parent_id: set(child_ids)} from is_a relations."""
    children: dict[str, set[str]] = defaultdict(set)
    for term in terms.values():
        if not term.obsolete:
            for parent_id in term.is_a:
                children[parent_id].add(term.id)
    return dict(children)


def bfs_descendants(
    children_map: dict[str, set[str]],
    root_ids: list[str],
    max_depth: int | None = None,
) -> set[str]:
    """BFS from root terms, return descendant IDs within max_depth."""
    visited: set[str] = set()
    queue: deque[tuple[str, int]] = deque()

    for rid in root_ids:
        queue.append((rid, 0))

    while queue:
        term_id, depth = queue.popleft()
        if term_id in visited:
            continue
        visited.add(term_id)

        if max_depth is not None and depth >= max_depth:
            continue

        for child_id in children_map.get(term_id, set()):
            if child_id not in visited:
                queue.append((child_id, depth + 1))

    return visited


# ── Download Helper ──────────────────────────────────────────────────


def download_obo(name: str, url: str, cache_dir: Path) -> Path:
    """Download an OBO file, using cache if available."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached = cache_dir / f"{name}.obo"

    if cached.exists():
        size_mb = cached.stat().st_size / (1024 * 1024)
        print(f"  Using cached {name}.obo ({size_mb:.1f} MB)")
        return cached

    print(f"  Downloading {name}.obo from {url} ...")
    urllib.request.urlretrieve(url, cached)
    size_mb = cached.stat().st_size / (1024 * 1024)
    print(f"  Downloaded {name}.obo ({size_mb:.1f} MB)")
    return cached


# ── Entry Extraction ─────────────────────────────────────────────────


def extract_entries(
    terms: dict[str, OBOTerm],
    keep_ids: set[str],
    exclude_patterns: list[str] | None = None,
    id_prefix: str | None = None,
) -> tuple[dict[str, list[str]], dict[str, str]]:
    """Extract ontology entries and synonyms from filtered terms.

    Returns:
        entries: {lowercase_key: [canonical_name, ontology_id]}
        synonyms: {lowercase_synonym: lowercase_canonical_key}
    """
    exclude = [p.lower() for p in (exclude_patterns or [])]
    entries: dict[str, list[str]] = {}
    synonyms: dict[str, str] = {}

    for term_id in keep_ids:
        if id_prefix and not term_id.startswith(id_prefix):
            continue

        term = terms.get(term_id)
        if not term or term.obsolete or not term.name:
            continue

        name_lower = term.name.lower()

        if any(pat in name_lower for pat in exclude):
            continue

        entries[name_lower] = [term.name, term.id]

        for syn_text, syn_scope in term.synonyms:
            if syn_scope == "EXACT":
                syn_lower = syn_text.lower()
                if syn_lower != name_lower and syn_lower not in entries:
                    synonyms[syn_lower] = name_lower

    return entries, synonyms


# ── Per-Ontology Builders ───────────────────────────────────────────


def _load_config(filename: str) -> dict[str, Any]:
    """Load a source config JSON file."""
    with open(SOURCES_DIR / filename) as f:
        return json.load(f)


def build_tissue(cache_dir: Path) -> tuple[dict, dict]:
    """Build tissue.json from UBERON ontology."""
    config = _load_config("uberon_config.json")
    obo_path = download_obo("uberon", OBO_SOURCES["uberon"], cache_dir)

    print("  Parsing UBERON ...")
    terms = parse_obo(obo_path)
    print(f"  Parsed {len(terms)} terms")

    children_map = build_children_map(terms)
    keep_ids = bfs_descendants(
        children_map, config["roots"], config.get("max_depth"),
    )

    for tid in config.get("include", []):
        keep_ids.add(tid)

    # Remove root terms (too generic for lookup, e.g. "cell", "disease")
    for rid in config["roots"]:
        keep_ids.discard(rid)

    entries, synonyms = extract_entries(
        terms, keep_ids, config.get("exclude_patterns"), config.get("id_prefix"),
    )

    # Merge extra entries from config (e.g., non-UBERON terms like "biopsy")
    for key, val in config.get("extra_entries", {}).items():
        entries.setdefault(key, val)

    # Extra synonyms are authoritative (override OBO-sourced ones)
    for syn, canonical in config.get("extra_synonyms", {}).items():
        synonyms[syn] = canonical

    return entries, synonyms


def build_disease(cache_dir: Path) -> tuple[dict, dict]:
    """Build disease.json from Disease Ontology."""
    config = _load_config("doid_config.json")
    obo_path = download_obo("doid", OBO_SOURCES["doid"], cache_dir)

    print("  Parsing DOID ...")
    terms = parse_obo(obo_path)
    print(f"  Parsed {len(terms)} terms")

    children_map = build_children_map(terms)
    keep_ids = bfs_descendants(
        children_map, config["roots"], config.get("max_depth"),
    )

    for tid in config.get("include", []):
        keep_ids.add(tid)

    for rid in config["roots"]:
        keep_ids.discard(rid)

    entries, synonyms = extract_entries(
        terms, keep_ids, config.get("exclude_patterns"), config.get("id_prefix"),
    )

    for key, val in config.get("extra_entries", {}).items():
        entries.setdefault(key, val)

    # Extra synonyms are authoritative (override OBO-sourced ones)
    for syn, canonical in config.get("extra_synonyms", {}).items():
        synonyms[syn] = canonical

    return entries, synonyms


def build_cell_type(cache_dir: Path) -> tuple[dict, dict]:
    """Build cell_type.json from Cell Ontology."""
    config = _load_config("cl_config.json")
    obo_path = download_obo("cl", OBO_SOURCES["cl"], cache_dir)

    print("  Parsing CL ...")
    terms = parse_obo(obo_path)
    print(f"  Parsed {len(terms)} terms")

    children_map = build_children_map(terms)
    keep_ids = bfs_descendants(
        children_map, config["roots"], config.get("max_depth"),
    )

    for tid in config.get("include", []):
        keep_ids.add(tid)

    for rid in config["roots"]:
        keep_ids.discard(rid)

    entries, synonyms = extract_entries(
        terms, keep_ids, config.get("exclude_patterns"), config.get("id_prefix"),
    )

    for key, val in config.get("extra_entries", {}).items():
        entries.setdefault(key, val)

    # Extra synonyms are authoritative (override OBO-sourced ones)
    for syn, canonical in config.get("extra_synonyms", {}).items():
        synonyms[syn] = canonical

    return entries, synonyms


def build_treatment() -> tuple[dict, dict]:
    """Build treatment.json from curated source file."""
    source_path = SOURCES_DIR / "treatments_curated.json"
    with open(source_path) as f:
        data = json.load(f)
    return data["entries"], data["synonyms"]


# ── Output Writers ───────────────────────────────────────────────────


def write_ontology(
    entries: dict[str, list[str]], filepath: Path, *, compact: bool = False,
) -> None:
    """Write sorted ontology JSON file."""
    sorted_entries = dict(sorted(entries.items()))
    indent = None if compact else 2
    sep = (",", ":") if compact else (",", ": ")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(sorted_entries, f, indent=indent, separators=sep, ensure_ascii=False)
        f.write("\n")


def write_synonyms(
    all_synonyms: dict[str, dict[str, str]],
    filepath: Path,
    *,
    compact: bool = False,
) -> None:
    """Write aggregated synonyms.json."""
    sorted_syns: dict[str, dict[str, str]] = {}
    for category in sorted(all_synonyms):
        sorted_syns[category] = dict(sorted(all_synonyms[category].items()))
    indent = None if compact else 2
    sep = (",", ":") if compact else (",", ": ")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(sorted_syns, f, indent=indent, separators=sep, ensure_ascii=False)
        f.write("\n")


# ── Main ─────────────────────────────────────────────────────────────


BUILDERS = {
    "tissue": ("tissue.json", True),
    "disease": ("disease.json", True),
    "cell_type": ("cell_type.json", True),
    "treatment": ("treatment.json", False),
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build GEOtcha ontology JSON files from OBO sources",
    )
    parser.add_argument(
        "--only",
        nargs="+",
        choices=list(BUILDERS),
        help="Build only specified ontologies",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=DEFAULT_CACHE,
        help=f"Cache directory for OBO downloads (default: {DEFAULT_CACHE})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help=f"Output directory for JSON files (default: {OUTPUT_DIR})",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Write compact JSON (no indentation) to reduce file size",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and show stats without writing files",
    )
    args = parser.parse_args()

    targets = set(args.only) if args.only else set(BUILDERS)
    all_synonyms: dict[str, dict[str, str]] = {}

    print("Building GEOtcha ontologies ...")
    print(f"  Output: {args.output_dir}")

    obo_builders = {
        "tissue": lambda: build_tissue(args.cache_dir),
        "disease": lambda: build_disease(args.cache_dir),
        "cell_type": lambda: build_cell_type(args.cache_dir),
        "treatment": build_treatment,
    }

    for name in BUILDERS:
        if name not in targets:
            continue

        filename = BUILDERS[name][0]
        print(f"\n{'=' * 50}")
        print(f"Building {name} ...")

        try:
            entries, synonyms = obo_builders[name]()
        except Exception as exc:
            print(f"  ERROR: {exc}", file=sys.stderr)
            continue

        print(f"  Entries: {len(entries)}")
        print(f"  Synonyms: {len(synonyms)}")

        if not args.dry_run:
            args.output_dir.mkdir(parents=True, exist_ok=True)
            write_ontology(entries, args.output_dir / filename, compact=args.compact)
            print(f"  Written: {filename}")

        all_synonyms[name] = synonyms

    if not args.dry_run and all_synonyms:
        syn_path = args.output_dir / "synonyms.json"
        # Preserve synonyms for categories not rebuilt
        if syn_path.exists():
            with open(syn_path) as f:
                existing = json.load(f)
            for cat, syns in existing.items():
                if cat not in all_synonyms:
                    all_synonyms[cat] = syns

        write_synonyms(all_synonyms, syn_path, compact=args.compact)
        total = sum(len(s) for s in all_synonyms.values())
        print(f"\nWritten: synonyms.json ({total} total synonyms)")

    print("\nDone!")


if __name__ == "__main__":
    main()
