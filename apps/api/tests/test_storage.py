"""Report-PDF storage routing + the Supabase Storage client, all mocked — no live calls.

Covers: local-vs-Supabase routing, the reports bucket + path used for upload, a 7-day signed URL,
and the raw upload/sign HTTP shape via an injected httpx MockTransport.
"""

from types import SimpleNamespace

import httpx
import pytest

from app.storage import report_storage, supabase_storage


def _supabase_settings(use_local=False):
    return SimpleNamespace(
        supabase_url="https://proj.supabase.co",
        supabase_service_role_key="svc-role-key",
        supabase_reports_bucket="recruitx-reports",
        supabase_storage_bucket="resumes",
        use_local_storage=use_local,
    )


# --- Routing (store_report_pdf) -------------------------------------------------------------


async def test_store_report_pdf_uploads_to_reports_bucket(monkeypatch):
    captured = {}

    async def _fake_upload(*, bucket, path, content, content_type):
        captured.update(bucket=bucket, path=path, content=content, content_type=content_type)
        return path

    monkeypatch.setattr(report_storage, "get_settings", lambda: _supabase_settings())
    monkeypatch.setattr(supabase_storage, "upload_object", _fake_upload)

    path = await report_storage.store_report_pdf(report_id="rid-1", content=b"%PDF-1.7 data")
    assert path == "rid-1/report.pdf"
    assert captured["bucket"] == "recruitx-reports"
    assert captured["path"] == "rid-1/report.pdf"
    assert captured["content_type"] == "application/pdf"


async def test_store_report_pdf_uses_local_when_flagged(monkeypatch, tmp_path):
    monkeypatch.setattr(report_storage, "get_settings", lambda: _supabase_settings(use_local=True))
    called = {}

    async def _fake_local(*, candidate_id, filename, content):
        called.update(candidate_id=candidate_id, filename=filename)
        return f"data/resumes/{candidate_id}/{filename}"

    monkeypatch.setattr("app.storage.local_storage.upload_resume", _fake_local)
    path = await report_storage.store_report_pdf(report_id="rid-2", content=b"%PDF")
    assert path.endswith("rid-2/report.pdf")
    assert called["candidate_id"] == "rid-2"


async def test_store_report_pdf_local_when_unconfigured(monkeypatch):
    monkeypatch.setattr(
        report_storage, "get_settings",
        lambda: SimpleNamespace(use_local_storage=False, supabase_url="", supabase_service_role_key="",
                                supabase_reports_bucket="recruitx-reports"),
    )

    async def _fake_local(*, candidate_id, filename, content):
        return f"data/resumes/{candidate_id}/{filename}"

    monkeypatch.setattr("app.storage.local_storage.upload_resume", _fake_local)
    path = await report_storage.store_report_pdf(report_id="rid-3", content=b"%PDF")
    assert path.endswith("rid-3/report.pdf")


# --- Signed URL -----------------------------------------------------------------------------


async def test_signed_report_url_none_on_local(monkeypatch):
    monkeypatch.setattr(report_storage, "get_settings", lambda: _supabase_settings(use_local=True))
    assert await report_storage.signed_report_url("rid/report.pdf") is None


async def test_signed_report_url_uses_reports_bucket_and_7_days(monkeypatch):
    captured = {}

    async def _fake_sign(storage_path, *, bucket, expires_in, client=None):
        captured.update(storage_path=storage_path, bucket=bucket, expires_in=expires_in)
        return "https://proj.supabase.co/storage/v1/object/sign/recruitx-reports/rid/report.pdf?token=x"

    monkeypatch.setattr(report_storage, "get_settings", lambda: _supabase_settings())
    monkeypatch.setattr(supabase_storage, "create_signed_url", _fake_sign)

    url = await report_storage.signed_report_url("rid/report.pdf")
    assert url and "recruitx-reports" in url
    assert captured["bucket"] == "recruitx-reports"
    assert captured["expires_in"] == report_storage.SEVEN_DAYS_SECONDS == 604800


# --- Supabase client HTTP shape (MockTransport) ---------------------------------------------


async def test_upload_object_posts_with_upsert_and_auth(monkeypatch):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        captured["auth"] = request.headers.get("authorization")
        captured["upsert"] = request.headers.get("x-upsert")
        captured["ctype"] = request.headers.get("content-type")
        return httpx.Response(200, json={"Key": "recruitx-reports/rid/report.pdf"})

    monkeypatch.setattr(supabase_storage, "get_settings", lambda: _supabase_settings())
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        path = await supabase_storage.upload_object(
            bucket="recruitx-reports", path="rid/report.pdf", content=b"%PDF",
            content_type="application/pdf", client=client,
        )
    assert path == "rid/report.pdf"
    assert captured["method"] == "POST"
    assert captured["url"].endswith("/storage/v1/object/recruitx-reports/rid/report.pdf")
    assert captured["auth"] == "Bearer svc-role-key"
    assert captured["upsert"] == "true"
    assert captured["ctype"] == "application/pdf"


async def test_create_signed_url_builds_full_url(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/storage/v1/object/sign/recruitx-reports/rid/report.pdf")
        return httpx.Response(200, json={"signedURL": "/object/sign/recruitx-reports/rid/report.pdf?token=abc"})

    monkeypatch.setattr(supabase_storage, "get_settings", lambda: _supabase_settings())
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        url = await supabase_storage.create_signed_url(
            "rid/report.pdf", bucket="recruitx-reports", expires_in=604800, client=client,
        )
    assert url == "https://proj.supabase.co/storage/v1/object/sign/recruitx-reports/rid/report.pdf?token=abc"


async def test_upload_object_raises_when_unconfigured(monkeypatch):
    monkeypatch.setattr(
        supabase_storage, "get_settings",
        lambda: SimpleNamespace(supabase_url="", supabase_service_role_key=""),
    )
    with pytest.raises(supabase_storage.StorageError):
        await supabase_storage.upload_object(bucket="b", path="p", content=b"x")
