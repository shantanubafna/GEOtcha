"""Token-bucket rate limiter for NCBI API calls."""

from __future__ import annotations

import threading
import time


class RateLimiter:
    """Token-bucket rate limiter.

    NCBI allows 3 requests/second without an API key, 10 with one.
    """

    def __init__(self, rate: float = 3.0, burst: int = 1) -> None:
        self.rate = rate
        self.burst = burst
        self._tokens = float(burst)
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """Block until a token is available."""
        while True:
            with self._lock:
                now = time.monotonic()
                elapsed = now - self._last_refill
                self._tokens = min(self.burst, self._tokens + elapsed * self.rate)
                self._last_refill = now

                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return

            # Sleep for the time needed to get one token
            time.sleep(1.0 / self.rate)


# Module-level singleton, configured lazily
_limiter: RateLimiter | None = None


def get_limiter(rate: float = 3.0) -> RateLimiter:
    """Get or create the global rate limiter."""
    global _limiter
    if _limiter is None or _limiter.rate != rate:
        _limiter = RateLimiter(rate=rate)
    return _limiter
