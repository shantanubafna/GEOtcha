"""File-based caching for SOFT files and API responses."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any


class Cache:
    """Simple file-based cache with TTL."""

    def __init__(self, cache_dir: Path, ttl_days: int = 7) -> None:
        self.cache_dir = cache_dir
        self.ttl_seconds = ttl_days * 86400
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _key_path(self, key: str) -> Path:
        hashed = hashlib.sha256(key.encode()).hexdigest()[:16]
        safe_key = "".join(c if c.isalnum() or c in "-_." else "_" for c in key)
        # Truncate safe_key to avoid overly long filenames
        safe_key = safe_key[:60]
        return self.cache_dir / f"{safe_key}_{hashed}.json"

    def get(self, key: str) -> Any | None:
        """Get a cached value, or None if missing/expired."""
        path = self._key_path(key)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            if time.time() - data["timestamp"] > self.ttl_seconds:
                path.unlink(missing_ok=True)
                return None
            return data["value"]
        except (json.JSONDecodeError, KeyError):
            path.unlink(missing_ok=True)
            return None

    def set(self, key: str, value: Any) -> None:
        """Store a value in the cache."""
        path = self._key_path(key)
        data = {"timestamp": time.time(), "value": value}
        path.write_text(json.dumps(data))

    def clear(self) -> int:
        """Remove all cached files. Returns count of removed files."""
        count = 0
        for f in self.cache_dir.glob("*.json"):
            f.unlink()
            count += 1
        return count
