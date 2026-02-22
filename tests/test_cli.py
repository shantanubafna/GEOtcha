"""Tests for CLI interface."""

from typer.testing import CliRunner

from geotcha.cli import app

runner = CliRunner()


class TestCLI:
    def test_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "GEOtcha" in result.output

    def test_version(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "GEOtcha v" in result.output

    def test_search_help(self):
        result = runner.invoke(app, ["search", "--help"])
        assert result.exit_code == 0
        assert "keyword" in result.output.lower()

    def test_extract_help(self):
        result = runner.invoke(app, ["extract", "--help"])
        assert result.exit_code == 0

    def test_run_help(self):
        result = runner.invoke(app, ["run", "--help"])
        assert result.exit_code == 0

    def test_config_show_help(self):
        result = runner.invoke(app, ["config", "show", "--help"])
        assert result.exit_code == 0

    def test_config_set_help(self):
        result = runner.invoke(app, ["config", "set", "--help"])
        assert result.exit_code == 0
