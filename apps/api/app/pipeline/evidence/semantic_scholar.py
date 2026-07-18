"""Semantic Scholar evidence: does a claimed researcher actually have a publication record?

Free API, no key. Searches authors by name and, on an exact name match with at least one paper,
emits a *partial* verdict — a name match to an author profile is corroborating but not conclusive
(namesakes exist), so it's interview fuel, never proof. Absence writes nothing.

The cited artifact is the author's detail endpoint, and the guardrail re-fetches it and requires
the author's name to appear verbatim before any row is written.
"""

from __future__ import annotations

import logging

import httpx

from app.pipeline.evidence.base import EvidenceDraft
from app.pipeline.evidence.citation_guard import artifact_resolves_with_snippet

logger = logging.getLogger(__name__)

SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org"
SOURCE_TYPE = "semantic_scholar"
_MAX_CANDIDATES_TO_CHECK = 5


async def gather_semantic_scholar_evidence(
    *,
    author_name: str,
    claim_id: str,
    client: httpx.AsyncClient,
    min_papers: int = 1,
    timeout: float = 15.0,
) -> list[EvidenceDraft]:
    name = (author_name or "").strip()
    if not name or not claim_id:
        return []

    try:
        response = await client.get(
            f"{SEMANTIC_SCHOLAR_API}/graph/v1/author/search",
            params={"query": name, "fields": "name,paperCount,citationCount", "limit": _MAX_CANDIDATES_TO_CHECK},
            timeout=timeout,
        )
        response.raise_for_status()
        authors = response.json().get("data", [])
    except (httpx.HTTPError, ValueError) as exc:
        logger.info("semantic_scholar: search failed for %r: %s", name, exc)
        return []

    for author in authors:
        author_id = author.get("authorId")
        if not author_id or (author.get("name", "").strip().lower() != name.lower()):
            continue
        if (author.get("paperCount") or 0) < min_papers:
            continue

        artifact_url = f"{SEMANTIC_SCHOLAR_API}/graph/v1/author/{author_id}?fields=name,paperCount,citationCount"
        if not await artifact_resolves_with_snippet(client, artifact_url, name, timeout=timeout):
            continue  # citation guardrail failed -> degrade to unverified (emit nothing)

        papers = author.get("paperCount") or 0
        citations = author.get("citationCount") or 0
        return [
            EvidenceDraft(
                claim_id=claim_id,
                source_type=SOURCE_TYPE,
                verdict="partial",
                summary=(
                    f"Semantic Scholar author profile matches '{name}' — {papers} papers, "
                    f"{citations} citations. Corroborating, but confirm it's the same person "
                    f"(profile: https://www.semanticscholar.org/author/{author_id})."
                ),
                artifact_url=artifact_url,
                artifact_snippet=name,
            )
        ]

    return []
