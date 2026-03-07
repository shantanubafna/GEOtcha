#!/usr/bin/env python3
"""Build FAISS ontology indices for SapBERT entity linking.

Usage:
    python scripts/build_ml_index.py [--output DIR] [--model MODEL] [--batch-size N]

Encodes all ontology terms (tissue, disease, cell_type, treatment) with SapBERT
and stores FAISS inner-product indices for fast nearest-neighbor lookup.

Requirements:
    pip install geotcha[ml] faiss-cpu
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build SapBERT FAISS indices for GEOtcha")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output directory for index files (default: ~/.cache/geotcha/ml/v1/indices)",
    )
    parser.add_argument(
        "--model",
        default="cambridgeltl/SapBERT-from-PubMedBERT-fulltext",
        help="SapBERT model name or path",
    )
    parser.add_argument("--batch-size", type=int, default=64, help="Encoding batch size")
    args = parser.parse_args()

    # Resolve output directory
    if args.output:
        output_dir = args.output
    else:
        from platformdirs import user_cache_dir
        output_dir = Path(user_cache_dir("geotcha")) / "ml" / "v1" / "indices"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load SapBERT encoder
    logger.info("Loading SapBERT model: %s", args.model)
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        logger.error("sentence-transformers not installed. Run: pip install geotcha[ml]")
        sys.exit(1)

    try:
        import faiss  # noqa: F401
    except ImportError:
        logger.error("faiss not installed. Run: pip install faiss-cpu")
        sys.exit(1)

    encoder = SentenceTransformer(args.model)

    # Load ontology data
    from geotcha.harmonize.ontology import (
        CELL_TYPE_ONTOLOGY,
        DISEASE_ONTOLOGY,
        TISSUE_ONTOLOGY,
        TREATMENT_ONTOLOGY,
    )
    from geotcha.ml.index import ONTOLOGY_TYPES, build_index_from_ontology

    ontology_map = {
        "tissue": TISSUE_ONTOLOGY,
        "disease": DISEASE_ONTOLOGY,
        "cell_type": CELL_TYPE_ONTOLOGY,
        "treatment": TREATMENT_ONTOLOGY,
    }

    total_start = time.time()
    for ont_type in ONTOLOGY_TYPES:
        data = ontology_map[ont_type]
        logger.info("Building %s index (%d terms)...", ont_type, len(data))
        start = time.time()
        index = build_index_from_ontology(
            data, ont_type, encoder, batch_size=args.batch_size
        )
        index.save(output_dir)
        elapsed = time.time() - start
        logger.info("  %s: %d entries in %.1fs", ont_type, index.size, elapsed)

    total_elapsed = time.time() - total_start
    logger.info("All indices built in %.1fs → %s", total_elapsed, output_dir)


if __name__ == "__main__":
    main()
