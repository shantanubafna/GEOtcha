"""Tests for ML model loader."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from geotcha.ml.exceptions import ModelNotFoundError
from geotcha.ml.loader import (
    _resolve_device,
    load_linker,
    load_ner_model,
    resolve_model_dir,
)


class TestResolveDevice:
    def test_explicit_device(self):
        assert _resolve_device("cuda") == "cuda"
        assert _resolve_device("cpu") == "cpu"
        assert _resolve_device("mps") == "mps"

    def test_auto_no_torch(self):
        with patch.dict("sys.modules", {"torch": None}):
            assert _resolve_device("auto") == "cpu"

    def test_auto_cuda(self):
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        with patch.dict("sys.modules", {"torch": mock_torch}):
            assert _resolve_device("auto") == "cuda"

    def test_auto_mps(self):
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps.is_available.return_value = True
        with patch.dict("sys.modules", {"torch": mock_torch}):
            assert _resolve_device("auto") == "mps"


class TestResolveModelDir:
    def test_explicit_path(self, tmp_path):
        model_dir = tmp_path / "my_models"
        result = resolve_model_dir(model_dir)
        assert result == model_dir
        assert result.exists()

    def test_default_path(self):
        result = resolve_model_dir(None, model_version="v1")
        assert "geotcha" in str(result)
        assert result.name == "v1"
        assert result.exists()


class TestLoadNerModel:
    def test_import_error(self):
        with patch.dict("sys.modules", {"gliner": None}):
            with pytest.raises(ModelNotFoundError, match="GLiNER not installed"):
                load_ner_model()

    def test_success(self):
        mock_gliner = MagicMock()
        mock_model = MagicMock()
        mock_gliner.GLiNER.from_pretrained.return_value = mock_model
        with patch.dict("sys.modules", {"gliner": mock_gliner}):
            result = load_ner_model("test-model")
        assert result is mock_model
        mock_gliner.GLiNER.from_pretrained.assert_called_once_with("test-model")


class TestLoadLinker:
    def test_import_error(self):
        with patch.dict("sys.modules", {"sentence_transformers": None}):
            with pytest.raises(ModelNotFoundError, match="sentence-transformers not installed"):
                load_linker()

    def test_success(self):
        mock_st = MagicMock()
        mock_model = MagicMock()
        mock_st.SentenceTransformer.return_value = mock_model
        with patch.dict("sys.modules", {"sentence_transformers": mock_st}):
            result = load_linker("test-linker")
        assert result is mock_model
        mock_st.SentenceTransformer.assert_called_once_with("test-linker")
