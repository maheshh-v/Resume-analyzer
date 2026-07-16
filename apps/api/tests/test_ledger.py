"""The Evidence Ledger's whole value is that tampering is detectable — so these tests tamper.

Unit tests exercise append/verify directly; the API tests drive the real pipeline + interview
flow and assert the chain both records everything and catches post-hoc edits.
"""


import pytest
from sqlalchemy import select

from app.ledger import append_event, sha256_text, verify_chain
from app.models.candidate import Candidate
from app.models.interview import InterviewAnswer
from app.models.ledger import GENESIS_HASH, LedgerEvent
from app.models.user import User
from tests.test_api_interview_flow import (
    _evaluation,
    _question,
    _setup_candidate_with_two_unverified_must_haves,
)


async def _make_candidate(db_session) -> Candidate:
    user = User(auth_id="ledger-auth", email="ledger@example.com")
    db_session.add(user)
    await db_session.flush()
    from app.models.job import Job

    job = Job(owner_user_id=user.id, title="X", jd_raw="jd")
    db_session.add(job)
    await db_session.flush()
    candidate = Candidate(owner_user_id=user.id, job_id=job.id, name="C", status="pending")
    db_session.add(candidate)
    await db_session.flush()
    return candidate


@pytest.mark.asyncio
async def test_chain_links_from_genesis_and_verifies(db_session):
    candidate = await _make_candidate(db_session)
    e0 = await append_event(db_session, candidate_id=candidate.id, event_type="a", actor_type="system")
    e1 = await append_event(db_session, candidate_id=candidate.id, event_type="b", actor_type="system", payload={"k": 1})
    await db_session.commit()

    assert e0.seq == 0 and e0.prev_hash == GENESIS_HASH
    assert e1.seq == 1 and e1.prev_hash == e0.event_hash

    verification = await verify_chain(db_session, candidate.id)
    assert verification.ok is True
    assert verification.event_count == 2


@pytest.mark.asyncio
async def test_tampered_payload_breaks_chain_at_that_seq(db_session):
    candidate = await _make_candidate(db_session)
    await append_event(db_session, candidate_id=candidate.id, event_type="a", actor_type="system", payload={"n": 1})
    await append_event(db_session, candidate_id=candidate.id, event_type="b", actor_type="system", payload={"n": 2})
    await db_session.commit()

    result = await db_session.execute(select(LedgerEvent).where(LedgerEvent.seq == 0))
    event = result.scalar_one()
    event.payload = {"n": 999}  # the cover-up
    await db_session.commit()

    verification = await verify_chain(db_session, candidate.id)
    assert verification.ok is False
    assert verification.first_broken_seq == 0


@pytest.mark.asyncio
async def test_deleted_event_breaks_chain(db_session):
    candidate = await _make_candidate(db_session)
    await append_event(db_session, candidate_id=candidate.id, event_type="a", actor_type="system")
    e1 = await append_event(db_session, candidate_id=candidate.id, event_type="b", actor_type="system")
    await append_event(db_session, candidate_id=candidate.id, event_type="c", actor_type="system")
    await db_session.commit()

    await db_session.delete(e1)
    await db_session.commit()

    verification = await verify_chain(db_session, candidate.id)
    assert verification.ok is False
    assert verification.first_broken_seq == 2  # the gap is exposed where seq 2 sits at position 1


@pytest.mark.asyncio
async def test_empty_chain_verifies_ok(db_session):
    candidate = await _make_candidate(db_session)
    verification = await verify_chain(db_session, candidate.id)
    assert verification.ok is True
    assert verification.event_count == 0


@pytest.mark.asyncio
async def test_pipeline_and_interview_emit_full_trail(client, fake_provider):
    candidate_id = await _setup_candidate_with_two_unverified_must_haves(client, fake_provider)
    token = (await client.post(f"/candidates/{candidate_id}/interviews")).json()["token"]

    fake_provider.responses.append(_question("Tell me about a TensorFlow retracing bug you hit.", ["retracing"]))
    state = (await client.get(f"/interview/{token}")).json()
    q1_id = state["current_question"]["id"]

    fake_provider.responses.append(_evaluation("strong", "precise"))
    fake_provider.responses.append(_question("Walk me through a k8s rollout you owned.", ["rollout"]))
    await client.post(f"/interview/{token}/questions/{q1_id}/answer", json={"answer_text": "We hit input-shape retracing..."})

    await client.post(f"/candidates/{candidate_id}/decision", json={"verdict": "advance", "rationale": "Strong on TF."})

    ledger = (await client.get(f"/candidates/{candidate_id}/ledger")).json()
    event_types = [e["event_type"] for e in ledger["events"]]
    assert event_types[0] == "candidate_created"
    for expected in ("resume_ingested", "claims_extracted", "consistency_checked", "interview_created", "question_asked", "answer_recorded", "decision_recorded"):
        assert expected in event_types, f"missing {expected} in {event_types}"
    # seq is dense and ordered
    assert [e["seq"] for e in ledger["events"]] == list(range(len(ledger["events"])))

    verification = (await client.get(f"/candidates/{candidate_id}/ledger/verify")).json()
    assert verification["ok"] is True
    assert verification["event_count"] == len(ledger["events"])
    assert verification["content_mismatches"] == []


@pytest.mark.asyncio
async def test_edited_answer_is_caught_by_content_attestation(client, fake_provider, db_session):
    candidate_id = await _setup_candidate_with_two_unverified_must_haves(client, fake_provider)
    token = (await client.post(f"/candidates/{candidate_id}/interviews")).json()["token"]

    fake_provider.responses.append(_question("Tell me about a TensorFlow retracing bug you hit.", ["retracing"]))
    state = (await client.get(f"/interview/{token}")).json()
    q1_id = state["current_question"]["id"]

    fake_provider.responses.append(_evaluation("weak", "generic"))
    fake_provider.responses.append(_question("Specifically what triggered it?", ["retracing"]))
    await client.post(f"/interview/{token}/questions/{q1_id}/answer", json={"answer_text": "TensorFlow is a framework."})

    # Someone quietly "improves" the recorded answer after the fact.
    result = await db_session.execute(select(InterviewAnswer))
    answer = result.scalars().first()
    original_hash = sha256_text(answer.answer_text)
    answer.answer_text = "I diagnosed a subtle retracing bug in our tf.function training loop."
    await db_session.commit()
    assert sha256_text(answer.answer_text) != original_hash

    verification = (await client.get(f"/candidates/{candidate_id}/ledger/verify")).json()
    assert verification["ok"] is False
    assert verification["first_broken_seq"] is None  # chain itself intact — the *content* was altered
    assert any(m["event_type"] == "answer_recorded" for m in verification["content_mismatches"])


@pytest.mark.asyncio
async def test_ledger_requires_ownership(client, fake_provider, db_session):
    candidate_id = await _setup_candidate_with_two_unverified_must_haves(client, fake_provider)

    # Rebind auth to a different user — the ledger must 404, not leak.
    from app.auth.dependencies import get_current_user
    from app.main import app

    intruder = User(auth_id="intruder-auth", email="intruder@example.com")
    db_session.add(intruder)
    await db_session.commit()
    await db_session.refresh(intruder)

    async def _override():
        return intruder

    app.dependency_overrides[get_current_user] = _override
    resp = await client.get(f"/candidates/{candidate_id}/ledger")
    assert resp.status_code == 404
