import io

import fitz
import pytest

from app.llm.prompts.claim_extraction import ExtractedClaim, ExtractedClaims
from app.llm.prompts.jd_extraction import ExtractedRequirement, ExtractedRequirements

JD_TEXT = "Senior ML Engineer.\nRequirements:\n- 3+ years of TensorFlow"


def _make_pdf_bytes(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


def _jd_response():
    return ExtractedRequirements(
        requirements=[
            ExtractedRequirement(
                skill="TensorFlow",
                normalized_skill="TensorFlow",
                category="technical",
                importance="must_have",
                min_years=3,
                evidence_criteria="A repo using TensorFlow for 3+ years",
                quoted_source_text="3+ years of TensorFlow",
            )
        ]
    )


async def _create_job(client, fake_provider) -> str:
    fake_provider.responses.append(_jd_response())
    resp = await client.post("/jobs", json={"title": "ML Engineer", "jd_raw": JD_TEXT})
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_create_candidate_under_job(client, fake_provider):
    job_id = await _create_job(client, fake_provider)
    resp = await client.post(f"/jobs/{job_id}/candidates", json={"name": "Jane Doe", "email": "jane@example.com"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Jane Doe"
    assert body["status"] == "pending"


@pytest.mark.asyncio
async def test_resume_upload_extracts_claims_and_marks_ready(client, fake_provider):
    job_id = await _create_job(client, fake_provider)
    candidate_resp = await client.post(f"/jobs/{job_id}/candidates", json={"name": "Jane Doe"})
    candidate_id = candidate_resp.json()["id"]

    resume_text = "Jane Doe\n4 years TensorFlow at Acme Inc, 2021-01 to present."
    fake_provider.responses.append(
        ExtractedClaims(
            claims=[
                ExtractedClaim(
                    claim_type="skill",
                    claim_text="4 years TensorFlow",
                    normalized_skill="TensorFlow",
                    asserted_years=4,
                    quoted_source_text="4 years TensorFlow",
                )
            ]
        )
    )

    pdf_bytes = _make_pdf_bytes(resume_text)
    upload_resp = await client.post(
        f"/candidates/{candidate_id}/resume",
        files={"file": ("resume.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_resp.status_code == 200

    detail_resp = await client.get(f"/candidates/{candidate_id}")
    assert detail_resp.status_code == 200
    body = detail_resp.json()
    assert body["candidate"]["status"] == "ready", body["candidate"]
    assert len(body["claims"]) == 1
    assert body["claims"][0]["normalized_skill"] == "tensorflow"
    assert body["matches"][0]["status"] == "matched"


@pytest.mark.asyncio
async def test_resume_upload_rejects_non_pdf(client, fake_provider):
    job_id = await _create_job(client, fake_provider)
    candidate_resp = await client.post(f"/jobs/{job_id}/candidates", json={"name": "Jane Doe"})
    candidate_id = candidate_resp.json()["id"]

    resp = await client.post(
        f"/candidates/{candidate_id}/resume",
        files={"file": ("resume.txt", io.BytesIO(b"not a pdf"), "text/plain")},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_resume_upload_with_overlapping_employment_writes_consistency_evidence(client, fake_provider):
    job_id = await _create_job(client, fake_provider)
    candidate_resp = await client.post(f"/jobs/{job_id}/candidates", json={"name": "Jane Doe"})
    candidate_id = candidate_resp.json()["id"]

    fake_provider.responses.append(
        ExtractedClaims(
            claims=[
                ExtractedClaim(
                    claim_type="employment",
                    claim_text="Led ML platform at Acme",
                    asserted_org="Acme",
                    asserted_start="2021-01",
                    asserted_end="2023-01",
                    quoted_source_text="Led ML at Acme",
                ),
                ExtractedClaim(
                    claim_type="employment",
                    claim_text="MS at Stanford full-time",
                    asserted_org="Stanford",
                    asserted_start="2022-01",
                    asserted_end="2024-01",
                    quoted_source_text="MS Stanford full-time",
                ),
            ]
        )
    )

    pdf_bytes = _make_pdf_bytes("Led ML at Acme. MS Stanford full-time.")
    await client.post(
        f"/candidates/{candidate_id}/resume",
        files={"file": ("resume.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )

    detail_resp = await client.get(f"/candidates/{candidate_id}")
    body = detail_resp.json()
    assert body["candidate"]["status"] == "ready"
    contradicted = [e for e in body["evidence"] if e["verdict"] == "contradicted"]
    assert len(contradicted) == 2  # one row per claim in the overlapping pair
