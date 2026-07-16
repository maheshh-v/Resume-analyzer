import httpx
import pytest

from app.pipeline.evidence.github import gather_github_evidence

REPOS_RESPONSE = [
    {"name": "ml-pipeline", "fork": False, "default_branch": "main"},
    {"name": "old-fork", "fork": True, "default_branch": "main"},
]
LANGUAGES_RESPONSE = {"Python": 42000, "Dockerfile": 300}
COMMIT_RESPONSE = {"sha": "abc123def456"}


def _make_transport(handler) -> httpx.MockTransport:
    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_matches_claim_to_repo_language_and_cites_pinned_commit():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/users/janedoe/repos":
            return httpx.Response(200, json=REPOS_RESPONSE)
        if request.url.path == "/repos/janedoe/ml-pipeline/languages":
            return httpx.Response(200, json=LANGUAGES_RESPONSE)
        if request.url.path == "/repos/janedoe/ml-pipeline/commits/main":
            return httpx.Response(200, json=COMMIT_RESPONSE)
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=_make_transport(handler)) as client:
        results = await gather_github_evidence(
            github_login="janedoe", claims=[("claim-1", "python")], client=client, token="fake-token"
        )

    assert len(results) == 1
    assert results[0].claim_id == "claim-1"
    assert results[0].verdict == "verified"
    assert "abc123def456" in results[0].artifact_url
    assert "ml-pipeline" in results[0].artifact_url


@pytest.mark.asyncio
async def test_forked_repos_are_never_used_as_evidence():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/users/janedoe/repos":
            return httpx.Response(200, json=[{"name": "old-fork", "fork": True, "default_branch": "main"}])
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=_make_transport(handler)) as client:
        results = await gather_github_evidence(github_login="janedoe", claims=[("claim-1", "python")], client=client)
    assert results == []


@pytest.mark.asyncio
async def test_no_claims_means_no_api_calls():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(200, json=[])

    async with httpx.AsyncClient(transport=_make_transport(handler)) as client:
        results = await gather_github_evidence(github_login="janedoe", claims=[], client=client)

    assert results == []
    assert calls == []


@pytest.mark.asyncio
async def test_no_github_login_writes_nothing_absence_never_penalizes():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    async with httpx.AsyncClient(transport=_make_transport(handler)) as client:
        results = await gather_github_evidence(github_login="", claims=[("claim-1", "python")], client=client)
    assert results == []


@pytest.mark.asyncio
async def test_user_not_found_degrades_to_no_evidence_not_an_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=_make_transport(handler)) as client:
        results = await gather_github_evidence(github_login="ghost-user", claims=[("claim-1", "python")], client=client)
    assert results == []
