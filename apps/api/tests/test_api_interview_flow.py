import io

import fitz
import pytest

from app.llm.prompts.claim_extraction import ExtractedClaim, ExtractedClaims
from app.llm.prompts.interview_evaluation import AnswerEvaluation
from app.llm.prompts.interview_question import QuestionDraft
from app.llm.prompts.jd_extraction import ExtractedRequirement, ExtractedRequirements

JD_TEXT = "Senior ML Engineer.\nRequirements:\n- 3+ years of TensorFlow\n- Kubernetes in production"


def _make_pdf_bytes(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


async def _setup_candidate_with_two_unverified_must_haves(client, fake_provider) -> str:
    fake_provider.responses.append(
        ExtractedRequirements(
            requirements=[
                ExtractedRequirement(
                    skill="TensorFlow", normalized_skill="TensorFlow", category="technical", importance="must_have",
                    min_years=None, evidence_criteria="a repo", quoted_source_text="3+ years of TensorFlow",
                ),
                ExtractedRequirement(
                    skill="Kubernetes", normalized_skill="Kubernetes", category="technical", importance="must_have",
                    min_years=None, evidence_criteria="a repo", quoted_source_text="Kubernetes in production",
                ),
            ]
        )
    )
    job_resp = await client.post("/api/v1/jobs", json={"title": "ML Engineer", "jd_raw": JD_TEXT})
    job_id = job_resp.json()["id"]

    candidate_resp = await client.post(f"/api/v1/jobs/{job_id}/candidates", json={"name": "Jane Doe"})
    candidate_id = candidate_resp.json()["id"]

    fake_provider.responses.append(
        ExtractedClaims(
            claims=[
                ExtractedClaim(claim_type="skill", claim_text="TensorFlow", normalized_skill="TensorFlow", quoted_source_text="TensorFlow"),
                ExtractedClaim(claim_type="skill", claim_text="Kubernetes", normalized_skill="Kubernetes", quoted_source_text="Kubernetes"),
            ]
        )
    )
    pdf_bytes = _make_pdf_bytes("TensorFlow. Kubernetes.")
    await client.post(f"/api/v1/candidates/{candidate_id}/resume", files={"file": ("r.pdf", io.BytesIO(pdf_bytes), "application/pdf")})

    return candidate_id


def _question(text: str, must_mention: list[str]) -> QuestionDraft:
    return QuestionDraft(question_text=text, rubric_must_mention=must_mention, rubric_bluffer_tells=["vague"], rationale="probe")


def _evaluation(verdict: str, notes: str) -> AnswerEvaluation:
    return AnswerEvaluation(specificity_verdict=verdict, specificity_notes=notes, rubric_points_hit=[], rubric_points_missed=[])


@pytest.mark.asyncio
async def test_full_interview_flow_strong_then_strong_completes(client, fake_provider):
    candidate_id = await _setup_candidate_with_two_unverified_must_haves(client, fake_provider)
    token = (await client.post(f"/api/v1/candidates/{candidate_id}/interviews")).json()["token"]

    # GET lazily generates the base question for claim 1.
    fake_provider.responses.append(_question("Tell me about a TensorFlow retracing bug you hit.", ["retracing"]))
    state = (await client.get(f"/api/v1/interview/{token}")).json()
    assert state["is_complete"] is False
    q1_id = state["current_question"]["id"]

    # Answering strongly resolves claim 1; submit_answer chains into get_interview_state,
    # which immediately (lazily) generates claim 2's base question in the same call.
    fake_provider.responses.append(_evaluation("strong", "named the retracing bug precisely"))
    fake_provider.responses.append(_question("Walk me through a k8s rollout you owned.", ["rollout"]))
    state = (await client.post(f"/api/v1/interview/{token}/questions/{q1_id}/answer", json={"answer_text": "We hit input-shape retracing on every batch..."})).json()
    assert state["is_complete"] is False
    q2_id = state["current_question"]["id"]
    assert q2_id != q1_id

    # Answering strongly resolves claim 2 — no targets remain, so no further LLM call.
    fake_provider.responses.append(_evaluation("strong", "named a real rollout with numbers"))
    state = (await client.post(f"/api/v1/interview/{token}/questions/{q2_id}/answer", json={"answer_text": "I owned a blue-green rollout across 12 nodes..."})).json()

    assert state["is_complete"] is True
    assert state["status"] == "submitted"


@pytest.mark.asyncio
async def test_weak_answer_triggers_one_followup_then_advances(client, fake_provider):
    candidate_id = await _setup_candidate_with_two_unverified_must_haves(client, fake_provider)
    token = (await client.post(f"/api/v1/candidates/{candidate_id}/interviews")).json()["token"]

    fake_provider.responses.append(_question("Tell me about a TensorFlow retracing bug you hit.", ["retracing"]))
    state = (await client.get(f"/api/v1/interview/{token}")).json()
    q1_id = state["current_question"]["id"]

    # A weak answer should trigger exactly one follow-up probe on the same claim, not an
    # advance to claim 2.
    fake_provider.responses.append(_evaluation("weak", "generic textbook answer"))
    fake_provider.responses.append(_question("Specifically, what triggered the retrace in your training loop?", ["retracing"]))
    state = (await client.post(f"/api/v1/interview/{token}/questions/{q1_id}/answer", json={"answer_text": "TensorFlow is a machine learning framework."})).json()

    assert state["is_complete"] is False
    followup_id = state["current_question"]["id"]
    assert followup_id != q1_id
    assert "retrace" in state["current_question"]["question_text"].lower()


@pytest.mark.asyncio
async def test_interview_creation_fails_when_resume_still_processing(client, fake_provider):
    fake_provider.responses.append(
        ExtractedRequirements(requirements=[ExtractedRequirement(skill="TensorFlow", normalized_skill="TensorFlow", category="technical", importance="must_have", min_years=None, evidence_criteria="x", quoted_source_text="3+ years of TensorFlow")])
    )
    job_resp = await client.post("/api/v1/jobs", json={"title": "ML Engineer", "jd_raw": JD_TEXT})
    job_id = job_resp.json()["id"]
    candidate_resp = await client.post(f"/api/v1/jobs/{job_id}/candidates", json={"name": "Jane Doe"})
    candidate_id = candidate_resp.json()["id"]

    resp = await client.post(f"/api/v1/candidates/{candidate_id}/interviews")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_public_interview_route_requires_no_auth(client, fake_provider):
    candidate_id = await _setup_candidate_with_two_unverified_must_haves(client, fake_provider)
    token = (await client.post(f"/api/v1/candidates/{candidate_id}/interviews")).json()["token"]

    from app.auth.dependencies import get_current_user
    from app.main import app

    app.dependency_overrides.pop(get_current_user, None)  # simulate a fully unauthenticated candidate
    fake_provider.responses.append(_question("Tell me about a TensorFlow retracing bug you hit.", ["retracing"]))
    resp = await client.get(f"/api/v1/interview/{token}")
    assert resp.status_code != 401


@pytest.mark.asyncio
async def test_unknown_token_returns_404(client):
    resp = await client.get("/api/v1/interview/not-a-real-token")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_recruiter_transcript_reflects_qa_exchange(client, fake_provider):
    candidate_id = await _setup_candidate_with_two_unverified_must_haves(client, fake_provider)
    interview_resp = await client.post(f"/api/v1/candidates/{candidate_id}/interviews")
    interview_id = interview_resp.json()["id"]
    token = interview_resp.json()["token"]

    fake_provider.responses.append(_question("Tell me about a TensorFlow retracing bug you hit.", ["retracing"]))
    state = (await client.get(f"/api/v1/interview/{token}")).json()
    q1_id = state["current_question"]["id"]

    fake_provider.responses.append(_evaluation("strong", "named the retracing bug precisely"))
    fake_provider.responses.append(_question("Walk me through a k8s rollout you owned.", ["rollout"]))
    await client.post(f"/api/v1/interview/{token}/questions/{q1_id}/answer", json={"answer_text": "We hit input-shape retracing on every batch..."})

    transcript_resp = await client.get(f"/api/v1/candidates/{candidate_id}/interviews/{interview_id}/transcript")
    assert transcript_resp.status_code == 200
    body = transcript_resp.json()
    assert len(body["questions"]) == 2  # base Q1 + generated base Q2
    assert len(body["answers"]) == 1
    assert body["answers"][0]["specificity_verdict"] == "strong"
