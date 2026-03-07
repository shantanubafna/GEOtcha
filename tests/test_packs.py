"""Tests for disease packs."""
from __future__ import annotations

import pytest
from typer.testing import CliRunner

from geotcha.cli import app
from geotcha.packs import DiseasePack, list_packs, load_pack

runner = CliRunner()


class TestListPacks:
    def test_returns_list(self):
        packs = list_packs()
        assert isinstance(packs, list)
        assert len(packs) >= 5

    def test_known_packs_present(self):
        packs = list_packs()
        assert "ibd" in packs
        assert "oncology" in packs
        assert "neurodegeneration" in packs
        assert "autoimmune" in packs
        assert "metabolic" in packs

    def test_sorted(self):
        packs = list_packs()
        assert packs == sorted(packs)


class TestLoadPack:
    def test_load_ibd(self):
        pack = load_pack("ibd")
        assert isinstance(pack, DiseasePack)
        assert pack.name == "ibd"
        assert pack.display_name == "Inflammatory Bowel Disease"
        assert "inflammatory bowel disease" in pack.search_terms
        assert "ulcerative colitis" in pack.search_terms
        assert "UC" in pack.relevance_keywords
        assert "colon" in pack.expected_tissues
        assert "infliximab" in pack.expected_treatments

    def test_load_oncology(self):
        pack = load_pack("oncology")
        assert pack.name == "oncology"
        assert "cancer" in pack.search_terms
        assert len(pack.expected_treatments) > 10

    def test_load_neurodegeneration(self):
        pack = load_pack("neurodegeneration")
        assert "Alzheimer's disease" in pack.search_terms
        assert "brain" in pack.expected_tissues

    def test_load_autoimmune(self):
        pack = load_pack("autoimmune")
        assert "rheumatoid arthritis" in pack.search_terms
        assert "methotrexate" in pack.expected_treatments

    def test_load_metabolic(self):
        pack = load_pack("metabolic")
        assert "type 2 diabetes" in pack.search_terms
        assert "liver" in pack.expected_tissues

    def test_unknown_pack_raises(self):
        with pytest.raises(FileNotFoundError, match="not found"):
            load_pack("nonexistent_pack")

    def test_error_message_lists_available(self):
        with pytest.raises(FileNotFoundError, match="ibd"):
            load_pack("nonexistent_pack")


class TestPacksCli:
    def test_packs_command(self):
        result = runner.invoke(app, ["packs"])
        assert result.exit_code == 0
        assert "ibd" in result.output
        assert "oncology" in result.output
        assert "neurodegeneration" in result.output
        assert "autoimmune" in result.output
        assert "metabolic" in result.output

    def test_packs_shows_details(self):
        result = runner.invoke(app, ["packs"])
        assert "Inflammatory Bowel Disease" in result.output
        assert "Search terms:" in result.output


class TestBuildPackQuery:
    def test_pack_query_has_terms(self):
        from geotcha.pipeline import _build_pack_query

        pack = load_pack("ibd")
        query = _build_pack_query(pack)
        assert "inflammatory bowel disease" in query
        assert "ulcerative colitis" in query
        assert "Homo sapiens" in query
        assert "high throughput sequencing" in query

    def test_empty_pack_terms(self):
        from geotcha.pipeline import _build_pack_query

        pack = DiseasePack(name="empty", display_name="Empty", description="test")
        query = _build_pack_query(pack)
        assert query == ""
