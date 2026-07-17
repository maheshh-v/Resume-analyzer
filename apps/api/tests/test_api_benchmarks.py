"""Tests for the public GET /api/v1/benchmarks/latest endpoint.

The endpoint reads whatever the eval harness wrote to evals/results/. We point it at a temp dir
so the test controls exactly what's on disk — present, absent, or malformed."""

import json

from app.routers import benchmarks as benchmarks_router

ENDPOINT = "/api/v1/benchmarks/latest"


async def test_returns_unavailable_when_no_results(client, monkeypatch, tmp_path):
    monkeypatch.setattr(benchmarks_router, "_results_dir", lambda: tmp_path)
    resp = await client.get(ENDPOINT)
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is False
    assert body["detail"]
    assert body["dataset_url"]  # the dataset link is offered even with no run yet


async def test_returns_metrics_when_present(client, monkeypatch, tmp_path):
    report = {
        "generated_at": "2026-07-18T00:00:00+00:00",
        "git_commit": "abc123",
        "provider": "recorded-fixture",
        "dataset": {
            "name": "golden_v1",
            "path": "evals/datasets/golden_v1.jsonl",
            "case_count": 15,
            "buckets": {"real": 5, "planted_lie": 5, "edge": 5},
        },
        "metrics": {
            "claim_extraction": {"f1": 0.9836, "precision": 0.9836, "recall": 0.9836},
            "citation_validity": {"span_citation_validity": 1.0, "accepted_claims_checked": 61},
            "verdict_accuracy": {"verdict_match_rate": 1.0, "fabrication_safety_rate": 1.0},
        },
    }
    (tmp_path / "latest.json").write_text(json.dumps(report), encoding="utf-8")
    (tmp_path / "latest.md").write_text("# RecruitX pipeline benchmarks\n", encoding="utf-8")
    monkeypatch.setattr(benchmarks_router, "_results_dir", lambda: tmp_path)

    resp = await client.get(ENDPOINT)
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is True
    assert body["metrics"]["claim_extraction"]["f1"] == 0.9836
    assert body["metrics"]["verdict_accuracy"]["fabrication_safety_rate"] == 1.0
    assert body["dataset"]["case_count"] == 15
    assert body["markdown"].startswith("# RecruitX")


async def test_survives_malformed_results_file(client, monkeypatch, tmp_path):
    (tmp_path / "latest.json").write_text("{ this is not valid json", encoding="utf-8")
    monkeypatch.setattr(benchmarks_router, "_results_dir", lambda: tmp_path)
    resp = await client.get(ENDPOINT)
    assert resp.status_code == 200
    assert resp.json()["available"] is False


async def test_endpoint_requires_no_auth(monkeypatch, tmp_path):
    """The page is public — the endpoint must answer without a Supabase session."""
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    monkeypatch.setattr(benchmarks_router, "_results_dir", lambda: tmp_path)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(ENDPOINT)  # no auth override installed
    assert resp.status_code == 200
