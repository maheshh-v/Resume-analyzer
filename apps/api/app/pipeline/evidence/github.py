"""Optional, high-precision, low-recall GitHub evidence.

Only runs when a candidate supplies a GitHub login. Never guesses a login from a name —
wrong-person attribution is a silent, catastrophic failure mode. Absence of a GitHub profile
(or absence of matching repos) writes NOTHING: no evidence row, no penalty. The claim simply
stays at its default `unverified` state. See docs/ARCHITECTURE.md — absence never subtracts.

MVP heuristic (deliberately simple, upgrade path is real): a claimed skill is "verified" if
it appears in the language breakdown of one of the candidate's own non-fork repos. This is
weak evidence on its own ("anyone can have a Python repo") — its real value per the product
plan is as *interview fuel*: the repo URL becomes the grounding artifact for a question that
only the actual author could answer.
"""

from dataclasses import dataclass

import httpx

GITHUB_API = "https://api.github.com"
_MAX_REPOS_TO_SCAN = 5


@dataclass
class GithubEvidenceDraft:
    claim_id: str
    verdict: str  # verified | partial
    summary: str
    artifact_url: str
    artifact_snippet: str


async def _get_json(client: httpx.AsyncClient, path: str, token: str | None) -> object:
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = await client.get(f"{GITHUB_API}{path}", headers=headers)
    response.raise_for_status()
    return response.json()


async def gather_github_evidence(
    *,
    github_login: str,
    claims: list[tuple[str, str]],  # (claim_id, normalized_skill)
    client: httpx.AsyncClient,
    token: str | None = None,
) -> list[GithubEvidenceDraft]:
    if not github_login or not claims:
        return []

    try:
        repos = await _get_json(client, f"/users/{github_login}/repos?type=owner&sort=pushed&per_page=20", token)
    except httpx.HTTPStatusError:
        return []

    non_fork_repos = [r for r in repos if not r.get("fork")][:_MAX_REPOS_TO_SCAN]
    if not non_fork_repos:
        return []

    drafts: list[GithubEvidenceDraft] = []
    matched_skills: set[str] = set()

    for repo in non_fork_repos:
        repo_name = repo["name"]
        try:
            languages = await _get_json(client, f"/repos/{github_login}/{repo_name}/languages", token)
            default_branch = repo.get("default_branch", "main")
            latest_commit = await _get_json(
                client, f"/repos/{github_login}/{repo_name}/commits/{default_branch}", token
            )
        except httpx.HTTPStatusError:
            continue

        repo_langs_lower = {lang.lower() for lang in languages}
        commit_sha = latest_commit.get("sha", default_branch)
        permalink = f"https://github.com/{github_login}/{repo_name}/tree/{commit_sha}"

        for claim_id, normalized_skill in claims:
            if normalized_skill in matched_skills or normalized_skill not in repo_langs_lower:
                continue
            matched_skills.add(normalized_skill)
            byte_count = languages[repo_langs_lower_original(languages, normalized_skill)]
            drafts.append(
                GithubEvidenceDraft(
                    claim_id=claim_id,
                    verdict="verified",
                    summary=f"'{normalized_skill}' appears as a primary language in their repo '{repo_name}'.",
                    artifact_url=permalink,
                    artifact_snippet=f"{normalized_skill}: {byte_count} bytes",
                )
            )

    return drafts


def repo_langs_lower_original(languages: dict, normalized_skill: str) -> str:
    for key in languages:
        if key.lower() == normalized_skill:
            return key
    raise KeyError(normalized_skill)
