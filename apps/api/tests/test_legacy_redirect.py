"""The temporary legacy-path -> /api/v1 redirect layer.

Old unprefixed recruiter routes 308-redirect to their /api/v1 equivalents (308 preserves method
and body, so a redirected POST stays a POST). /health and other infra paths are never redirected.
The `client` fixture doesn't follow redirects, so we see the 308 directly.
"""


async def test_legacy_get_redirects_308(client):
    resp = await client.get("/jobs")
    assert resp.status_code == 308
    assert resp.headers["location"].endswith("/api/v1/jobs")


async def test_legacy_nested_path_preserves_query(client):
    resp = await client.get("/candidates/abc-123?foo=bar")
    assert resp.status_code == 308
    assert resp.headers["location"].endswith("/api/v1/candidates/abc-123?foo=bar")


async def test_legacy_interview_path_redirects(client):
    resp = await client.get("/interview/some-token")
    assert resp.status_code == 308
    assert resp.headers["location"].endswith("/api/v1/interview/some-token")


async def test_legacy_post_is_308_not_302(client):
    # A 302 would silently downgrade POST to GET; 308 keeps the method + body.
    resp = await client.post("/jobs", json={"title": "x", "jd_raw": "y"})
    assert resp.status_code == 308
    assert resp.headers["location"].endswith("/api/v1/jobs")


async def test_health_is_not_redirected(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_v1_path_is_not_redirected(client):
    # Already-migrated paths pass straight through (no double-prefix, no redirect loop).
    resp = await client.get("/api/v1/jobs")
    assert resp.status_code == 200  # empty list for the authed test user
