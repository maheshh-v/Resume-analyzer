"""Google Patents evidence: does a claimed inventor actually appear on granted patents?

Uses the public patents.google.com XHR search. Per ToS we stay light: results are cached
aggressively per inventor for the process lifetime so a batch of candidates never re-hammers the
endpoint, and only a handful of results are ever inspected. A name match to a patent is
corroborating but not conclusive (namesakes), so the verdict is *partial* — interview fuel.

The cited artifact is the patent's public page, and the guardrail re-fetches it and requires the
inventor's name to appear verbatim before a row is written.
"""

from __future__ import annotations

import logging

import httpx

from app.pipeline.evidence.base import EvidenceDraft
from app.pipeline.evidence.citation_guard import artifact_resolves_with_snippet

logger = logging.getLogger(__name__)

GOOGLE_PATENTS = "https://patents.google.com"
SOURCE_TYPE = "google_patents"
_MAX_PATENTS_TO_CHECK = 5

# Aggressive, process-lifetime cache of raw query results keyed by normalized inventor name, so a
# batch of candidates (or retries) never re-queries Google for the same name. Cleared on restart.
_query_cache: dict[str, list[dict]] = {}


def clear_cache() -> None:
    """Test/ops seam — drop the in-process patent-query cache."""
    _query_cache.clear()


async def _query_patents(client: httpx.AsyncClient, inventor_name: str, timeout: float) -> list[dict]:
    key = inventor_name.lower()
    if key in _query_cache:
        return _query_cache[key]
    try:
        response = await client.get(
            f"{GOOGLE_PATENTS}/xhr/query",
            params={"url": f"inventor={inventor_name}", "exp": ""},
            timeout=timeout,
        )
        response.raise_for_status()
        clusters = response.json().get("results", {}).get("cluster", [])
        patents = [
            entry["patent"]
            for cluster in clusters
            for entry in cluster.get("result", [])
            if isinstance(entry.get("patent"), dict)
        ]
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        logger.info("google_patents: query failed for %r: %s", inventor_name, exc)
        patents = []
    _query_cache[key] = patents
    return patents


async def gather_patent_evidence(
    *,
    inventor_name: str,
    claim_id: str,
    client: httpx.AsyncClient,
    timeout: float = 15.0,
) -> list[EvidenceDraft]:
    name = (inventor_name or "").strip()
    if not name or not claim_id:
        return []

    patents = await _query_patents(client, name, timeout)
    for patent in patents[:_MAX_PATENTS_TO_CHECK]:
        publication_number = (patent.get("publication_number") or "").strip()
        title = (patent.get("title") or "").strip()
        if not publication_number:
            continue

        artifact_url = f"{GOOGLE_PATENTS}/patent/{publication_number}/en"
        # The patent page must both resolve and literally name this inventor — a title match alone
        # could be a different person's patent.
        if not await artifact_resolves_with_snippet(client, artifact_url, name, timeout=timeout):
            continue

        return [
            EvidenceDraft(
                claim_id=claim_id,
                source_type=SOURCE_TYPE,
                verdict="partial",
                summary=(
                    f"Named inventor on patent {publication_number}"
                    + (f" ('{title}')" if title else "")
                    + f". Corroborating for '{name}'; confirm it's the same person."
                ),
                artifact_url=artifact_url,
                artifact_snippet=name,
            )
        ]

    return []
