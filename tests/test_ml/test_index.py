"""Tests for FAISS ontology index module."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import numpy as np
import pytest

from geotcha.ml.exceptions import ModelNotFoundError

# ---------------------------------------------------------------------------
# Mock faiss so tests run without faiss-cpu installed
# ---------------------------------------------------------------------------

class _FakeIndex:
    """Minimal stand-in for faiss.IndexFlatIP."""

    def __init__(self, dim: int):
        self.dim = dim
        self._vectors: list[np.ndarray] = []
        self.ntotal = 0

    def add(self, vectors: np.ndarray) -> None:
        for v in vectors:
            self._vectors.append(v.copy())
        self.ntotal = len(self._vectors)

    def search(self, query: np.ndarray, k: int):
        """Brute-force inner product search."""
        if not self._vectors:
            return np.array([[-1.0] * k]), np.array([[-1] * k])
        mat = np.stack(self._vectors)
        scores = (query @ mat.T)[0]
        top_k = min(k, len(scores))
        top_indices = np.argsort(-scores)[:top_k]
        result_scores = scores[top_indices].reshape(1, -1)
        result_indices = top_indices.reshape(1, -1)
        return result_scores, result_indices


@pytest.fixture(autouse=True)
def _mock_faiss(monkeypatch):
    """Inject a fake faiss module for all tests in this file."""
    fake_faiss = MagicMock()
    fake_faiss.IndexFlatIP = _FakeIndex

    def _read_index(path):
        raise FileNotFoundError(f"No real faiss in tests: {path}")

    def _write_index(index, path):
        pass  # no-op in tests

    fake_faiss.read_index = _read_index
    fake_faiss.write_index = _write_index

    monkeypatch.setitem(__import__("sys").modules, "faiss", fake_faiss)
    yield fake_faiss


# ---------------------------------------------------------------------------
# OntologyIndex
# ---------------------------------------------------------------------------

class TestOntologyIndex:
    def test_build_and_search(self):
        from geotcha.ml.index import OntologyIndex

        dim = 8
        names = ["colon", "liver", "lung"]
        ont_ids = ["UBERON:001", "UBERON:002", "UBERON:003"]

        # Create embeddings — make "colon" and query similar
        vecs = np.random.randn(3, dim).astype(np.float32)
        vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)

        index = _FakeIndex(dim)
        index.add(vecs)

        ont_index = OntologyIndex(
            index=index, names=names, ontology_ids=ont_ids, ontology_type="tissue"
        )

        assert ont_index.size == 3
        assert ont_index.ontology_type == "tissue"

        # Search with the first vector — should return "colon"
        results = ont_index.search(vecs[0], top_k=1)
        assert len(results) == 1
        assert results[0][0] == "colon"
        assert results[0][1] == "UBERON:001"
        assert results[0][2] > 0.99  # self-similarity ≈ 1.0

    def test_search_top_k(self):
        from geotcha.ml.index import OntologyIndex

        dim = 4
        vecs = np.eye(3, dim, dtype=np.float32)
        index = _FakeIndex(dim)
        index.add(vecs)

        ont_index = OntologyIndex(
            index=index,
            names=["a", "b", "c"],
            ontology_ids=["ID:1", "ID:2", "ID:3"],
            ontology_type="disease",
        )

        results = ont_index.search(vecs[1], top_k=3)
        assert len(results) == 3
        assert results[0][0] == "b"  # highest similarity to itself

    def test_search_1d_input(self):
        from geotcha.ml.index import OntologyIndex

        dim = 4
        vecs = np.eye(2, dim, dtype=np.float32)
        index = _FakeIndex(dim)
        index.add(vecs)

        ont_index = OntologyIndex(
            index=index,
            names=["x", "y"],
            ontology_ids=["X:1", "Y:1"],
            ontology_type="tissue",
        )

        # Pass 1D vector instead of 2D
        results = ont_index.search(vecs[0].flatten(), top_k=1)
        assert len(results) == 1

    def test_save(self, tmp_path, _mock_faiss):
        from geotcha.ml.index import OntologyIndex

        index = _FakeIndex(4)
        index.add(np.eye(2, 4, dtype=np.float32))

        ont_index = OntologyIndex(
            index=index,
            names=["a", "b"],
            ontology_ids=["A:1", "B:1"],
            ontology_type="tissue",
        )
        ont_index.save(tmp_path)

        meta_path = tmp_path / "tissue.meta.json"
        assert meta_path.exists()
        meta = json.loads(meta_path.read_text())
        assert meta["names"] == ["a", "b"]
        assert meta["ontology_ids"] == ["A:1", "B:1"]


# ---------------------------------------------------------------------------
# OntologyIndexSet
# ---------------------------------------------------------------------------

class TestOntologyIndexSet:
    def test_contains_and_get(self):
        from geotcha.ml.index import OntologyIndex, OntologyIndexSet

        idx = OntologyIndex(
            index=_FakeIndex(4),
            names=["x"],
            ontology_ids=["X:1"],
            ontology_type="tissue",
        )
        idx_set = OntologyIndexSet({"tissue": idx})

        assert "tissue" in idx_set
        assert "disease" not in idx_set
        assert idx_set.get("tissue") is idx
        assert idx_set.get("disease") is None
        assert idx_set.available_types == ["tissue"]

    def test_load_empty_dir_raises(self, tmp_path):
        from geotcha.ml.index import OntologyIndexSet

        with pytest.raises(ModelNotFoundError, match="No ontology indices found"):
            OntologyIndexSet.load(tmp_path)


# ---------------------------------------------------------------------------
# build_index_from_ontology
# ---------------------------------------------------------------------------

class TestBuildIndexFromOntology:
    def test_build(self):
        from geotcha.ml.index import build_index_from_ontology

        ontology_data = {
            "colon": ("colon", "UBERON:0001155"),
            "liver": ("liver", "UBERON:0002107"),
        }
        mock_encoder = MagicMock()
        mock_encoder.encode.return_value = np.random.randn(2, 8).astype(np.float32)

        idx = build_index_from_ontology(ontology_data, "tissue", mock_encoder, batch_size=32)
        assert idx.size == 2
        assert idx.ontology_type == "tissue"
        mock_encoder.encode.assert_called_once()

    def test_empty_raises(self):
        from geotcha.ml.index import build_index_from_ontology

        with pytest.raises(ValueError, match="Empty ontology data"):
            build_index_from_ontology({}, "tissue", MagicMock())


# ---------------------------------------------------------------------------
# _link_entity in MLHarmonizer
# ---------------------------------------------------------------------------

class TestLinkEntity:
    def test_no_linker_returns_none(self):
        from geotcha.ml.inference import MLHarmonizer

        h = MLHarmonizer(linker_model=None)
        result = h._link_entity("colon", "tissue")
        assert result == (None, 0.0)

    def test_no_index_set_returns_none(self):
        from geotcha.ml.inference import MLHarmonizer

        h = MLHarmonizer(linker_model=MagicMock(), index_set=None)
        result = h._link_entity("colon", "tissue")
        assert result == (None, 0.0)

    def test_field_not_in_index_map(self):
        from geotcha.ml.inference import MLHarmonizer

        h = MLHarmonizer(linker_model=MagicMock(), index_set=MagicMock())
        result = h._link_entity("male", "gender")
        assert result == (None, 0.0)

    def test_successful_linking(self):
        from geotcha.ml.index import OntologyIndex, OntologyIndexSet
        from geotcha.ml.inference import MLHarmonizer

        dim = 8
        vecs = np.eye(2, dim, dtype=np.float32)
        index = _FakeIndex(dim)
        index.add(vecs)

        ont_index = OntologyIndex(
            index=index,
            names=["colon", "liver"],
            ontology_ids=["UBERON:0001155", "UBERON:0002107"],
            ontology_type="tissue",
        )
        idx_set = OntologyIndexSet({"tissue": ont_index})

        mock_linker = MagicMock()
        # Return embedding similar to first entry ("colon")
        mock_linker.encode.return_value = vecs[0:1]

        h = MLHarmonizer(linker_model=mock_linker, index_set=idx_set)
        ontology_id, score = h._link_entity("colon biopsy", "tissue")

        assert ontology_id == "UBERON:0001155"
        assert score > 0.7

    def test_low_score_returns_none(self):
        from geotcha.ml.index import OntologyIndex, OntologyIndexSet
        from geotcha.ml.inference import MLHarmonizer

        dim = 8
        vecs = np.eye(2, dim, dtype=np.float32)
        index = _FakeIndex(dim)
        index.add(vecs)

        ont_index = OntologyIndex(
            index=index,
            names=["colon", "liver"],
            ontology_ids=["UBERON:0001155", "UBERON:0002107"],
            ontology_type="tissue",
        )
        idx_set = OntologyIndexSet({"tissue": ont_index})

        mock_linker = MagicMock()
        # Return a random vector that won't match well
        random_vec = np.random.randn(1, dim).astype(np.float32)
        random_vec /= np.linalg.norm(random_vec)
        # Make it orthogonal to both entries to ensure low score
        random_vec = np.zeros((1, dim), dtype=np.float32)
        random_vec[0, 7] = 1.0  # vecs use dims 0 and 1
        mock_linker.encode.return_value = random_vec

        h = MLHarmonizer(linker_model=mock_linker, index_set=idx_set)
        ontology_id, score = h._link_entity("totally unrelated", "tissue")

        assert ontology_id is None

    def test_exception_returns_none(self):
        from geotcha.ml.inference import MLHarmonizer

        mock_linker = MagicMock()
        mock_linker.encode.side_effect = RuntimeError("encode failed")

        mock_idx_set = MagicMock()
        mock_idx_set.get.return_value = MagicMock()

        h = MLHarmonizer(linker_model=mock_linker, index_set=mock_idx_set)
        result = h._link_entity("colon", "tissue")
        assert result == (None, 0.0)
