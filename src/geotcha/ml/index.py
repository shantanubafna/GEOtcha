"""FAISS-backed ontology index for SapBERT entity linking."""
from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np

from geotcha.ml.exceptions import ModelNotFoundError

logger = logging.getLogger(__name__)

# Index file naming convention
_INDEX_SUFFIX = ".faiss"
_META_SUFFIX = ".meta.json"

# Supported ontology types
ONTOLOGY_TYPES = ("tissue", "disease", "cell_type", "treatment")


class OntologyIndex:
    """A single FAISS index for one ontology type.

    Stores embeddings of ontology term names and maps indices back to
    (canonical_name, ontology_id) tuples.
    """

    def __init__(
        self,
        index,  # faiss.IndexFlatIP
        names: list[str],
        ontology_ids: list[str],
        ontology_type: str,
    ) -> None:
        self._index = index
        self._names = names
        self._ontology_ids = ontology_ids
        self.ontology_type = ontology_type

    @property
    def size(self) -> int:
        return self._index.ntotal

    def search(
        self, embedding: np.ndarray, top_k: int = 1
    ) -> list[tuple[str, str, float]]:
        """Search the index for nearest neighbors.

        Args:
            embedding: Query embedding, shape (1, dim) or (dim,).
            top_k: Number of results to return.

        Returns:
            List of (canonical_name, ontology_id, similarity_score) tuples,
            sorted by descending similarity.
        """
        if embedding.ndim == 1:
            embedding = embedding.reshape(1, -1)

        # Normalize for cosine similarity (IndexFlatIP on unit vectors = cosine)
        norm = np.linalg.norm(embedding, axis=1, keepdims=True)
        if norm > 0:
            embedding = embedding / norm

        scores, indices = self._index.search(embedding.astype(np.float32), top_k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            results.append((self._names[idx], self._ontology_ids[idx], float(score)))
        return results

    @classmethod
    def load(cls, index_dir: Path, ontology_type: str) -> OntologyIndex:
        """Load a pre-built index from disk.

        Expects:
            - {index_dir}/{ontology_type}.faiss
            - {index_dir}/{ontology_type}.meta.json
        """
        import faiss

        index_path = index_dir / f"{ontology_type}{_INDEX_SUFFIX}"
        meta_path = index_dir / f"{ontology_type}{_META_SUFFIX}"

        if not index_path.exists():
            raise ModelNotFoundError(
                f"Index file not found: {index_path}. "
                "Run 'geotcha ml build-index' or 'geotcha ml download' first."
            )
        if not meta_path.exists():
            raise ModelNotFoundError(f"Metadata file not found: {meta_path}")

        index = faiss.read_index(str(index_path))
        with open(meta_path) as f:
            meta = json.load(f)

        logger.info(
            "Loaded %s index: %d entries from %s",
            ontology_type,
            index.ntotal,
            index_path,
        )
        return cls(
            index=index,
            names=meta["names"],
            ontology_ids=meta["ontology_ids"],
            ontology_type=ontology_type,
        )

    def save(self, index_dir: Path) -> None:
        """Save index and metadata to disk."""
        import faiss

        index_dir.mkdir(parents=True, exist_ok=True)
        index_path = index_dir / f"{self.ontology_type}{_INDEX_SUFFIX}"
        meta_path = index_dir / f"{self.ontology_type}{_META_SUFFIX}"

        faiss.write_index(self._index, str(index_path))
        with open(meta_path, "w") as f:
            json.dump(
                {"names": self._names, "ontology_ids": self._ontology_ids},
                f,
            )
        logger.info("Saved %s index (%d entries) to %s", self.ontology_type, self.size, index_path)


class OntologyIndexSet:
    """Collection of FAISS indices for all ontology types.

    Maps field names to their corresponding OntologyIndex.
    """

    def __init__(self, indices: dict[str, OntologyIndex] | None = None) -> None:
        self._indices = indices or {}

    def __contains__(self, ontology_type: str) -> bool:
        return ontology_type in self._indices

    def get(self, ontology_type: str) -> OntologyIndex | None:
        return self._indices.get(ontology_type)

    @classmethod
    def load(cls, index_dir: Path) -> OntologyIndexSet:
        """Load all available ontology indices from a directory."""
        indices: dict[str, OntologyIndex] = {}
        for ont_type in ONTOLOGY_TYPES:
            index_path = index_dir / f"{ont_type}{_INDEX_SUFFIX}"
            if index_path.exists():
                try:
                    indices[ont_type] = OntologyIndex.load(index_dir, ont_type)
                except Exception as e:
                    logger.warning("Failed to load %s index: %s", ont_type, e)
        if not indices:
            raise ModelNotFoundError(
                f"No ontology indices found in {index_dir}. "
                "Run 'geotcha ml build-index' or 'geotcha ml download' first."
            )
        logger.info("Loaded %d ontology indices from %s", len(indices), index_dir)
        return cls(indices)

    @property
    def available_types(self) -> list[str]:
        return list(self._indices.keys())


def build_index_from_ontology(
    ontology_data: dict[str, tuple[str, str]],
    ontology_type: str,
    encoder,
    batch_size: int = 64,
) -> OntologyIndex:
    """Build a FAISS index from an ontology dict using a SapBERT encoder.

    Args:
        ontology_data: Dict mapping lowercase key -> (canonical_name, ontology_id).
        ontology_type: One of ONTOLOGY_TYPES.
        encoder: SentenceTransformer model for encoding terms.
        batch_size: Encoding batch size.

    Returns:
        An OntologyIndex ready for search or saving.
    """
    import faiss

    names = []
    ontology_ids = []
    texts = []

    for _key, (name, ont_id) in ontology_data.items():
        names.append(name)
        ontology_ids.append(ont_id)
        texts.append(name)

    if not texts:
        raise ValueError(f"Empty ontology data for {ontology_type}")

    # Encode all terms
    logger.info("Encoding %d %s terms...", len(texts), ontology_type)
    embeddings = encoder.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    embeddings = np.array(embeddings, dtype=np.float32)

    # Build FAISS index (inner product on normalized vectors = cosine similarity)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    logger.info("Built %s index: %d entries, dim=%d", ontology_type, index.ntotal, dim)
    return OntologyIndex(
        index=index,
        names=names,
        ontology_ids=ontology_ids,
        ontology_type=ontology_type,
    )
