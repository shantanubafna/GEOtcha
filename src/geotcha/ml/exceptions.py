"""ML-specific exceptions for GEOtcha."""
from __future__ import annotations

from geotcha.exceptions import GEOtchaError


class ModelNotFoundError(GEOtchaError):
    """Raised when ML model files cannot be located."""


class MLInferenceError(GEOtchaError):
    """Raised when ML inference fails."""
