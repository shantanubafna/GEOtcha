"""Tests for ML CLI subcommands."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from geotcha.cli import app

runner = CliRunner()


class TestMlStatus:
    def test_no_indices(self, tmp_path):
        with patch("geotcha.ml.loader.resolve_model_dir", return_value=tmp_path):
            result = runner.invoke(app, ["ml", "status"])
        assert result.exit_code == 0
        assert "No ontology indices found" in result.output

    def test_with_indices(self, tmp_path):
        index_dir = tmp_path / "indices"
        index_dir.mkdir()
        (index_dir / "tissue.faiss").write_bytes(b"fake")
        (index_dir / "disease.faiss").write_bytes(b"fake")

        with patch("geotcha.ml.loader.resolve_model_dir", return_value=tmp_path):
            result = runner.invoke(app, ["ml", "status"])
        assert result.exit_code == 0
        assert "tissue" in result.output
        assert "disease" in result.output


class TestMlBuildIndex:
    def test_missing_sentence_transformers(self):
        with patch.dict("sys.modules", {"sentence_transformers": None}):
            result = runner.invoke(app, ["ml", "build-index"])
        assert result.exit_code == 1
        assert "sentence-transformers" in result.output

    def test_missing_faiss(self):
        mock_st = MagicMock()
        with (
            patch.dict("sys.modules", {"sentence_transformers": mock_st}),
            patch.dict("sys.modules", {"faiss": None}),
        ):
            result = runner.invoke(app, ["ml", "build-index"])
        assert result.exit_code == 1
        assert "faiss" in result.output


class TestMlDownload:
    def test_download_fallback_message(self):
        """Download should show fallback message (pre-built hosting not yet available)."""
        # It will fail because sentence-transformers isn't installed, but we check the message
        with patch.dict("sys.modules", {"sentence_transformers": None}):
            result = runner.invoke(app, ["ml", "download"])
        assert "not yet available" in result.output


class TestMlHelp:
    def test_ml_help(self):
        result = runner.invoke(app, ["ml", "--help"])
        assert result.exit_code == 0
        assert "build-index" in result.output
        assert "download" in result.output
        assert "status" in result.output
