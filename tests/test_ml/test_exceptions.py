"""Tests for ML exceptions."""
from __future__ import annotations

from geotcha.exceptions import GEOtchaError
from geotcha.ml.exceptions import MLInferenceError, ModelNotFoundError


def test_model_not_found_is_geotcha_error():
    assert issubclass(ModelNotFoundError, GEOtchaError)


def test_ml_inference_error_is_geotcha_error():
    assert issubclass(MLInferenceError, GEOtchaError)


def test_exception_messages():
    err = ModelNotFoundError("model missing")
    assert str(err) == "model missing"

    err2 = MLInferenceError("inference failed")
    assert str(err2) == "inference failed"
