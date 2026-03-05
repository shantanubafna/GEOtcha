"""Tests for ML-related config settings."""
from __future__ import annotations

import os
from unittest.mock import patch

from typer.testing import CliRunner

from geotcha.cli import app
from geotcha.config import Settings

runner = CliRunner()


class TestMlConfigDefaults:
    def test_ml_mode_default_off(self):
        s = Settings(output_dir="/tmp/test", cache_dir="/tmp/cache", data_dir="/tmp/data")
        assert s.ml_mode == "off"

    def test_ml_threshold_default(self):
        s = Settings(output_dir="/tmp/test", cache_dir="/tmp/cache", data_dir="/tmp/data")
        assert s.ml_threshold == 0.65

    def test_ml_device_default(self):
        s = Settings(output_dir="/tmp/test", cache_dir="/tmp/cache", data_dir="/tmp/data")
        assert s.ml_device == "auto"

    def test_ml_batch_size_default(self):
        s = Settings(output_dir="/tmp/test", cache_dir="/tmp/cache", data_dir="/tmp/data")
        assert s.ml_batch_size == 32

    def test_ml_review_threshold_default(self):
        s = Settings(output_dir="/tmp/test", cache_dir="/tmp/cache", data_dir="/tmp/data")
        assert s.ml_review_threshold == 0.50


class TestMlConfigFromEnv:
    def test_ml_mode_from_env(self):
        with patch.dict(os.environ, {"GEOTCHA_ML_MODE": "hybrid"}, clear=False):
            s = Settings(output_dir="/tmp/test", cache_dir="/tmp/cache", data_dir="/tmp/data")
            assert s.ml_mode == "hybrid"

    def test_ml_threshold_from_env(self):
        with patch.dict(os.environ, {"GEOTCHA_ML_THRESHOLD": "0.80"}, clear=False):
            s = Settings(output_dir="/tmp/test", cache_dir="/tmp/cache", data_dir="/tmp/data")
            assert s.ml_threshold == 0.80


class TestMlConfigFromToml:
    def test_ml_settings_from_toml(self, tmp_path):
        toml_content = 'ml_mode = "full"\nml_threshold = 0.75\n'
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "config.toml"
        config_file.write_text(toml_content)

        with patch("geotcha.config._geotcha_config_dir", return_value=config_dir):
            s = Settings.load()
        assert s.ml_mode == "full"
        assert s.ml_threshold == 0.75


class TestConfigValidate:
    def test_valid_config(self):
        result = runner.invoke(app, ["config", "validate"])
        assert result.exit_code == 0
        assert "valid" in result.output.lower()

    def test_warns_invalid_ml_mode(self, tmp_path):
        toml_content = 'ml_mode = "invalid"\n'
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "config.toml"
        config_file.write_text(toml_content)

        with patch("geotcha.config._geotcha_config_dir", return_value=config_dir):
            result = runner.invoke(app, ["config", "validate"])
        assert "warning" in result.output.lower() or "Warning" in result.output
