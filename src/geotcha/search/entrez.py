"""Bio.Entrez wrappers for searching GEO."""

from __future__ import annotations

import logging
import urllib.error
from typing import Any

from Bio import Entrez
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from geotcha.config import Settings
from geotcha.exceptions import NetworkError
from geotcha.rate_limiter import get_limiter

logger = logging.getLogger(__name__)


def _configure_entrez(settings: Settings) -> None:
    """Configure Bio.Entrez with credentials."""
    Entrez.email = settings.ncbi_email or "geotcha@example.com"
    Entrez.tool = settings.ncbi_tool
    if settings.ncbi_api_key:
        Entrez.api_key = settings.ncbi_api_key


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=30),
    retry=retry_if_exception_type((IOError, RuntimeError, urllib.error.URLError, OSError)),
)
def _esearch(query: str, retstart: int, retmax: int, settings: Settings) -> dict[str, Any]:
    """Execute a single eSearch call with rate limiting and retry."""
    limiter = get_limiter(settings.get_effective_rate_limit())
    limiter.acquire()
    handle = Entrez.esearch(db="gds", term=query, retstart=retstart, retmax=retmax)
    result = Entrez.read(handle)
    handle.close()
    return dict(result)


def search_geo(query: str, settings: Settings) -> list[str]:
    """Search GEO for datasets matching a query.

    Returns a list of GDS/GSE IDs from the gds database.
    Handles pagination automatically.
    """
    _configure_entrez(settings)

    try:
        # First call to get total count
        result = _esearch(query, retstart=0, retmax=1, settings=settings)
        total = int(result.get("Count", 0))
        logger.info(f"Search returned {total} total results for query: {query[:80]}")

        if total == 0:
            return []

        # Paginate through all results
        all_ids: list[str] = []
        batch_size = 500
        for start in range(0, total, batch_size):
            result = _esearch(query, retstart=start, retmax=batch_size, settings=settings)
            ids = result.get("IdList", [])
            all_ids.extend(ids)
            logger.debug(f"Fetched {len(ids)} IDs (offset {start})")

        logger.info(f"Total IDs collected: {len(all_ids)}")
        return all_ids
    except NetworkError:
        raise
    except (urllib.error.URLError, OSError) as e:
        raise NetworkError(
            f"Failed to connect to NCBI. Check your internet connection and try again. Details: {e}"
        ) from e


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=30),
    retry=retry_if_exception_type((IOError, RuntimeError, urllib.error.URLError, OSError)),
)
def _esummary_batch(ids: list[str], settings: Settings) -> list[dict[str, Any]]:
    """Fetch eSummary for a batch of IDs."""
    limiter = get_limiter(settings.get_effective_rate_limit())
    limiter.acquire()
    handle = Entrez.esummary(db="gds", id=",".join(ids))
    result = Entrez.read(handle)
    handle.close()
    return [dict(r) for r in result]


def get_summaries(ids: list[str], settings: Settings) -> list[dict[str, Any]]:
    """Get eSummary data for a list of GDS IDs.

    Returns list of summary dictionaries with fields like:
    - Accession (e.g., GSE12345)
    - title
    - summary
    - GPL (platform)
    - GSE (series accession)
    - taxon (organism)
    - gdsType (data type)
    - n_samples
    """
    _configure_entrez(settings)
    summaries: list[dict[str, Any]] = []

    try:
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            batch = ids[i : i + batch_size]
            batch_results = _esummary_batch(batch, settings)
            summaries.extend(batch_results)
            logger.debug(f"Fetched summaries for {len(batch)} IDs")

        return summaries
    except NetworkError:
        raise
    except (urllib.error.URLError, OSError) as e:
        raise NetworkError(
            "Failed to fetch summaries from NCBI. "
            f"Check your internet connection and try again. Details: {e}"
        ) from e


def get_gse_summaries(
    gse_ids: list[str], settings: Settings
) -> dict[str, dict[str, str]]:
    """Get title and summary for a list of GSE accessions.

    Searches the GDS database for each GSE ID and returns a dict mapping
    GSE accession to {"title": ..., "summary": ...}.
    """
    _configure_entrez(settings)
    result: dict[str, dict[str, str]] = {}

    for gse_id in gse_ids:
        try:
            limiter = get_limiter(settings.get_effective_rate_limit())
            limiter.acquire()
            handle = Entrez.esearch(db="gds", term=f"{gse_id}[Accession]", retmax=1)
            search_result = Entrez.read(handle)
            handle.close()

            ids = search_result.get("IdList", [])
            if ids:
                summaries = _esummary_batch(ids, settings)
                if summaries:
                    result[gse_id] = {
                        "title": str(summaries[0].get("title", "")),
                        "summary": str(summaries[0].get("summary", "")),
                    }
        except Exception as e:
            logger.debug(f"Failed to get summary for {gse_id}: {e}")

    return result
