"""Package-ownership evidence: does the candidate actually own the packages they imply?

Two modes, both free-API and both guardrail-gated:

  - Explicit package claims (ecosystem + package + handle): confirm the handle is a listed
    maintainer/author of that exact package. This is strong — verdict *verified*.
  - npm handle search: find packages maintained by an npm username (we opportunistically try the
    candidate's GitHub login, since handles are often shared). Ownership by that npm account is
    certain, but that the candidate *is* that account is not — verdict *partial*.

The cited artifact is the canonical registry metadata endpoint, where the handle provably appears;
the guardrail re-fetches it and requires the handle verbatim. Absence writes nothing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from app.pipeline.evidence.base import EvidenceDraft
from app.pipeline.evidence.citation_guard import artifact_resolves_with_snippet

logger = logging.getLogger(__name__)

NPM_REGISTRY = "https://registry.npmjs.org"
PYPI = "https://pypi.org"
SOURCE_TYPE = "package_ownership"
_MAX_PACKAGES = 5


@dataclass
class PackageClaim:
    ecosystem: str  # "npm" | "pypi"
    package: str
    handle: str  # the maintainer/author name the candidate claims to be


async def _json(client: httpx.AsyncClient, url: str, timeout: float, **params) -> dict | None:
    try:
        response = await client.get(url, params=params or None, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.info("package_ownership: fetch failed for %s: %s", url, exc)
        return None


async def _verified_draft(
    *, claim_id: str, artifact_url: str, handle: str, client: httpx.AsyncClient, timeout: float, verdict: str, summary: str
) -> EvidenceDraft | None:
    if not await artifact_resolves_with_snippet(client, artifact_url, handle, timeout=timeout):
        return None
    return EvidenceDraft(
        claim_id=claim_id,
        source_type=SOURCE_TYPE,
        verdict=verdict,
        summary=summary,
        artifact_url=artifact_url,
        artifact_snippet=handle,
    )


async def _check_npm_package(pc: PackageClaim, claim_id: str, client: httpx.AsyncClient, timeout: float) -> EvidenceDraft | None:
    data = await _json(client, f"{NPM_REGISTRY}/{pc.package}", timeout)
    if not data:
        return None
    maintainers = {m.get("name") for m in data.get("maintainers", []) if isinstance(m, dict)}
    if pc.handle not in maintainers:
        return None
    return await _verified_draft(
        claim_id=claim_id,
        artifact_url=f"{NPM_REGISTRY}/{pc.package}",
        handle=pc.handle,
        client=client,
        timeout=timeout,
        verdict="verified",
        summary=(
            f"'{pc.handle}' is a listed maintainer of the npm package '{pc.package}' "
            f"(https://www.npmjs.com/package/{pc.package})."
        ),
    )


async def _check_pypi_package(pc: PackageClaim, claim_id: str, client: httpx.AsyncClient, timeout: float) -> EvidenceDraft | None:
    data = await _json(client, f"{PYPI}/pypi/{pc.package}/json", timeout)
    if not data:
        return None
    info = data.get("info", {})
    owners = f"{info.get('author') or ''}\n{info.get('maintainer') or ''}"
    if pc.handle not in owners:  # exact-case substring so the snippet is provably present
        return None
    return await _verified_draft(
        claim_id=claim_id,
        artifact_url=f"{PYPI}/pypi/{pc.package}/json",
        handle=pc.handle,
        client=client,
        timeout=timeout,
        verdict="verified",
        summary=(
            f"'{pc.handle}' is listed as author/maintainer of the PyPI package '{pc.package}' "
            f"(https://pypi.org/project/{pc.package}/)."
        ),
    )


async def _search_npm_by_maintainer(handle: str, claim_id: str, client: httpx.AsyncClient, timeout: float) -> list[EvidenceDraft]:
    data = await _json(
        client, f"{NPM_REGISTRY}/-/v1/search", timeout, text=f"maintainer:{handle}", size=_MAX_PACKAGES
    )
    if not data:
        return []
    drafts: list[EvidenceDraft] = []
    for obj in data.get("objects", [])[:_MAX_PACKAGES]:
        package = (obj.get("package", {}) or {}).get("name")
        if not package:
            continue
        draft = await _verified_draft(
            claim_id=claim_id,
            artifact_url=f"{NPM_REGISTRY}/{package}",
            handle=handle,
            client=client,
            timeout=timeout,
            verdict="partial",
            summary=(
                f"npm account '{handle}' maintains the package '{package}' "
                f"(https://www.npmjs.com/package/{package}). Confirm the candidate owns that account."
            ),
        )
        if draft:
            drafts.append(draft)
    return drafts


async def gather_package_ownership_evidence(
    *,
    claim_id: str,
    client: httpx.AsyncClient,
    npm_handle: str | None = None,
    package_claims: list[PackageClaim] | None = None,
    timeout: float = 15.0,
) -> list[EvidenceDraft]:
    if not claim_id:
        return []

    drafts: list[EvidenceDraft] = []
    for pc in package_claims or []:
        if pc.ecosystem == "npm":
            draft = await _check_npm_package(pc, claim_id, client, timeout)
        elif pc.ecosystem == "pypi":
            draft = await _check_pypi_package(pc, claim_id, client, timeout)
        else:
            draft = None
        if draft:
            drafts.append(draft)

    if npm_handle and npm_handle.strip():
        drafts.extend(await _search_npm_by_maintainer(npm_handle.strip(), claim_id, client, timeout))

    return drafts
