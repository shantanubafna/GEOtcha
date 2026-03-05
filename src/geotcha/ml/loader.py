"""Model loading utilities for the ML harmonization layer."""
from __future__ import annotations

import logging
from pathlib import Path

from geotcha.ml.exceptions import ModelNotFoundError

logger = logging.getLogger(__name__)

_DEFAULT_NER_MODEL = "Ihor/gliner-biomed-large-v1.0"
_DEFAULT_LINKER_MODEL = "cambridgeltl/SapBERT-from-PubMedBERT-fulltext"


def _resolve_device(device: str) -> str:
    """Resolve 'auto' device to the best available backend.

    Returns 'cuda', 'mps', or 'cpu'.
    """
    if device != "auto":
        return device
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
    except ImportError:
        pass
    return "cpu"


def resolve_model_dir(model_dir: Path | None, model_version: str = "v1") -> Path:
    """Resolve the directory containing ML model artifacts.

    Priority: explicit model_dir > ~/.cache/geotcha/ml/{model_version}
    """
    if model_dir:
        resolved = Path(model_dir)
    else:
        from platformdirs import user_cache_dir

        resolved = Path(user_cache_dir("geotcha")) / "ml" / model_version
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def load_ner_model(model_name_or_path: str | None = None):
    """Load GLiNER-BioMed model for zero-shot biomedical NER.

    Args:
        model_name_or_path: HuggingFace model ID or local path.
            Defaults to Ihor/gliner-biomed-large-v1.0.

    Returns:
        A GLiNER model instance ready for .predict_entities().

    Raises:
        ModelNotFoundError: If the model cannot be loaded.
    """
    try:
        from gliner import GLiNER
    except ImportError as e:
        raise ModelNotFoundError(
            "GLiNER not installed. Install with: pip install geotcha[ml]"
        ) from e

    name = model_name_or_path or _DEFAULT_NER_MODEL
    try:
        model = GLiNER.from_pretrained(name)
        logger.info("Loaded NER model: %s", name)
        return model
    except Exception as e:
        raise ModelNotFoundError(f"Failed to load NER model '{name}': {e}") from e


def load_linker(model_name_or_path: str | None = None):
    """Load SapBERT model for ontology entity linking.

    Args:
        model_name_or_path: HuggingFace model ID or local path.
            Defaults to cambridgeltl/SapBERT-from-PubMedBERT-fulltext.

    Returns:
        A SentenceTransformer-compatible model for encoding entity strings.

    Raises:
        ModelNotFoundError: If the model cannot be loaded.
    """
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        raise ModelNotFoundError(
            "sentence-transformers not installed. Install with: pip install geotcha[ml]"
        ) from e

    name = model_name_or_path or _DEFAULT_LINKER_MODEL
    try:
        model = SentenceTransformer(name)
        logger.info("Loaded linker model: %s", name)
        return model
    except Exception as e:
        raise ModelNotFoundError(f"Failed to load linker model '{name}': {e}") from e
