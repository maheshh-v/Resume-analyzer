"""Fixture-based tests for the evidence connectors + the citation guardrail.

Every HTTP call — the connector's data fetch AND the guardrail's verification fetch — is served
by an httpx.MockTransport handler, so nothing here touches the network. This is the "recorded
JSON" approach the prompt calls for.
"""

import httpx
import pytest

from app.pipeline.evidence import google_patents
from app.pipeline.evidence.citation_guard import artifact_resolves_with_snippet
from app.pipeline.evidence.google_patents import gather_patent_evidence
from app.pipeline.evidence.package_ownership import PackageClaim, gather_package_ownership_evidence
from app.pipeline.evidence.semantic_scholar import gather_semantic_scholar_evidence


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


# --- Citation guardrail ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_guard_true_when_200_and_snippet_present():
    async with _client(lambda r: httpx.Response(200, text="hello Jane Doe world")) as c:
        assert await artifact_resolves_with_snippet(c, "https://x/y", "Jane Doe") is True


@pytest.mark.asyncio
async def test_guard_false_on_non_200():
    async with _client(lambda r: httpx.Response(404, text="Jane Doe")) as c:
        assert await artifact_resolves_with_snippet(c, "https://x/y", "Jane Doe") is False


@pytest.mark.asyncio
async def test_guard_false_when_snippet_absent():
    async with _client(lambda r: httpx.Response(200, text="someone else entirely")) as c:
        assert await artifact_resolves_with_snippet(c, "https://x/y", "Jane Doe") is False


@pytest.mark.asyncio
async def test_guard_false_on_network_error():
    def boom(r):
        raise httpx.ConnectError("down")

    async with _client(boom) as c:
        assert await artifact_resolves_with_snippet(c, "https://x/y", "Jane Doe") is False


@pytest.mark.asyncio
async def test_guard_false_on_empty_inputs():
    async with _client(lambda r: httpx.Response(200, text="x")) as c:
        assert await artifact_resolves_with_snippet(c, "", "Jane Doe") is False
        assert await artifact_resolves_with_snippet(c, "https://x/y", "  ") is False


# --- Semantic Scholar -----------------------------------------------------------------------


def _scholar_handler(*, name="Wei Chen", papers=12, detail_body=None, detail_status=200):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/graph/v1/author/search":
            return httpx.Response(200, json={"data": [{"authorId": "49", "name": name, "paperCount": papers, "citationCount": 345}]})
        if request.url.path.startswith("/graph/v1/author/49"):
            return httpx.Response(detail_status, json=detail_body if detail_body is not None else {"name": name, "paperCount": papers})
        return httpx.Response(404)

    return handler


@pytest.mark.asyncio
async def test_semantic_scholar_partial_on_name_match_and_guardrail_pass():
    async with _client(_scholar_handler()) as c:
        drafts = await gather_semantic_scholar_evidence(author_name="Wei Chen", claim_id="claim-1", client=c)
    assert len(drafts) == 1
    d = drafts[0]
    assert d.verdict == "partial"
    assert d.source_type == "semantic_scholar"
    assert d.artifact_snippet == "Wei Chen"
    assert d.claim_id == "claim-1"


@pytest.mark.asyncio
async def test_semantic_scholar_ignores_namesake_mismatch():
    async with _client(_scholar_handler(name="Weiqiang Chen")) as c:
        drafts = await gather_semantic_scholar_evidence(author_name="Wei Chen", claim_id="claim-1", client=c)
    assert drafts == []


@pytest.mark.asyncio
async def test_semantic_scholar_degrades_when_guardrail_fails():
    # Detail endpoint doesn't contain the name -> guardrail fails -> nothing written.
    async with _client(_scholar_handler(detail_body={"name": "Someone Else", "paperCount": 3})) as c:
        drafts = await gather_semantic_scholar_evidence(author_name="Wei Chen", claim_id="claim-1", client=c)
    assert drafts == []


@pytest.mark.asyncio
async def test_semantic_scholar_empty_name_makes_no_calls():
    calls = []

    def handler(r):
        calls.append(r.url.path)
        return httpx.Response(200, json={"data": []})

    async with _client(handler) as c:
        drafts = await gather_semantic_scholar_evidence(author_name="  ", claim_id="claim-1", client=c)
    assert drafts == []
    assert calls == []


# --- Google Patents -------------------------------------------------------------------------


def _patents_handler(*, inventor="Grace Hopper", patent_page_contains="Grace Hopper", query_counter=None):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/xhr/query":
            if query_counter is not None:
                query_counter.append(1)
            return httpx.Response(
                200,
                json={"results": {"cluster": [{"result": [{"patent": {"publication_number": "US1234567B2", "title": "A Compiler"}}]}]}},
            )
        if request.url.path == "/patent/US1234567B2/en":
            return httpx.Response(200, text=f"Patent page. Inventor: {patent_page_contains}. Filed 1952.")
        return httpx.Response(404)

    return handler


@pytest.mark.asyncio
async def test_patents_partial_when_inventor_on_page():
    google_patents.clear_cache()
    async with _client(_patents_handler()) as c:
        drafts = await gather_patent_evidence(inventor_name="Grace Hopper", claim_id="claim-2", client=c)
    assert len(drafts) == 1
    assert drafts[0].verdict == "partial"
    assert "US1234567B2" in drafts[0].artifact_url
    assert drafts[0].artifact_snippet == "Grace Hopper"


@pytest.mark.asyncio
async def test_patents_degrades_when_page_lacks_inventor():
    google_patents.clear_cache()
    async with _client(_patents_handler(patent_page_contains="Someone Else")) as c:
        drafts = await gather_patent_evidence(inventor_name="Grace Hopper", claim_id="claim-2", client=c)
    assert drafts == []


