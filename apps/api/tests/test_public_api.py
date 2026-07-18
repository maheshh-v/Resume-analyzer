"""Phase 4: white-label public API + Stripe metering scaffold.

The LLM is FakeProvider (via the fake_provider fixture), storage is local disk, Stripe is mocked,
and webhooks are captured — no external calls anywhere.
"""

import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.db.base import utcnow
from app.llm.prompts.claim_extraction import ExtractedClaim, ExtractedClaims
from app.llm.prompts.jd_extraction import ExtractedRequirement, ExtractedRequirements
from app.models.api_key import ApiKey
from app.models.public_report import PublicReport
from app.public_api import rate_limit
from app.public_api.keys import generate_api_key, hash_api_key


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    rate_limit.reset_rate_limits()
    yield
    rate_limit.reset_rate_limits()


async def _make_key(db_session, *, quota=0, revoked=False, stripe_customer_id=None, org="Acme Staffing"):
    raw, key_hash, prefix = generate_api_key()
    key = ApiKey(
        org_name=org, key_hash=key_hash, key_prefix=prefix, monthly_quota=quota,
        stripe_customer_id=stripe_customer_id, revoked_at=utcnow() if revoked else None,
    )
    db_session.add(key)
    await db_session.commit()
    await db_session.refresh(key)
    return raw, key


def _queue_verification_responses(fake_provider):
    """One JD-extraction response then one claim-extraction response, matching verify_job order."""
    fake_provider.responses.append(
        ExtractedRequirements(
            requirements=[
                ExtractedRequirement(
                    skill="Python", normalized_skill="Python", category="technical",
                    importance="must_have", min_years=3, evidence_criteria="uses python",
                    quoted_source_text="Python",
                )
            ]
        )
    )
    fake_provider.responses.append(
        ExtractedClaims(
            claims=[
                ExtractedClaim(
                    claim_type="skill", claim_text="Python", normalized_skill="Python",
                    asserted_years=5, quoted_source_text="Python",
                )
            ]
        )
    )


# --- Keys + auth ----------------------------------------------------------------------------


def test_generate_api_key_is_hashed_and_prefixed():
    raw, key_hash, prefix = generate_api_key()
    assert raw.startswith("rx_live_")
    assert key_hash == hash_api_key(raw)
    assert raw.startswith(prefix)
    assert len(key_hash) == 64


async def test_verify_rejects_missing_key(client):
    resp = await client.post("/api/v1/public/verify", json={"resume": "x", "jd": "y"})
    assert resp.status_code == 401


async def test_verify_rejects_invalid_key(client):
    resp = await client.post("/api/v1/public/verify", json={"resume": "x", "jd": "y"}, headers={"X-API-Key": "rx_live_nope"})
    assert resp.status_code == 401


async def test_verify_rejects_revoked_key(client, db_session):
    raw, _ = await _make_key(db_session, revoked=True)
    resp = await client.post("/api/v1/public/verify", json={"resume": "x", "jd": "y"}, headers={"X-API-Key": raw})
    assert resp.status_code == 403


# --- Verify -> poll -> download -------------------------------------------------------------


async def test_verify_flow_produces_report_and_pdf(client, db_session, fake_provider):
    raw, key = await _make_key(db_session)
    _queue_verification_responses(fake_provider)

    resp = await client.post(
        "/api/v1/public/verify",
        json={"resume": "Jane Doe. 5 years of Python.", "jd": "Backend role. Must have: Python."},
        headers={"X-API-Key": raw},
    )
    assert resp.status_code == 202
    report_id = resp.json()["report_id"]
    assert resp.json()["status_url"].endswith(report_id)

    poll = await client.get(f"/api/v1/public/reports/{report_id}", headers={"X-API-Key": raw})
    assert poll.status_code == 200
    body = poll.json()
    assert body["status"] == "ready", body
    assert body["report"] is not None
    assert body["report"]["matrix"][0]["skill"] == "Python"
    assert body["pdf_storage_path"]

    # The branded PDF is a real PDF on disk.
    pdf_path = Path(body["pdf_storage_path"])
    assert pdf_path.exists()
    assert pdf_path.read_bytes()[:5] == b"%PDF-"

    # Quota consumed.
    await db_session.refresh(key)
    assert key.usage_count == 1


async def test_report_is_scoped_to_creating_key(client, db_session, fake_provider):
    raw_a, _ = await _make_key(db_session, org="A")
    raw_b, _ = await _make_key(db_session, org="B")
    _queue_verification_responses(fake_provider)
    report_id = (
        await client.post(
            "/api/v1/public/verify",
            json={"resume": "Python dev", "jd": "Python"},
            headers={"X-API-Key": raw_a},
        )
    ).json()["report_id"]

    # Key B must not see key A's report.
    resp = await client.get(f"/api/v1/public/reports/{report_id}", headers={"X-API-Key": raw_b})
    assert resp.status_code == 404


