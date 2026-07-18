"""The connector citation guardrail: URL 200 + literal substring.

Every external connector must pass its candidate evidence through here before it's allowed to
become an Evidence row. The promise the product makes is that a cited source *actually resolves*
and *actually contains* the quoted text — so this fetches the artifact URL live, requires a 200,
and requires the snippet to be a literal substring of the response body.

It delegates the substring test to `citation.snippet_is_literal_substring` — the sacred guardrail
function — and never reimplements it. Any failure (non-200, network error, snippet absent) returns
False, and the connector degrades to "unverified" (emits nothing). It NEVER raises into the
pipeline.
"""

from __future__ import annotations

import logging

import httpx

from app.pipeline.citation import snippet_is_literal_substring

logger = logging.getLogger(__name__)


async def artifact_resolves_with_snippet(
    client: httpx.AsyncClient, url: str, snippet: str, *, timeout: float = 15.0
) -> bool:
    """True only if `url` returns HTTP 200 AND `snippet` appears verbatim in the body."""
    if not url or not snippet or not snippet.strip():
        return False
    try:
        response = await client.get(url, timeout=timeout, follow_redirects=True)
    except httpx.HTTPError as exc:
        logger.info("citation guard: fetch failed for %s: %s", url, exc)
        return False
    if response.status_code != 200:
        logger.info("citation guard: %s returned %s", url, response.status_code)
        return False
    return snippet_is_literal_substring(response.text, snippet)
