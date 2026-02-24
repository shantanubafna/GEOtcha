"""Tests for file-based cache."""

from __future__ import annotations

from unittest.mock import patch

from geotcha.cache import Cache


class TestCacheGetSet:
    def test_set_and_get(self, tmp_path):
        cache = Cache(tmp_path / "cache")
        cache.set("key1", {"data": "value"})
        assert cache.get("key1") == {"data": "value"}

    def test_miss_returns_none(self, tmp_path):
        cache = Cache(tmp_path / "cache")
        assert cache.get("nonexistent") is None

    def test_list_value(self, tmp_path):
        cache = Cache(tmp_path / "cache")
        cache.set("key1", ["a", "b", "c"])
        assert cache.get("key1") == ["a", "b", "c"]

    def test_different_keys_independent(self, tmp_path):
        cache = Cache(tmp_path / "cache")
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"

    def test_overwrite(self, tmp_path):
        cache = Cache(tmp_path / "cache")
        cache.set("key1", "old")
        cache.set("key1", "new")
        assert cache.get("key1") == "new"

    def test_numeric_value(self, tmp_path):
        cache = Cache(tmp_path / "cache")
        cache.set("count", 42)
        assert cache.get("count") == 42


class TestCacheExpiry:
    def test_expiry_via_mock(self, tmp_path):
        """Items past TTL are expired."""
        import time

        cache = Cache(tmp_path / "cache", ttl_days=1)
        cache.set("key1", "value")
        # Simulate time advancing past TTL (1 day = 86400 seconds)
        future = time.time() + 86401
        with patch("geotcha.cache.time.time", return_value=future):
            assert cache.get("key1") is None

    def test_not_expired_before_ttl(self, tmp_path):
        """Items within TTL are not expired."""
        import time

        cache = Cache(tmp_path / "cache", ttl_days=7)
        cache.set("key1", "value")
        future = time.time() + 86400  # 1 day later, still within 7-day TTL
        with patch("geotcha.cache.time.time", return_value=future):
            assert cache.get("key1") == "value"

    def test_expired_file_removed(self, tmp_path):
        """Expired cache file is deleted on access."""
        import time

        cache = Cache(tmp_path / "cache", ttl_days=1)
        cache.set("key1", "value")
        key_path = cache._key_path("key1")
        assert key_path.exists()

        future = time.time() + 86401
        with patch("geotcha.cache.time.time", return_value=future):
            cache.get("key1")

        assert not key_path.exists()


class TestCacheClear:
    def test_clear_returns_count(self, tmp_path):
        cache = Cache(tmp_path / "cache")
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        count = cache.clear()
        assert count == 2

    def test_clear_empties_cache(self, tmp_path):
        cache = Cache(tmp_path / "cache")
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        cache.clear()
        assert cache.get("k1") is None
        assert cache.get("k2") is None

    def test_clear_empty_cache(self, tmp_path):
        cache = Cache(tmp_path / "cache")
        assert cache.clear() == 0


class TestCacheCorruption:
    def test_corrupted_file_returns_none(self, tmp_path):
        """Corrupted cache file is treated as a miss."""
        cache = Cache(tmp_path / "cache")
        cache.set("key1", "value")
        path = cache._key_path("key1")
        path.write_text("not valid json")
        assert cache.get("key1") is None

    def test_corrupted_file_removed(self, tmp_path):
        """Corrupted cache file is cleaned up."""
        cache = Cache(tmp_path / "cache")
        cache.set("key1", "value")
        path = cache._key_path("key1")
        path.write_text("not valid json")
        cache.get("key1")
        assert not path.exists()
