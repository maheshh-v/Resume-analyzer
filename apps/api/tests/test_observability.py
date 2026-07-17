"""Phase 2 observability: Langfuse span tagging, cost logging, and the cost endpoint.

The live model is never called — everything runs on FakeProvider, and Langfuse is replaced with
an in-memory fake so we can assert on the spans/tags without the real SDK or any network.
"""

import sys
import types

import pytest
from pydantic import BaseModel
from sqlalchemy import select

from app.config import Settings
from app.llm.client import LLMClient
from app.llm.provider import FakeProvider
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.llm_call_log import LLMCallLog
from app.observability.context import llm_call_context
from app.observability.cost_tracker import record_llm_call


class _Reply(BaseModel):
    value: str


# --- Fake Langfuse SDK ----------------------------------------------------------------------


class _FakeGeneration:
    def __init__(self):
        self.ended = False

    def end(self):
        self.ended = True


class _FakeLangfuse:
    instances: list["_FakeLangfuse"] = []

    def __init__(self, **kwargs):
        self.init_kwargs = kwargs
        self.generations: list[dict] = []
        _FakeLangfuse.instances.append(self)

    def start_generation(self, name, metadata=None, **_):
        self.generations.append({"name": name, "metadata": metadata or {}})
        return _FakeGeneration()


@pytest.fixture
def fake_langfuse(monkeypatch):
    _FakeLangfuse.instances.clear()
    module = types.ModuleType("langfuse")
    module.Langfuse = _FakeLangfuse
    monkeypatch.setitem(sys.modules, "langfuse", module)
    return _FakeLangfuse


async def _no_cost_log(**_):
    return None


# --- Langfuse span tagging ------------------------------------------------------------------


async def test_span_created_with_all_tags(fake_langfuse, monkeypatch):
    # Don't hit the DB for cost logging in this test — we only care about the span tags.
    monkeypatch.setattr("app.llm.client.record_llm_call", _no_cost_log)
    settings = Settings(langfuse_public_key="pk-test", langfuse_secret_key="sk-test")
    client = LLMClient(provider=FakeProvider(responses=[{"value": "ok"}]), settings=settings)
    assert client._tracer._enabled is True

    with llm_call_context(candidate_id="cand-1", job_id="job-1"):
        await client.generate_structured(
            system="s", user="u", schema=_Reply, prompt_version="v1", trace_name="extract_claims"
        )

    tracer_client = fake_langfuse.instances[-1]
    assert len(tracer_client.generations) == 1
    meta = tracer_client.generations[0]["metadata"]
    assert meta["candidate_id"] == "cand-1"
    assert meta["job_id"] == "job-1"
    assert meta["pipeline_stage"] == "extract_claims"
    assert meta["model"] == "fake-model"
    assert meta["provider"] == "fake"
    assert meta["retry_count"] == 0


async def test_tracer_is_noop_when_env_missing(monkeypatch):
    # If Langfuse were touched, importing the (absent) SDK would explode — prove it isn't.
    monkeypatch.setitem(sys.modules, "langfuse", None)
    monkeypatch.setattr("app.llm.client.record_llm_call", _no_cost_log)
    settings = Settings(langfuse_public_key="", langfuse_secret_key="")
    client = LLMClient(provider=FakeProvider(responses=[{"value": "ok"}]), settings=settings)
    assert client._tracer._enabled is False
    assert client._tracer._client is None

    result = await client.generate_structured(
        system="s", user="u", schema=_Reply, prompt_version="v1", trace_name="extract_jd"
    )
    assert result.data.value == "ok"


# --- Cost tracker ---------------------------------------------------------------------------


async def test_cost_tracker_writes_metadata_row(db_session):
    await record_llm_call(
        candidate_id="c1",
        job_id="j1",
        pipeline_stage="extract_claims",
        model="gemini-3.5-flash",
        provider="gemini",
        input_tokens=100,
        output_tokens=50,
        cost_usd=0.00125,
        latency_ms=1234,
        retry_count=1,
    )
    rows = (await db_session.execute(select(LLMCallLog).where(LLMCallLog.candidate_id == "c1"))).scalars().all()
    assert len(rows) == 1
    row = rows[0]
    assert row.pipeline_stage == "extract_claims"
    assert row.model == "gemini-3.5-flash"
    assert row.input_tokens == 100
    assert row.output_tokens == 50
    assert row.cost_usd == pytest.approx(0.00125)
    assert row.latency_ms == 1234
    assert row.retry_count == 1


async def test_cost_tracker_swallows_errors(monkeypatch):
    # A broken session factory must NOT raise — telemetry can never break the pipeline.
    def boom():
        raise RuntimeError("db down")

    await record_llm_call(
        candidate_id="c1", job_id=None, pipeline_stage="x", model="m", provider="p",
        input_tokens=0, output_tokens=0, cost_usd=0.0, latency_ms=0, retry_count=0,
        session_factory=boom,
    )  # no exception = pass


