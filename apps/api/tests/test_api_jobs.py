import pytest

from app.llm.prompts.jd_extraction import ExtractedRequirement, ExtractedRequirements

JD_TEXT = "Senior Backend Engineer.\nRequirements:\n- 3+ years of Python\n- Kubernetes experience"


def _jd_response():
    return ExtractedRequirements(
        requirements=[
            ExtractedRequirement(
                skill="Python",
                normalized_skill="Python",
                category="technical",
                importance="must_have",
                min_years=3,
                evidence_criteria="A repo or role using Python for 3+ years",
                quoted_source_text="3+ years of Python",
            ),
            ExtractedRequirement(
                skill="Kubernetes",
                normalized_skill="Kubernetes",
                category="technical",
                importance="nice_to_have",
                min_years=None,
                evidence_criteria="A repo with k8s manifests",
                quoted_source_text="Kubernetes experience",
            ),
        ]
    )


@pytest.mark.asyncio
async def test_create_job_extracts_requirements(client, fake_provider):
    fake_provider.responses.append(_jd_response())

    response = await client.post("/api/v1/jobs", json={"title": "Backend Engineer", "jd_raw": JD_TEXT})

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Backend Engineer"
    assert body["requirements_status"] == "draft"
    assert len(body["requirements"]) == 2
    assert {r["skill"] for r in body["requirements"]} == {"Python", "Kubernetes"}


@pytest.mark.asyncio
async def test_list_jobs_includes_candidate_count(client, fake_provider):
    fake_provider.responses.append(_jd_response())
    create_resp = await client.post("/api/v1/jobs", json={"title": "Backend Engineer", "jd_raw": JD_TEXT})
    job_id = create_resp.json()["id"]

    await client.post(f"/api/v1/jobs/{job_id}/candidates", json={"name": "Jane Doe"})

    list_resp = await client.get("/api/v1/jobs")
    assert list_resp.status_code == 200
    jobs = list_resp.json()
    assert len(jobs) == 1
    assert jobs[0]["candidate_count"] == 1


@pytest.mark.asyncio
async def test_get_job_not_found_returns_404(client):
    response = await client.get("/api/v1/jobs/does-not-exist")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_replace_requirements_marks_reviewed(client, fake_provider):
    fake_provider.responses.append(_jd_response())
    create_resp = await client.post("/api/v1/jobs", json={"title": "Backend Engineer", "jd_raw": JD_TEXT})
    job_id = create_resp.json()["id"]

    replace_resp = await client.put(
        f"/api/v1/jobs/{job_id}/requirements",
        json={
            "requirements": [
                {
                    "skill": "Go",
                    "normalized_skill": "go",
                    "category": "technical",
                    "importance": "must_have",
                    "min_years": 2,
                    "evidence_criteria": "A repo in Go",
                }
            ]
        },
    )
    assert replace_resp.status_code == 200
    body = replace_resp.json()
    assert body["requirements_status"] == "reviewed"
    assert len(body["requirements"]) == 1
    assert body["requirements"][0]["skill"] == "Go"


@pytest.mark.asyncio
async def test_jobs_are_scoped_to_owner(client, fake_provider, db_session):
    from app.models.user import User

    other_user = User(auth_id="other-auth-id", email="other@example.com")
    db_session.add(other_user)
    await db_session.commit()

    fake_provider.responses.append(_jd_response())
    create_resp = await client.post("/api/v1/jobs", json={"title": "Backend Engineer", "jd_raw": JD_TEXT})
    job_id = create_resp.json()["id"]

    from app.auth.dependencies import get_current_user
    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: other_user
    response = await client.get(f"/api/v1/jobs/{job_id}")
    assert response.status_code == 404
