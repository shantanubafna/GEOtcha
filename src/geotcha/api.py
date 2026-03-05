"""Python SDK for GEOtcha — no Typer/Rich dependency."""
from __future__ import annotations

import logging
from pathlib import Path

from geotcha.config import Settings
from geotcha.models import GSERecord

logger = logging.getLogger(__name__)


class GEOtchaClient:
    """Programmatic interface to GEOtcha functionality.

    Example::

        from geotcha import GEOtchaClient

        client = GEOtchaClient(ncbi_api_key="...")
        ids = client.search("ulcerative colitis")
        records = client.extract(ids[:5])
        records = client.harmonize(records)
    """

    def __init__(self, **kwargs) -> None:
        self.settings = Settings.load(**kwargs)

    def search(self, query: str) -> list[str]:
        """Search GEO and return filtered GSE IDs."""
        from geotcha.search.entrez import search_geo
        from geotcha.search.filters import filter_results
        from geotcha.search.query_builder import build_query

        expanded = build_query(query)
        raw_ids = search_geo(expanded, self.settings)
        return filter_results(raw_ids, self.settings, query=query)

    def extract(self, gse_ids: list[str]) -> list[GSERecord]:
        """Extract metadata for a list of GSE IDs."""
        from geotcha.extract.gse_parser import parse_gse

        records = []
        for gse_id in gse_ids:
            record = parse_gse(gse_id, self.settings)
            records.append(record)
        return records

    def harmonize(
        self, records: list[GSERecord], ml_mode: str = "off"
    ) -> list[GSERecord]:
        """Apply harmonization to all records and samples.

        Args:
            records: GSERecord list from extract().
            ml_mode: "off" (rules only), "hybrid" (rules+ML), or "full" (ML for all).
        """
        from geotcha.harmonize.rules import harmonize_gse, harmonize_gsm

        ml_harmonizer = None
        if ml_mode != "off":
            try:
                from geotcha.ml.inference import MLHarmonizer

                ml_harmonizer = MLHarmonizer.from_config(self.settings)
            except Exception:
                logger.warning("ML models could not be loaded. Continuing without ML.")

        for record in records:
            harmonize_gse(record)
            for sample in record.samples:
                harmonize_gsm(sample)
            if ml_harmonizer:
                record = ml_harmonizer.harmonize_gse(record)
                record.samples = [
                    ml_harmonizer.harmonize_gsm(s) for s in record.samples
                ]
        return records

    def export(
        self,
        records: list[GSERecord],
        output_dir: Path | None = None,
        fmt: str = "csv",
        harmonized: bool = False,
    ) -> dict[str, Path]:
        """Export records to files."""
        from geotcha.export.writers import write_all

        out = output_dir or self.settings.output_dir
        return write_all(records, out, fmt, harmonized)

    def run(
        self,
        query: str,
        output_dir: Path | None = None,
        harmonize: bool = False,
        fmt: str = "csv",
        ml_mode: str = "off",
    ) -> list[GSERecord]:
        """Run the full pipeline: search -> extract -> harmonize -> export."""
        ids = self.search(query)
        records = self.extract(ids)
        if harmonize:
            records = self.harmonize(records, ml_mode=ml_mode)
        self.export(records, output_dir, fmt, harmonize)
        return records
