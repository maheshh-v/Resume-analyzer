import io

import fitz
import pytest

from app.llm.prompts.claim_extraction import ExtractedClaim, ExtractedClaims
from app.llm.prompts.jd_extraction import ExtractedRequirement, ExtractedRequirements

JD_TEXT = "Senior ML Engineer.\nRequirements:\n- 3+ years of TensorFlow\n- Kubernetes in production"


def _make_pdf_bytes(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


async def _setup_candidate(client, fake_provider) -> tuple[str, str]:
    fake_provider.responses.append(
        ExtractedRequirements(
            requirements=[
                ExtractedRequirement(skill="TensorFlow", normalized_skill="TensorFlow", category="technical", importance="must_have", min_years=None, evidence_criteria="a repo", quoted_source_text="3+ years of TensorFlow"),
                ExtractedRequirement(skill="Kubernetes", normalized_skill="Kubernetes", category="technical", importance="must_have", min_years=None, evidence_criteria="a repo", quoted_source_text="Kubernetes in production"),
            ]
        )
    )
    job_resp = await client.post("/jobs", json={"title": "ML Engineer", "jd_raw": JD_TEXT})
    job_id = job_resp.json()["id"]
    candidate_resp = await client.post(f"/jobs/{job_id}/candidates", json={"name": "Jane Doe"})
    candidate_id = candidate_resp.json()["id"]

    fake_provider.responses.append(
        ExtractedClaims(claims=[ExtractedClaim(claim_type="skill", claim_text="TensorFlow", normalized_skill="TensorFlow", quoted_source_text="TensorFlow")])
    )
    pdf_bytes = _make_pdf_bytes("TensorFlow.")
    await client.post(f"/candidates/{candidate_id}/resume", files={"file": ("r.pdf", io.BytesIO(pdf_bytes), "application/pdf")})
    return job_id, candidate_id


@pytest.mark.asyncio
async def test_hiring_summary_has_no_score_field(client, fake_provider):
    _, candidate_id = await _setup_candidate(client, fake_provider)
    resp = await client.get(f"/candidates/{candidate_id}/report")
    assert resp.status_code == 200
    body = resp.json()

    assert "score" not in body
    assert "rank" not in body
    assert "recommendation" not in body
    assert body["evidence_coverage_total"] == 2  # TensorFlow (claimed) + Kubernetes (gap)
    assert any(row["skill"] == "Kubernetes" for row in body["needs_manual_verification"] + body["matrix"])


@pytest.mark.asyncio
async def test_record_decision(client, fake_provider):
    _, candidate_id = await _setup_candidate(client, fake_provider)
    resp = await client.post(f"/candidates/{candidate_id}/decision", json={"verdict": "advance", "rationale": "Strong TensorFlow evidence, Kubernetes unverified but not disqualifying."})
    assert resp.status_code == 201
    body = resp.json()
    assert body["verdict"] == "advance"
    assert body["candidate_id"] == candidate_id


@pytest.mark.asyncio
async def test_record_decision_rejects_invalid_verdict(client, fake_provider):
    _, candidate_id = await _setup_candidate(client, fake_provider)
    resp = await client.post(f"/candidates/{candidate_id}/decision", json={"verdict": "super_hire", "rationale": "x"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_report_scoped_to_owner(client, fake_provider, db_session):
    from app.auth.dependencies import get_current_user
    from app.main import app
    from app.models.user import User

    _, candidate_id = await _setup_candidate(client, fake_provider)

    other_user = User(auth_id="other-2", email="other2@example.com")
    db_session.add(other_user)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: other_user
    resp = await client.get(f"/candidates/{candidate_id}/report")
    assert resp.status_code == 404
