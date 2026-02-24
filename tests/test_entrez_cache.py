"""Tests for Entrez response caching (0.3.0 performance features)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from geotcha.config import Settings
from geotcha.search.entrez import _get_entrez_cache, get_gse_summaries, search_geo

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def cached_settings(tmp_path):
    return Settings(
        cache_dir=tmp_path / "cache",
        data_dir=tmp_path / "data",
        output_dir=tmp_path / "output",
        enable_entrez_cache=True,
        cache_ttl_days=7,
    )


@pytest.fixture
def uncached_settings(tmp_path):
    return Settings(
        cache_dir=tmp_path / "cache",
        data_dir=tmp_path / "data",
        output_dir=tmp_path / "output",
        enable_entrez_cache=False,
    )


# ---------------------------------------------------------------------------
# _get_entrez_cache helper
# ---------------------------------------------------------------------------

class TestGetEntrezCache:
    def test_cache_dir_is_entrez_subdir(self, cached_settings):
        cache = _get_entrez_cache(cached_settings)
        assert cache.cache_dir.name == "entrez"

    def test_cache_ttl_matches_settings(self, cached_settings):
        cache = _get_entrez_cache(cached_settings)
        assert cache.ttl_seconds == cached_settings.cache_ttl_days * 86400


# ---------------------------------------------------------------------------
# search_geo caching
# ---------------------------------------------------------------------------

class TestSearchGeoCaching:
    @patch("geotcha.search.entrez._configure_entrez")
    @patch("geotcha.search.entrez._esearch")
    def test_warm_cache_skips_entrez(self, mock_esearch, mock_configure, cached_settings):
        """search_geo with a warm cache returns cached IDs without calling Entrez."""
        query = "ulcerative colitis"
        expected_ids = ["200012345", "200067890"]

        cache = _get_entrez_cache(cached_settings)
        cache.set(f"esearch:{query}", expected_ids)

        result = search_geo(query, cached_settings)

        assert result == expected_ids
        mock_esearch.assert_not_called()

    @patch("geotcha.search.entrez._configure_entrez")
    @patch("geotcha.search.entrez._esearch")
    def test_cold_cache_calls_entrez_and_stores(
        self, mock_esearch, mock_configure, cached_settings
    ):
        """search_geo with no cache calls Entrez and stores the result."""
        query = "crohn disease"
        ids = ["200011111", "200022222"]

        mock_esearch.side_effect = [
            {"Count": "2", "IdList": []},   # first call: count only
            {"Count": "2", "IdList": ids},  # second call: paginated batch
        ]

        result = search_geo(query, cached_settings)

        assert result == ids
        assert mock_esearch.call_count == 2

        # Verify the result is now cached
        cache = _get_entrez_cache(cached_settings)
        assert cache.get(f"esearch:{query}") == ids

    @patch("geotcha.search.entrez._configure_entrez")
    @patch("geotcha.search.entrez._esearch")
    def test_second_call_uses_cache(self, mock_esearch, mock_configure, cached_settings):
        """Repeated search_geo calls return cached results after the first call."""
        query = "ibd cohort"
        ids = ["200055555"]

        mock_esearch.side_effect = [
            {"Count": "1", "IdList": []},
            {"Count": "1", "IdList": ids},
        ]

        first = search_geo(query, cached_settings)
        second = search_geo(query, cached_settings)

        assert first == second == ids
        # Entrez called only twice (for the first search_geo call)
        assert mock_esearch.call_count == 2

    @patch("geotcha.search.entrez._configure_entrez")
    @patch("geotcha.search.entrez._esearch")
    def test_cache_disabled_always_calls_entrez(
        self, mock_esearch, mock_configure, uncached_settings
    ):
        """When enable_entrez_cache=False, Entrez is called every time."""
        query = "ibd"
        ids = ["200033333"]

        mock_esearch.side_effect = [
            {"Count": "1", "IdList": []},
            {"Count": "1", "IdList": ids},
            {"Count": "1", "IdList": []},
            {"Count": "1", "IdList": ids},
        ]

        search_geo(query, uncached_settings)
        search_geo(query, uncached_settings)

        assert mock_esearch.call_count == 4  # called both times, no caching

    @patch("geotcha.search.entrez._configure_entrez")
    @patch("geotcha.search.entrez._esearch")
    def test_empty_result_not_cached(self, mock_esearch, mock_configure, cached_settings):
        """Zero-result searches are not cached (avoids stale empty cache on transient failures)."""
        # Note: search_geo returns [] early on Count=0, no caching path is hit
        mock_esearch.return_value = {"Count": "0", "IdList": []}

        result = search_geo("no match query xyz", cached_settings)
        assert result == []

        cache = _get_entrez_cache(cached_settings)
        assert cache.get("esearch:no match query xyz") is None


# ---------------------------------------------------------------------------
# get_summaries caching (per-batch)
# ---------------------------------------------------------------------------

class TestGetSummariesCaching:
    @patch("geotcha.search.entrez._configure_entrez")
    @patch("geotcha.search.entrez._esummary_batch")
    def test_warm_cache_skips_esummary(self, mock_esummary, mock_configure, cached_settings):
        """Cached esummary batches are returned without network calls."""
        from geotcha.search.entrez import get_summaries

        ids = ["100", "101"]
        cached_result = [{"title": "Cached Study"}]

        cache = _get_entrez_cache(cached_settings)
        cache_key = f"esummary:{','.join(sorted(ids))}"
        cache.set(cache_key, cached_result)

        result = get_summaries(ids, cached_settings)

        assert result == cached_result
        mock_esummary.assert_not_called()

    @patch("geotcha.search.entrez._configure_entrez")
    @patch("geotcha.search.entrez._esummary_batch")
    def test_cold_cache_calls_esummary_and_stores(
        self, mock_esummary, mock_configure, cached_settings
    ):
        """get_summaries calls Entrez and caches the batch result."""
        from geotcha.search.entrez import get_summaries

        ids = ["200", "201"]
        fetched = [{"title": "New Study"}]
        mock_esummary.return_value = fetched

        result = get_summaries(ids, cached_settings)

        assert result == fetched
        mock_esummary.assert_called_once()

        cache = _get_entrez_cache(cached_settings)
        cache_key = f"esummary:{','.join(sorted(ids))}"
        assert cache.get(cache_key) == fetched


# ---------------------------------------------------------------------------
# get_gse_summaries: batching + caching
# ---------------------------------------------------------------------------

class TestGetGSESummariesBatching:
    @patch("geotcha.search.entrez._configure_entrez")
    @patch("geotcha.search.entrez._esummary_batch")
    @patch("geotcha.search.entrez._esearch")
    def test_multiple_gse_ids_batched_in_one_esearch(
        self, mock_esearch, mock_esummary, mock_configure, cached_settings
    ):
        """get_gse_summaries batches multiple GSE IDs in a single esearch call."""
        gse_ids = ["GSE001", "GSE002", "GSE003"]
        mock_esearch.return_value = {"IdList": ["100", "101", "102"]}
        mock_esummary.return_value = [
            {"Accession": "GSE001", "title": "Study 1", "summary": "Summary 1"},
            {"Accession": "GSE002", "title": "Study 2", "summary": "Summary 2"},
            {"Accession": "GSE003", "title": "Study 3", "summary": "Summary 3"},
        ]

        result = get_gse_summaries(gse_ids, cached_settings)

        assert mock_esearch.call_count == 1  # single batched call
        assert set(result.keys()) == {"GSE001", "GSE002", "GSE003"}
        assert result["GSE001"]["title"] == "Study 1"
        assert result["GSE003"]["summary"] == "Summary 3"

    @patch("geotcha.search.entrez._configure_entrez")
    @patch("geotcha.search.entrez._esummary_batch")
    @patch("geotcha.search.entrez._esearch")
    def test_warm_cache_skips_network_for_known_gse(
        self, mock_esearch, mock_esummary, mock_configure, cached_settings
    ):
        """Cached GSE IDs are not re-fetched from Entrez."""
        cache = _get_entrez_cache(cached_settings)
        cache.set("gse_summary:GSE001", {"title": "Cached Title", "summary": "Cached"})

        result = get_gse_summaries(["GSE001"], cached_settings)

        assert result["GSE001"]["title"] == "Cached Title"
        mock_esearch.assert_not_called()
        mock_esummary.assert_not_called()

    @patch("geotcha.search.entrez._configure_entrez")
    @patch("geotcha.search.entrez._esummary_batch")
    @patch("geotcha.search.entrez._esearch")
    def test_mixed_cache_hit_and_miss(
        self, mock_esearch, mock_esummary, mock_configure, cached_settings
    ):
        """Cache hits served from cache; misses fetched and then cached."""
        cache = _get_entrez_cache(cached_settings)
        cache.set("gse_summary:GSE001", {"title": "Cached", "summary": "OK"})

        mock_esearch.return_value = {"IdList": ["200"]}
        mock_esummary.return_value = [
            {"Accession": "GSE002", "title": "Fresh", "summary": "Fresh summary"},
        ]

        result = get_gse_summaries(["GSE001", "GSE002"], cached_settings)

        assert result["GSE001"]["title"] == "Cached"
        assert result["GSE002"]["title"] == "Fresh"
        # Only one esearch call for the uncached GSE002
        assert mock_esearch.call_count == 1
        # GSE002 now cached
        assert cache.get("gse_summary:GSE002") == {"title": "Fresh", "summary": "Fresh summary"}

    @patch("geotcha.search.entrez._configure_entrez")
    @patch("geotcha.search.entrez._esummary_batch")
    @patch("geotcha.search.entrez._esearch")
    def test_cache_disabled_always_fetches(
        self, mock_esearch, mock_esummary, mock_configure, uncached_settings
    ):
        """When enable_entrez_cache=False, every call hits Entrez."""
        mock_esearch.return_value = {"IdList": ["100"]}
        mock_esummary.return_value = [
            {"Accession": "GSE001", "title": "Study", "summary": "S"},
        ]

        get_gse_summaries(["GSE001"], uncached_settings)
        get_gse_summaries(["GSE001"], uncached_settings)

        assert mock_esearch.call_count == 2

    @patch("geotcha.search.entrez._configure_entrez")
    @patch("geotcha.search.entrez._esummary_batch")
    @patch("geotcha.search.entrez._esearch")
    def test_empty_gse_ids_returns_empty(
        self, mock_esearch, mock_esummary, mock_configure, cached_settings
    ):
        result = get_gse_summaries([], cached_settings)
        assert result == {}
        mock_esearch.assert_not_called()