# --- Quota + rate limiting ------------------------------------------------------------------


async def test_quota_enforced(client, db_session, fake_provider):
    raw, _ = await _make_key(db_session, quota=1)
    _queue_verification_responses(fake_provider)
    first = await client.post("/api/v1/public/verify", json={"resume": "Python", "jd": "Python"}, headers={"X-API-Key": raw})
    assert first.status_code == 202
    second = await client.post("/api/v1/public/verify", json={"resume": "Python", "jd": "Python"}, headers={"X-API-Key": raw})
    assert second.status_code == 429


async def test_rate_limiter_unit_blocks_after_limit(monkeypatch):
    rate_limit.reset_rate_limits()
    monkeypatch.setattr(rate_limit, "get_settings", lambda: SimpleNamespace(public_api_rate_limit_per_min=3))
    key = ApiKey(org_name="A", key_hash="h", key_prefix="p", monthly_quota=0)
    key.id = "rate-key-1"
    for _ in range(3):
        assert await rate_limit.rate_limited_api_key(key) is key
    with pytest.raises(HTTPException) as exc:
        await rate_limit.rate_limited_api_key(key)
    assert exc.value.status_code == 429


async def test_rate_limit_enforced_on_endpoint(client, db_session, fake_provider, monkeypatch):
    monkeypatch.setattr(rate_limit, "get_settings", lambda: SimpleNamespace(public_api_rate_limit_per_min=1))
    raw, _ = await _make_key(db_session)
    _queue_verification_responses(fake_provider)  # only the first call runs verification
    first = await client.post("/api/v1/public/verify", json={"resume": "Python", "jd": "Python"}, headers={"X-API-Key": raw})
    assert first.status_code == 202
    second = await client.post("/api/v1/public/verify", json={"resume": "Python", "jd": "Python"}, headers={"X-API-Key": raw})
    assert second.status_code == 429


# --- Stripe metering (scaffold, mocked) -----------------------------------------------------


async def test_verify_emits_one_metered_event(client, db_session, fake_provider, monkeypatch):
    calls = []

    async def _record(key, quantity=1):
        calls.append(key.id)
        return True

    monkeypatch.setattr("app.routers.public.record_verification_usage", _record)
    raw, _ = await _make_key(db_session)
    _queue_verification_responses(fake_provider)
    await client.post("/api/v1/public/verify", json={"resume": "Python", "jd": "Python"}, headers={"X-API-Key": raw})
    assert len(calls) == 1


async def test_meter_noop_without_stripe_config(db_session):
    from app.billing.meter import record_verification_usage

    _, key = await _make_key(db_session)  # no stripe_customer_id
    assert await record_verification_usage(key) is False


async def test_meter_emits_event_when_configured(db_session, monkeypatch):
    from app.billing import meter

    events = []
    fake_stripe = types.ModuleType("stripe")
    fake_stripe.billing = types.SimpleNamespace(
        MeterEvent=types.SimpleNamespace(create=lambda **kw: events.append(kw))
    )
    monkeypatch.setitem(sys.modules, "stripe", fake_stripe)
    monkeypatch.setattr(meter, "get_settings", lambda: SimpleNamespace(stripe_api_key="sk_test", stripe_meter_event_name="recruitx_verification"))

    _, key = await _make_key(db_session, stripe_customer_id="cus_123")
    assert await meter.record_verification_usage(key) is True
    assert len(events) == 1
    assert events[0]["payload"]["stripe_customer_id"] == "cus_123"


# --- Webhook (direct, captured) -------------------------------------------------------------


async def test_verify_job_fires_webhook_on_completion(db_session, fake_provider):
    from app.public_api.verify_job import run_public_verification

    report = PublicReport(api_key_id=(await _make_key(db_session))[1].id, status="pending", webhook_url="https://hook.test/x")
    db_session.add(report)
    await db_session.commit()
    _queue_verification_responses(fake_provider)

    captured = []

    async def _poster(url, payload):
        captured.append((url, payload))

    await run_public_verification(
        report_id=report.id, resume_text="Python dev", jd_text="Python",
        org_name="Acme", webhook_url="https://hook.test/x", webhook_poster=_poster,
    )
    assert len(captured) == 1
    assert captured[0][0] == "https://hook.test/x"
    assert captured[0][1]["report_id"] == report.id
    assert captured[0][1]["status"] == "ready"


# --- Admin CLI ------------------------------------------------------------------------------


async def test_cli_create_api_key(db_session):
    from app.cli import _create_api_key

    key_id, raw = await _create_api_key(org="CLI Corp", quota=250)
    assert raw.startswith("rx_live_")
    row = (await db_session.execute(select(ApiKey).where(ApiKey.id == key_id))).scalar_one()
    assert row.org_name == "CLI Corp"
    assert row.monthly_quota == 250
    assert row.key_hash == hash_api_key(raw)  # only the hash is stored
