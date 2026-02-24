"""Bio.Entrez wrappers for searching GEO."""

from __future__ import annotations

import logging
import urllib.error
from typing import Any

from Bio import Entrez
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from geotcha.cache import Cache
from geotcha.config import Settings
from geotcha.exceptions import NetworkError
from geotcha.rate_limiter import get_limiter

logger = logging.getLogger(__name__)


def _get_entrez_cache(settings: Settings) -> Cache:
    """Return a Cache instance pointed at the entrez sub-directory."""
    cache_dir = settings.get_cache_dir().parent / "entrez"
    return Cache(cache_dir, ttl_days=settings.cache_ttl_days)


def _configure_entrez(settings: Settings) -> None:
    """Configure Bio.Entrez with credentials."""
    Entrez.email = settings.ncbi_email or "geotcha@example.com"
    Entrez.tool = settings.ncbi_tool
    if settings.ncbi_api_key:
        Entrez.api_key = settings.ncbi_api_key


def _esearch(query: str, retstart: int, retmax: int, settings: Settings) -> dict[str, Any]:
    """Execute a single eSearch call with rate limiting and dynamic retry."""
    for attempt in Retrying(
        stop=stop_after_attempt(settings.max_retries),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        retry=retry_if_exception_type((IOError, RuntimeError, urllib.error.URLError, OSError)),
        reraise=True,
    ):
        with attempt:
            limiter = get_limiter(settings.get_effective_rate_limit())
            limiter.acquire()
            handle = Entrez.esearch(db="gds", term=query, retstart=retstart, retmax=retmax)
            result = Entrez.read(handle)
            handle.close()
            return dict(result)
    raise RuntimeError("unreachable")  # pragma: no cover


def search_geo(query: str, settings: Settings) -> list[str]:
    """Search GEO for datasets matching a query.

    Returns a list of GDS/GSE IDs from the gds database.
    Handles pagination automatically. Results are cached when enable_entrez_cache is True.
    """
    _configure_entrez(settings)

    cache_key = f"esearch:{query}"
    if settings.enable_entrez_cache:
        cache = _get_entrez_cache(settings)
        cached = cache.get(cache_key)
        if cached is not None:
            logger.info(f"Cache hit for esearch query ({len(cached)} IDs)")
            return cached

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

        if settings.enable_entrez_cache:
            cache.set(cache_key, all_ids)

        return all_ids
    except NetworkError:
        raise
    except (urllib.error.URLError, OSError) as e:
        raise NetworkError(
            f"Failed to connect to NCBI. Check your internet connection and try again. Details: {e}"
        ) from e


def _esummary_batch(ids: list[str], settings: Settings) -> list[dict[str, Any]]:
    """Fetch eSummary for a batch of IDs with dynamic retry."""
    for attempt in Retrying(
        stop=stop_after_attempt(settings.max_retries),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        retry=retry_if_exception_type((IOError, RuntimeError, urllib.error.URLError, OSError)),
        reraise=True,
    ):
        with attempt:
            limiter = get_limiter(settings.get_effective_rate_limit())
            limiter.acquire()
            handle = Entrez.esummary(db="gds", id=",".join(ids))
            result = Entrez.read(handle)
            handle.close()
            return [dict(r) for r in result]
    raise RuntimeError("unreachable")  # pragma: no cover


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

    Per-batch results are cached when enable_entrez_cache is True.
    """
    _configure_entrez(settings)
    summaries: list[dict[str, Any]] = []
    cache = _get_entrez_cache(settings) if settings.enable_entrez_cache else None

    try:
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            batch = ids[i : i + batch_size]
            cache_key = f"esummary:{','.join(sorted(batch))}"
            if cache:
                cached = cache.get(cache_key)
                if cached is not None:
                    logger.debug(f"Cache hit for esummary batch ({len(batch)} IDs)")
                    summaries.extend(cached)
                    continue

            batch_results = _esummary_batch(batch, settings)
            summaries.extend(batch_results)
            logger.debug(f"Fetched summaries for {len(batch)} IDs")

            if cache:
                cache.set(cache_key, batch_results)

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

    Batches 50 accessions per esearch call (down from 1 call per GSE).
    Per-GSE results are cached when enable_entrez_cache is True.
    Returns a dict mapping GSE accession to {"title": ..., "summary": ...}.
    """
    _configure_entrez(settings)
    result: dict[str, dict[str, str]] = {}
    cache = _get_entrez_cache(settings) if settings.enable_entrez_cache else None

    # Resolve cache hits first
    uncached: list[str] = []
    for gse_id in gse_ids:
        if cache:
            cached = cache.get(f"gse_summary:{gse_id}")
            if cached is not None:
                result[gse_id] = cached
                continue
        uncached.append(gse_id)

    # Batch-fetch uncached IDs (50 accessions per esearch call)
    batch_size = 50
    for i in range(0, len(uncached), batch_size):
        batch = uncached[i : i + batch_size]
        try:
            term = " OR ".join(f"{gid}[Accession]" for gid in batch)
            search_res = _esearch(term, retstart=0, retmax=len(batch) * 2, settings=settings)
            uids = search_res.get("IdList", [])
            if not uids:
                continue
            summaries = _esummary_batch(uids, settings)
            for s in summaries:
                acc = str(s.get("Accession", ""))
                if acc in batch:
                    entry: dict[str, str] = {
                        "title": str(s.get("title", "")),
                        "summary": str(s.get("summary", "")),
                    }
                    result[acc] = entry
                    if cache:
                        cache.set(f"gse_summary:{acc}", entry)
        except Exception as e:
            logger.debug(f"Batch GSE summary fetch failed for batch starting {batch[0]}: {e}")

    return result
