"""ML-based harmonization for GEOtcha metadata."""
from __future__ import annotations

import logging

from geotcha.harmonize.rules import NormResult, _apply_norm
from geotcha.ml.exceptions import MLInferenceError
from geotcha.models import GSERecord, GSMRecord

logger = logging.getLogger(__name__)

# Entity label mapping: GLiNER label -> (record field, provenance source)
_NER_LABELS = ["disease", "tissue", "cell type", "treatment", "gender"]
_LABEL_TO_FIELD = {
    "disease": "disease",
    "tissue": "tissue",
    "cell type": "cell_type",
    "treatment": "treatment",
    "gender": "gender",
}

# Map field names to ontology index types
_FIELD_TO_INDEX = {
    "disease": "disease",
    "tissue": "tissue",
    "cell_type": "cell_type",
    "treatment": "treatment",
}

# Minimum similarity score for entity linking to be considered valid
_LINK_MIN_SCORE = 0.70


class MLHarmonizer:
    """ML-based harmonizer using GLiNER for NER and SapBERT for entity linking.

    Only upgrades fields where current confidence < threshold.
    Thread-safe for read-only inference after __init__.
    """

    def __init__(
        self,
        ner_model=None,
        linker_model=None,
        threshold: float = 0.65,
        device: str = "auto",
        review_threshold: float = 0.50,
        index_set=None,
    ) -> None:
        self._ner = ner_model
        self._linker = linker_model
        self.threshold = threshold
        self.device = device
        self.review_threshold = review_threshold
        self._index_set = index_set  # OntologyIndexSet or None

    @classmethod
    def from_config(cls, settings) -> MLHarmonizer:
        """Create an MLHarmonizer from GEOtcha settings."""
        from geotcha.ml.loader import _resolve_device, load_linker, load_ner_model

        device = _resolve_device(settings.ml_device)
        ner = load_ner_model(None)
        linker = load_linker(None)

        # Try to load ontology indices for entity linking
        index_set = None
        try:
            from geotcha.ml.index import OntologyIndexSet
            from geotcha.ml.loader import resolve_model_dir

            index_dir = resolve_model_dir(None) / "indices"
            if index_dir.exists():
                index_set = OntologyIndexSet.load(index_dir)
                logger.info("Loaded ontology indices for entity linking")
        except Exception as e:
            logger.debug("Ontology indices not available: %s", e)

        return cls(
            ner_model=ner,
            linker_model=linker,
            threshold=settings.ml_threshold,
            device=device,
            review_threshold=settings.ml_review_threshold,
            index_set=index_set,
        )

    def _needs_ml(self, record, field: str) -> bool:
        """Check if a field needs ML augmentation (missing or low confidence)."""
        harmonized = getattr(record, f"{field}_harmonized", None)
        confidence = getattr(record, f"{field}_confidence", None)
        if harmonized is None:
            return True
        if confidence is not None and confidence < self.threshold:
            return True
        return False

    def _build_text(self, record: GSMRecord) -> str:
        """Build input text for NER from GSM record fields."""
        parts = []
        if record.title:
            parts.append(record.title)
        if record.source_name:
            parts.append(record.source_name)
        if record.description:
            parts.append(record.description)
        for v in record.characteristics.values():
            parts.append(v)
        return " ; ".join(parts)

    def _build_gse_text(self, record: GSERecord) -> str:
        """Build input text for NER from GSE record fields."""
        parts = []
        if record.title:
            parts.append(record.title)
        if record.summary:
            parts.append(record.summary[:512])
        if record.overall_design:
            parts.append(record.overall_design[:256])
        return " ; ".join(parts)

    def _run_ner(self, text: str) -> list[dict]:
        """Run GLiNER NER on text. Returns list of {label, text, score}."""
        if self._ner is None:
            return []
        try:
            entities = self._ner.predict_entities(text, _NER_LABELS, threshold=0.3)
            return entities
        except Exception as e:
            logger.warning("NER inference failed: %s", e)
            return []

    def _link_entity(self, text: str, field: str) -> tuple[str | None, float]:
        """Link an entity string to an ontology term using SapBERT.

        Encodes the entity text with SapBERT and searches the corresponding
        FAISS ontology index for the nearest neighbor.

        Returns (ontology_id, confidence). Returns (None, 0.0) if linking fails
        or if no index is available for this field.
        """
        if self._linker is None:
            return None, 0.0

        index_type = _FIELD_TO_INDEX.get(field)
        if not index_type or self._index_set is None:
            return None, 0.0

        index = self._index_set.get(index_type)
        if index is None:
            return None, 0.0

        try:
            import numpy as np

            embedding = self._linker.encode(
                [text], show_progress_bar=False, normalize_embeddings=True
            )
            embedding = np.array(embedding, dtype=np.float32)
            results = index.search(embedding, top_k=1)

            if results:
                _name, ontology_id, score = results[0]
                if score >= _LINK_MIN_SCORE:
                    return ontology_id, float(score)

            return None, 0.0
        except Exception as e:
            logger.warning("Entity linking failed for '%s' (%s): %s", text, field, e)
            return None, 0.0

    def harmonize_gsm(self, record: GSMRecord) -> GSMRecord:
        """Apply ML harmonization to a GSM record.

        Only updates fields where rules produced low confidence or no value.
        """
        fields_needing_ml = [
            f for f in _LABEL_TO_FIELD.values() if self._needs_ml(record, f)
        ]
        if not fields_needing_ml:
            return record

        text = self._build_text(record)
        if not text.strip():
            return record

        try:
            entities = self._run_ner(text)
        except Exception as e:
            raise MLInferenceError(f"NER failed for {record.gsm_id}: {e}") from e

        for ent in entities:
            label = ent.get("label", "")
            field = _LABEL_TO_FIELD.get(label)
            if field and field in fields_needing_ml:
                score = ent.get("score", 0.0)
                ent_text = ent.get("text", "")
                if score >= self.threshold:
                    ontology_id, _link_conf = self._link_entity(ent_text, field)
                    result = NormResult(
                        value=ent_text,
                        source="ml",
                        confidence=round(score, 4),
                        ontology_id=ontology_id,
                    )
                    _apply_norm(record, field, result)
                    fields_needing_ml.remove(field)
                elif score < self.review_threshold:
                    record.needs_review = True

        return record

    def harmonize_gse(self, record: GSERecord) -> GSERecord:
        """Apply ML harmonization to a GSE record."""
        gse_fields = ["disease", "tissue", "treatment"]
        fields_needing_ml = [f for f in gse_fields if self._needs_ml(record, f)]
        if not fields_needing_ml:
            return record

        text = self._build_gse_text(record)
        if not text.strip():
            return record

        try:
            entities = self._run_ner(text)
        except Exception as e:
            raise MLInferenceError(f"NER failed for {record.gse_id}: {e}") from e

        for ent in entities:
            label = ent.get("label", "")
            field = _LABEL_TO_FIELD.get(label)
            if field and field in fields_needing_ml:
                score = ent.get("score", 0.0)
                ent_text = ent.get("text", "")
                if score >= self.threshold:
                    ontology_id, _link_conf = self._link_entity(ent_text, field)
                    result = NormResult(
                        value=ent_text,
                        source="ml",
                        confidence=round(score, 4),
                        ontology_id=ontology_id,
                    )
                    _apply_norm(record, field, result)
                    fields_needing_ml.remove(field)
                elif score < self.review_threshold:
                    record.needs_review = True

        return record
