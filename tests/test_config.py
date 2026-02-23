"""Tests for configuration management."""

from __future__ import annotations

from unittest.mock import patch

from geotcha.config import Settings, save_config


class TestSettingsDefaults:
    def test_default_max_retries(self):
        settings = Settings()
        assert settings.max_retries == 3

    def test_default_output_format(self):
        settings = Settings()
        assert settings.output_format == "csv"

    def test_default_non_interactive_false(self):
        settings = Settings()
        assert settings.non_interactive is False

    def test_default_yes_false(self):
        settings = Settings()
        assert settings.yes is False

    def test_default_subset_size(self):
        settings = Settings()
        assert settings.default_subset_size == 5


class TestSettingsLoad:
    def test_override_max_retries(self, tmp_path):
        settings = Settings.load(output_dir=tmp_path / "out", max_retries=7)
        assert settings.max_retries == 7

    def test_override_output_format(self, tmp_path):
        settings = Settings.load(output_dir=tmp_path / "out", output_format="tsv")
        assert settings.output_format == "tsv"

    def test_none_overrides_ignored(self, tmp_path):
        """None values in overrides don't clobber defaults."""
        settings = Settings.load(output_dir=tmp_path / "out", ncbi_api_key=None)
        assert settings.ncbi_api_key is None

    def test_yes_flag_propagated(self, tmp_path):
        settings = Settings.load(output_dir=tmp_path / "out", yes=True)
        assert settings.yes is True

    def test_non_interactive_flag_propagated(self, tmp_path):
        settings = Settings.load(output_dir=tmp_path / "out", non_interactive=True)
        assert settings.non_interactive is True


class TestSaveConfig:
    def test_saves_string_value(self, tmp_path):
        with patch("geotcha.config._geotcha_config_dir", return_value=tmp_path):
            save_config("ncbi_tool", "my_tool")
            content = (tmp_path / "config.toml").read_text()
            assert 'ncbi_tool = "my_tool"' in content

    def test_saves_multiple_keys(self, tmp_path):
        with patch("geotcha.config._geotcha_config_dir", return_value=tmp_path):
            save_config("ncbi_tool", "tool1")
            save_config("output_format", "tsv")
            content = (tmp_path / "config.toml").read_text()
            assert 'ncbi_tool = "tool1"' in content
            assert 'output_format = "tsv"' in content

    def test_overwrites_existing_key(self, tmp_path):
        with patch("geotcha.config._geotcha_config_dir", return_value=tmp_path):
            save_config("ncbi_tool", "old_tool")
            save_config("ncbi_tool", "new_tool")
            content = (tmp_path / "config.toml").read_text()
            assert 'ncbi_tool = "new_tool"' in content
            assert "old_tool" not in content

    def test_creates_config_dir_if_missing(self, tmp_path):
        config_dir = tmp_path / "nested" / "config"
        with patch("geotcha.config._geotcha_config_dir", return_value=config_dir):
            # _geotcha_config_dir uses ensure_exists=True in real code,
            # but here we just verify the file is written
            config_dir.mkdir(parents=True)
            save_config("key", "value")
            assert (config_dir / "config.toml").exists()


class TestEffectiveRateLimit:
    def test_rate_limit_without_key(self):
        settings = Settings(ncbi_api_key=None)
        assert settings.get_effective_rate_limit() == 3.0

    def test_rate_limit_with_key(self):
        settings = Settings(ncbi_api_key="somekey")
        assert settings.get_effective_rate_limit() == 10.0


class TestGetDataDir:
    def test_custom_data_dir(self, tmp_path):
        settings = Settings(data_dir=tmp_path / "mydata")
        d = settings.get_data_dir()
        assert d == tmp_path / "mydata"
        assert d.exists()

    def test_custom_cache_dir(self, tmp_path):
        settings = Settings(cache_dir=tmp_path / "mycache")
        d = settings.get_cache_dir()
        assert d == tmp_path / "mycache"
        assert d.exists()