async def test_client_skips_cost_log_without_candidate_context(monkeypatch):
    calls = []

    async def _record(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr("app.llm.client.record_llm_call", _record)
    client = LLMClient(provider=FakeProvider(responses=[{"value": "ok"}]), settings=Settings())
    # No llm_call_context -> no candidate -> no cost row scheduled.
    await client.generate_structured(system="s", user="u", schema=_Reply, prompt_version="v1", trace_name="extract_jd")
    import asyncio

    await asyncio.gather(*client._cost_tasks)
    assert calls == []


# --- Endpoint -------------------------------------------------------------------------------


async def _make_candidate(db_session, owner_id: str) -> str:
    job = Job(owner_user_id=owner_id, title="T", jd_raw="jd", requirements_status="draft")
    db_session.add(job)
    await db_session.flush()
    candidate = Candidate(owner_user_id=owner_id, job_id=job.id, name="Cand", status="ready")
    db_session.add(candidate)
    await db_session.flush()
    db_session.add_all(
        [
            LLMCallLog(candidate_id=candidate.id, job_id=job.id, pipeline_stage="extract_claims",
                       model="gemini-3.5-flash", provider="gemini", input_tokens=200, output_tokens=80,
                       cost_usd=0.002, latency_ms=900, retry_count=0),
            LLMCallLog(candidate_id=candidate.id, job_id=job.id, pipeline_stage="interview_evaluate_answer",
                       model="gemini-3.5-flash", provider="gemini", input_tokens=50, output_tokens=20,
                       cost_usd=0.0005, latency_ms=300, retry_count=2),
            LLMCallLog(candidate_id=candidate.id, job_id=job.id, pipeline_stage="interview_evaluate_answer",
                       model="gemini-3.5-flash", provider="gemini", input_tokens=60, output_tokens=25,
                       cost_usd=0.0006, latency_ms=350, retry_count=0),
        ]
    )
    await db_session.commit()
    return candidate.id


async def test_llm_costs_endpoint_aggregates_by_stage(client, db_session, test_user):
    candidate_id = await _make_candidate(db_session, test_user.id)
    resp = await client.get(f"/api/v1/candidates/{candidate_id}/llm-costs")
    assert resp.status_code == 200
    body = resp.json()
    assert body["candidate_id"] == candidate_id
    assert body["total_calls"] == 3
    assert body["total_input_tokens"] == 310
    assert body["total_cost_usd"] == pytest.approx(0.0031)
    stages = {s["pipeline_stage"]: s for s in body["per_stage"]}
    assert stages["extract_claims"]["calls"] == 1
    interview = stages["interview_evaluate_answer"]
    assert interview["calls"] == 2
    assert interview["max_retry_count"] == 2
    assert interview["input_tokens"] == 110


async def test_llm_costs_endpoint_empty_is_zeros(client, db_session, test_user):
    candidate = Candidate(
        owner_user_id=test_user.id,
        job_id=(await _bare_job(db_session, test_user.id)),
        name="NoCalls",
        status="ready",
    )
    db_session.add(candidate)
    await db_session.commit()
    resp = await client.get(f"/api/v1/candidates/{candidate.id}/llm-costs")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_calls"] == 0
    assert body["per_stage"] == []


async def test_llm_costs_endpoint_rejects_unowned_candidate(client, db_session):
    # A candidate owned by someone else must 404, not leak cost data.
    other_candidate_id = await _make_candidate(db_session, "someone-else-user-id")
    resp = await client.get(f"/api/v1/candidates/{other_candidate_id}/llm-costs")
    assert resp.status_code == 404


async def _bare_job(db_session, owner_id: str) -> str:
    job = Job(owner_user_id=owner_id, title="T", jd_raw="jd", requirements_status="draft")
    db_session.add(job)
    await db_session.flush()
    return job.id


# --- End-to-end: the real pipeline records a cost row -----------------------------------------


async def test_resume_pipeline_records_extract_claims_cost(client, fake_provider, db_session):
    """Upload a resume through the real pipeline (mocked LLM) and confirm a candidate-scoped
    extract_claims cost row lands — proving the context wiring + drain work end to end."""
    import io

    import fitz

    from app.llm.prompts.claim_extraction import ExtractedClaim, ExtractedClaims
    from app.llm.prompts.jd_extraction import ExtractedRequirement, ExtractedRequirements

    fake_provider.responses.append(
        ExtractedRequirements(
            requirements=[
                ExtractedRequirement(
                    skill="TensorFlow", normalized_skill="TensorFlow", category="technical",
                    importance="must_have", min_years=3, evidence_criteria="repo using TF",
                    quoted_source_text="3+ years of TensorFlow",
                )
            ]
        )
    )
    job_id = (
        await client.post("/jobs", json={"title": "ML", "jd_raw": "Senior ML.\n- 3+ years of TensorFlow"})
    ).json()["id"]
    candidate_id = (await client.post(f"/jobs/{job_id}/candidates", json={"name": "Jane"})).json()["id"]

    fake_provider.responses.append(
        ExtractedClaims(
            claims=[
                ExtractedClaim(
                    claim_type="skill", claim_text="4 years TensorFlow", normalized_skill="TensorFlow",
                    asserted_years=4, quoted_source_text="4 years TensorFlow",
                )
            ]
        )
    )
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "Jane Doe\n4 years TensorFlow at Acme, 2021-01 to present.")
    pdf_bytes = doc.tobytes()
    doc.close()

    await client.post(
        f"/candidates/{candidate_id}/resume",
        files={"file": ("resume.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )

    rows = (
        await db_session.execute(select(LLMCallLog).where(LLMCallLog.candidate_id == candidate_id))
    ).scalars().all()
    stages = {r.pipeline_stage for r in rows}
    assert "extract_claims" in stages, f"expected an extract_claims cost row, got {stages}"

    # And the endpoint surfaces it.
    resp = await client.get(f"/api/v1/candidates/{candidate_id}/llm-costs")
    assert resp.status_code == 200
    assert any(s["pipeline_stage"] == "extract_claims" for s in resp.json()["per_stage"])