@pytest.mark.asyncio
async def test_patents_caches_query_by_inventor():
    google_patents.clear_cache()
    counter: list[int] = []
    handler = _patents_handler(query_counter=counter)
    async with _client(handler) as c:
        await gather_patent_evidence(inventor_name="Grace Hopper", claim_id="claim-2", client=c)
        await gather_patent_evidence(inventor_name="Grace Hopper", claim_id="claim-3", client=c)
    assert len(counter) == 1  # second call served from cache, not re-queried


# --- Package ownership ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_package_ownership_npm_verified_for_explicit_package():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/left-pad":
            return httpx.Response(200, json={"maintainers": [{"name": "janedoe"}], "name": "left-pad"})
        return httpx.Response(404)

    async with _client(handler) as c:
        drafts = await gather_package_ownership_evidence(
            claim_id="claim-3", client=c,
            package_claims=[PackageClaim(ecosystem="npm", package="left-pad", handle="janedoe")],
        )
    assert len(drafts) == 1
    assert drafts[0].verdict == "verified"
    assert drafts[0].source_type == "package_ownership"


@pytest.mark.asyncio
async def test_package_ownership_npm_rejects_non_maintainer():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"maintainers": [{"name": "someone-else"}], "name": "left-pad"})

    async with _client(handler) as c:
        drafts = await gather_package_ownership_evidence(
            claim_id="claim-3", client=c,
            package_claims=[PackageClaim(ecosystem="npm", package="left-pad", handle="janedoe")],
        )
    assert drafts == []


@pytest.mark.asyncio
async def test_package_ownership_pypi_verified_when_author_matches():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/pypi/coolpkg/json":
            return httpx.Response(200, json={"info": {"author": "Jane Doe (janedoe)", "maintainer": None}})
        return httpx.Response(404)

    async with _client(handler) as c:
        drafts = await gather_package_ownership_evidence(
            claim_id="claim-3", client=c,
            package_claims=[PackageClaim(ecosystem="pypi", package="coolpkg", handle="janedoe")],
        )
    assert len(drafts) == 1
    assert drafts[0].verdict == "verified"


@pytest.mark.asyncio
async def test_package_ownership_npm_handle_search_is_partial():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/-/v1/search":
            return httpx.Response(200, json={"objects": [{"package": {"name": "cool-lib"}}]})
        if request.url.path == "/cool-lib":
            return httpx.Response(200, json={"maintainers": [{"name": "janedoe"}], "name": "cool-lib"})
        return httpx.Response(404)

    async with _client(handler) as c:
        drafts = await gather_package_ownership_evidence(claim_id="claim-3", client=c, npm_handle="janedoe")
    assert len(drafts) == 1
    assert drafts[0].verdict == "partial"
    assert "cool-lib" in drafts[0].artifact_url


@pytest.mark.asyncio
async def test_package_ownership_empty_claim_id_is_noop():
    async with _client(lambda r: httpx.Response(200, json={})) as c:
        drafts = await gather_package_ownership_evidence(claim_id="", client=c, npm_handle="janedoe")
    assert drafts == []


# --- Orchestrate wiring ---------------------------------------------------------------------


async def test_orchestrate_writes_connector_evidence_when_flag_enabled(db_session, monkeypatch, test_user):
    """When a connector flag is on, orchestrate persists its (already-guardrail-passed) drafts as
    Evidence rows and records a ledger event. Connector is mocked — no network."""
    from types import SimpleNamespace

    from sqlalchemy import select

    from app.models.candidate import Candidate
    from app.models.claim import Claim
    from app.models.document import Document
    from app.models.evidence import Evidence
    from app.models.job import Job
    from app.pipeline import orchestrate
    from app.pipeline.evidence.base import EvidenceDraft

    job = Job(owner_user_id=test_user.id, title="T", jd_raw="jd", requirements_status="draft")
    db_session.add(job)
    await db_session.flush()
    candidate = Candidate(owner_user_id=test_user.id, job_id=job.id, name="Jane", github_login="janedoe", status="processing")
    db_session.add(candidate)
    await db_session.flush()
    document = Document(candidate_id=candidate.id, kind="resume", filename="r.pdf", content_hash="h",
                        storage_path="p", extracted_text="Python", page_offsets=[[0, 6]], size_bytes=6)
    db_session.add(document)
    await db_session.flush()
    claim = Claim(candidate_id=candidate.id, document_id=document.id, claim_type="skill", claim_text="Python",
                  normalized_skill="python", source_span_start=0, source_span_end=6, extractor_model="fake", prompt_version="v1")
    db_session.add(claim)
    await db_session.flush()

    monkeypatch.setattr(
        orchestrate, "get_settings",
        lambda: SimpleNamespace(enable_semantic_scholar=False, enable_google_patents=False, enable_package_ownership=True),
    )

    async def fake_pkg(**kwargs):
        return [EvidenceDraft(claim_id=kwargs["claim_id"], source_type="package_ownership",
                              verdict="partial", summary="owns cool-lib", artifact_url="https://x", artifact_snippet="janedoe")]

    monkeypatch.setattr(orchestrate, "gather_package_ownership_evidence", fake_pkg)

    await orchestrate._gather_connector_evidence(db_session, candidate=candidate, claim_rows=[claim])
    await db_session.commit()

    rows = (await db_session.execute(select(Evidence).where(Evidence.source_type == "package_ownership"))).scalars().all()
    assert len(rows) == 1
    assert rows[0].claim_id == claim.id
    assert rows[0].verdict == "partial"
