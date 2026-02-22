"""Custom exceptions for GEOtcha."""


class GEOtchaError(Exception):
    """Base exception for GEOtcha."""


class SearchError(GEOtchaError):
    """Error during GEO search."""


class NetworkError(SearchError):
    """Transient network failure during NCBI API calls."""


class ExtractionError(GEOtchaError):
    """Error during metadata extraction."""


class HarmonizationError(GEOtchaError):
    """Error during metadata harmonization."""


class ConfigError(GEOtchaError):
    """Error in configuration."""


class RateLimitError(GEOtchaError):
    """Rate limit exceeded."""


class CacheError(GEOtchaError):
    """Error in caching operations."""
