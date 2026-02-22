"""Disease variant expansion mappings."""

from __future__ import annotations

# Re-export from query_builder for consistency
from geotcha.search.query_builder import DISEASE_EXPANSIONS, expand_disease_terms

__all__ = ["DISEASE_EXPANSIONS", "expand_disease_terms"]
