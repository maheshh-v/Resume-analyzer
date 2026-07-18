"""Bulk intake: multi-PDF upload, CSV/XLSX sheet import, and the public apply link.

Everything runs against SQLite + FakeProvider; resume-URL fetching is exercised through
httpx.MockTransport or injected fakes — no live network anywhere.
"""

import io

import fitz
import httpx
import pytest

from app.intake.fetch import ResumeFetchError, fetch_resume_pdf
from app.intake.ingest import ResumeFetchItem, ingest_sheet_resumes
from app.intake.naming import candidate_name_from_filename
from app.intake.sheet import parse_candidate_sheet
from app.llm.prompts.claim_extraction import ExtractedClaim, ExtractedClaims
from app.llm.prompts.jd_extraction import ExtractedRequirement, ExtractedRequirements
from app.public_api.rate_limit import reset_rate_limits

JD_TEXT = "Senior ML Engineer.\nRequirements:\n- 3+ years of TensorFlow"
RESUME_TEXT = "4 years TensorFlow at Acme Inc."


def _make_pdf_bytes(text: str = RESUME_TEXT) -> bytes:
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


def _claims_response():
    return ExtractedClaims(
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


async def _create_job(client, fake_provider) -> str:
    fake_provider.responses.append(_jd_response())
    resp = await client.post("/api/v1/jobs", json={"title": "ML Engineer", "jd_raw": JD_TEXT})
    return resp.json()["id"]


# --- filename -> name -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("Jane_Doe_Resume_2024.pdf", "Jane Doe"),
        ("john-smith-cv.pdf", "John Smith"),
        ("PRIYA SHARMA final v2.pdf", "Priya Sharma"),
        ("McDonald_Angus_CV.pdf", "McDonald Angus"),
        ("resume.pdf", "Unnamed candidate"),
        ("cv_final_updated (1).pdf", "Unnamed candidate"),
    ],
)
def test_candidate_name_from_filename(filename, expected):
    assert candidate_name_from_filename(filename) == expected


# --- sheet parsing ----------------------------------------------------------------------


def test_parse_csv_with_forgiving_headers_and_bad_rows():
    csv_bytes = (
        "Name,Email,GitHub username,LinkedIn,Resume URL\n"
        "Jane Doe,jane@example.com,janedoe,https://linkedin.com/in/janedoe,https://cdn.example.com/jane.pdf\n"
        ",missing@name.com,,,\n"
        "Bad Email,not-an-email,,,\n"
        "Bad Url,ok@example.com,,,ftp://files/jane.pdf\n"
        "Rahul Verma,rahul@example.com,,,\n"
    ).encode()
    result = parse_candidate_sheet(csv_bytes, "candidates.csv")

    assert [r.name for r in result.rows] == ["Jane Doe", "Rahul Verma"]
    jane = result.rows[0]
    assert jane.email == "jane@example.com"
    assert jane.github_login == "janedoe"
    assert jane.resume_url == "https://cdn.example.com/jane.pdf"
    assert jane.row_number == 2  # spreadsheet numbering: header is row 1
    assert len(result.errors) == 3
    assert "Row 3" in result.errors[0]
    assert "Row 4" in result.errors[1]
    assert "Row 5" in result.errors[2]


def test_parse_xlsx():
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(["name", "email"])
    ws.append(["Jane Doe", "jane@example.com"])
    buffer = io.BytesIO()
    wb.save(buffer)

    result = parse_candidate_sheet(buffer.getvalue(), "candidates.xlsx")
    assert len(result.rows) == 1
    assert result.rows[0].name == "Jane Doe"
    assert result.errors == []


def test_parse_sheet_without_name_column_is_an_error():
    result = parse_candidate_sheet(b"email\njane@example.com\n", "x.csv")
    assert result.rows == []
    assert any("name" in e for e in result.errors)


# --- resume URL fetching ----------------------------------------------------------------


def _pdf_transport(body: bytes = b"%PDF-1.4 fake", status_code: int = 200):
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, content=body)

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_fetch_resume_pdf_happy_path():
    async with httpx.AsyncClient(transport=_pdf_transport()) as client:
        content = await fetch_resume_pdf("https://cdn.example.com/resume.pdf", client=client)
    assert content.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_fetch_rejects_private_hosts_and_bad_schemes():
    with pytest.raises(ResumeFetchError):
        await fetch_resume_pdf("http://127.0.0.1/resume.pdf")
    with pytest.raises(ResumeFetchError):
        await fetch_resume_pdf("http://localhost/resume.pdf")
    with pytest.raises(ResumeFetchError):
        await fetch_resume_pdf("ftp://cdn.example.com/resume.pdf")


@pytest.mark.asyncio
async def test_fetch_rejects_redirect_to_private_host():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "http://127.0.0.1/internal.pdf"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ResumeFetchError):
            await fetch_resume_pdf("https://cdn.example.com/resume.pdf", client=client)


@pytest.mark.asyncio
async def test_fetch_rejects_non_pdf_body():
    async with httpx.AsyncClient(transport=_pdf_transport(body=b"<html>login page</html>")) as client:
        with pytest.raises(ResumeFetchError):
            await fetch_resume_pdf("https://cdn.example.com/resume.pdf", client=client)


# --- bulk PDF upload --------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bulk_upload_creates_and_processes_all_files(client, fake_provider):
    job_id = await _create_job(client, fake_provider)
    fake_provider.responses.append(_claims_response())
    fake_provider.responses.append(_claims_response())

    pdf = _make_pdf_bytes()
    resp = await client.post(
        f"/api/v1/jobs/{job_id}/candidates/bulk-upload",
        files=[
            ("files", ("Jane_Doe_Resume.pdf", io.BytesIO(pdf), "application/pdf")),
            ("files", ("rahul-verma-cv.pdf", io.BytesIO(pdf), "application/pdf")),
        ],
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["errors"] == []
    assert [c["name"] for c in body["created"]] == ["Jane Doe", "Rahul Verma"]
    assert all(c["status"] == "processing" for c in body["created"])

    list_resp = await client.get(f"/api/v1/jobs/{job_id}/candidates")
    statuses = {c["name"]: c["status"] for c in list_resp.json()}
    assert statuses == {"Jane Doe": "ready", "Rahul Verma": "ready"}


@pytest.mark.asyncio
async def test_bulk_upload_bad_file_reports_error_without_blocking_batch(client, fake_provider):
    job_id = await _create_job(client, fake_provider)
    fake_provider.responses.append(_claims_response())

    resp = await client.post(
        f"/api/v1/jobs/{job_id}/candidates/bulk-upload",
        files=[
            ("files", ("Jane_Doe_Resume.pdf", io.BytesIO(_make_pdf_bytes()), "application/pdf")),
            ("files", ("notes.txt", io.BytesIO(b"not a pdf"), "text/plain")),
        ],
    )
    assert resp.status_code == 201
    body = resp.json()
    assert len(body["created"]) == 1
    assert body["created"][0]["name"] == "Jane Doe"
    assert len(body["errors"]) == 1
    assert "notes.txt" in body["errors"][0]


@pytest.mark.asyncio
async def test_bulk_upload_caps_batch_size(client, fake_provider):
    job_id = await _create_job(client, fake_provider)
    pdf = _make_pdf_bytes()
    files = [("files", (f"c{i}.pdf", io.BytesIO(pdf), "application/pdf")) for i in range(21)]
    resp = await client.post(f"/api/v1/jobs/{job_id}/candidates/bulk-upload", files=files)
    assert resp.status_code == 400


# --- sheet import endpoint --------------------------------------------------------------


@pytest.mark.asyncio
async def test_import_csv_creates_candidates_and_reports_row_errors(client, fake_provider):
    job_id = await _create_job(client, fake_provider)
    csv_bytes = (
        "name,email,github\n"
        "Jane Doe,jane@example.com,janedoe\n"
        ",missing@name.com,\n"
        "Rahul Verma,rahul@example.com,\n"
    ).encode()

    resp = await client.post(
        f"/api/v1/jobs/{job_id}/candidates/import",
        files={"file": ("candidates.csv", io.BytesIO(csv_bytes), "text/csv")},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert [c["name"] for c in body["created"]] == ["Jane Doe", "Rahul Verma"]
    assert body["created"][0]["email"] == "jane@example.com"
    assert body["created"][0]["github_login"] == "janedoe"
    # no resume URLs -> candidates await a manual upload, nothing is being fetched
    assert all(c["status"] == "pending" for c in body["created"])
    assert body["fetching_count"] == 0
    assert len(body["errors"]) == 1 and "Row 3" in body["errors"][0]


@pytest.mark.asyncio
async def test_import_with_resume_urls_schedules_fetch(client, fake_provider, monkeypatch):
    from app.routers import intake as intake_router

    scheduled: list[ResumeFetchItem] = []

    async def _fake_ingest(*, items, session_factory):
        scheduled.extend(items)

    monkeypatch.setattr(intake_router, "ingest_sheet_resumes", _fake_ingest)

    job_id = await _create_job(client, fake_provider)
    csv_bytes = (
        "name,resume_url\nJane Doe,https://cdn.example.com/jane.pdf\nRahul Verma,\n"
    ).encode()
    resp = await client.post(
        f"/api/v1/jobs/{job_id}/candidates/import",
        files={"file": ("candidates.csv", io.BytesIO(csv_bytes), "text/csv")},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["fetching_count"] == 1
    statuses = {c["name"]: c["status"] for c in body["created"]}
    assert statuses == {"Jane Doe": "processing", "Rahul Verma": "pending"}
    assert len(scheduled) == 1
    assert scheduled[0].resume_url == "https://cdn.example.com/jane.pdf"


@pytest.mark.asyncio
async def test_ingest_runs_pipeline_on_fetched_resume_and_marks_dead_urls_failed(client, fake_provider, monkeypatch):
    from app.db.session import SessionLocal
    from app.routers import intake as intake_router

    # Neutralize the endpoint's scheduled ingest (it would hit the network); the real
    # ingest_sheet_resumes runs below with an injected fetcher instead.
    async def _noop_ingest(*, items, session_factory):
        return None

    monkeypatch.setattr(intake_router, "ingest_sheet_resumes", _noop_ingest)

    job_id = await _create_job(client, fake_provider)
    csv_bytes = (
        "name,resume_url\n"
        "Jane Doe,https://cdn.example.com/jane.pdf\n"
        "Dead Link,https://cdn.example.com/gone.pdf\n"
    ).encode()
    resp = await client.post(
        f"/api/v1/jobs/{job_id}/candidates/import",
        files={"file": ("candidates.csv", io.BytesIO(csv_bytes), "text/csv")},
    )
    by_name = {c["name"]: c["id"] for c in resp.json()["created"]}
    fake_provider.responses.append(_claims_response())

    async def _fetcher(url: str) -> bytes:
        if "gone" in url:
            raise ResumeFetchError("Resume URL returned HTTP 404")
        return _make_pdf_bytes()

    await ingest_sheet_resumes(
        items=[
            ResumeFetchItem(candidate_id=by_name["Jane Doe"], candidate_name="Jane Doe", resume_url="https://cdn.example.com/jane.pdf"),
            ResumeFetchItem(candidate_id=by_name["Dead Link"], candidate_name="Dead Link", resume_url="https://cdn.example.com/gone.pdf"),
        ],
        session_factory=SessionLocal,
        fetcher=_fetcher,
    )

    list_resp = await client.get(f"/api/v1/jobs/{job_id}/candidates")
    rows = {c["name"]: c for c in list_resp.json()}
    assert rows["Jane Doe"]["status"] == "ready"
    assert rows["Dead Link"]["status"] == "failed"
    assert "404" in rows["Dead Link"]["status_detail"]


@pytest.mark.asyncio
async def test_import_rejects_unusable_sheets(client, fake_provider):
    job_id = await _create_job(client, fake_provider)

    resp = await client.post(
        f"/api/v1/jobs/{job_id}/candidates/import",
        files={"file": ("resume.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
    )
    assert resp.status_code == 400

    resp = await client.post(
        f"/api/v1/jobs/{job_id}/candidates/import",
        files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")},
    )
    assert resp.status_code == 400


# --- public apply link ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apply_link_lifecycle(client, fake_provider):
    job_id = await _create_job(client, fake_provider)

    link_resp = await client.post(f"/api/v1/jobs/{job_id}/apply-link")
    assert link_resp.status_code == 200
    token = link_resp.json()["apply_token"]
    assert link_resp.json()["apply_url_path"] == f"/apply/{token}"

    # the job payload exposes the token so the recruiter UI can show link state
    job_resp = await client.get(f"/api/v1/jobs/{job_id}")
    assert job_resp.json()["apply_token"] == token

    public_resp = await client.get(f"/api/v1/apply/{token}")
    assert public_resp.status_code == 200
    assert public_resp.json()["job_title"] == "ML Engineer"

    # rotating invalidates the old link
    rotate_resp = await client.post(f"/api/v1/jobs/{job_id}/apply-link")
    new_token = rotate_resp.json()["apply_token"]
    assert new_token != token
    assert (await client.get(f"/api/v1/apply/{token}")).status_code == 404
    assert (await client.get(f"/api/v1/apply/{new_token}")).status_code == 200

    # disabling kills it entirely
    assert (await client.delete(f"/api/v1/jobs/{job_id}/apply-link")).status_code == 204
    assert (await client.get(f"/api/v1/apply/{new_token}")).status_code == 404


@pytest.mark.asyncio
async def test_application_runs_pipeline_and_seals_ledger(client, fake_provider):
    reset_rate_limits()
    job_id = await _create_job(client, fake_provider)
    token = (await client.post(f"/api/v1/jobs/{job_id}/apply-link")).json()["apply_token"]
    fake_provider.responses.append(_claims_response())

    resp = await client.post(
        f"/api/v1/apply/{token}",
        data={"name": "Jane Doe", "email": "jane@example.com", "github_login": "janedoe"},
        files={"file": ("resume.pdf", io.BytesIO(_make_pdf_bytes()), "application/pdf")},
    )
    assert resp.status_code == 201
    assert resp.json() == {"status": "received"}  # no candidate id leaks to the applicant

    list_resp = await client.get(f"/api/v1/jobs/{job_id}/candidates")
    [candidate] = list_resp.json()
    assert candidate["name"] == "Jane Doe"
    assert candidate["email"] == "jane@example.com"
    assert candidate["status"] == "ready"

    ledger_resp = await client.get(f"/api/v1/candidates/{candidate['id']}/ledger")
    events = ledger_resp.json()["events"]
    applied = [e for e in events if e["event_type"] == "candidate_applied"]
    assert len(applied) == 1
    assert applied[0]["actor_type"] == "candidate"
    verify_resp = await client.get(f"/api/v1/candidates/{candidate['id']}/ledger/verify")
    assert verify_resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_application_validation_and_dead_tokens(client, fake_provider):
    job_id = await _create_job(client, fake_provider)
    token = (await client.post(f"/api/v1/jobs/{job_id}/apply-link")).json()["apply_token"]

    resp = await client.post(
        "/api/v1/apply/not-a-real-token",
        data={"name": "Jane", "email": "jane@example.com"},
        files={"file": ("resume.pdf", io.BytesIO(_make_pdf_bytes()), "application/pdf")},
    )
    assert resp.status_code == 404

    resp = await client.post(
        f"/api/v1/apply/{token}",
        data={"name": "Jane", "email": "not-an-email"},
        files={"file": ("resume.pdf", io.BytesIO(_make_pdf_bytes()), "application/pdf")},
    )
    assert resp.status_code == 400

    resp = await client.post(
        f"/api/v1/apply/{token}",
        data={"name": "Jane", "email": "jane@example.com"},
        files={"file": ("resume.docx", io.BytesIO(b"word doc"), "application/msword")},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_application_rate_limit(client, fake_provider):
    from app.config import get_settings

    reset_rate_limits()
    settings = get_settings()
    original = settings.apply_rate_limit_per_min
    settings.apply_rate_limit_per_min = 1
    try:
        job_id = await _create_job(client, fake_provider)
        token = (await client.post(f"/api/v1/jobs/{job_id}/apply-link")).json()["apply_token"]
        fake_provider.responses.append(_claims_response())

        first = await client.post(
            f"/api/v1/apply/{token}",
            data={"name": "Jane", "email": "jane@example.com"},
            files={"file": ("resume.pdf", io.BytesIO(_make_pdf_bytes()), "application/pdf")},
        )
        assert first.status_code == 201

        second = await client.post(
            f"/api/v1/apply/{token}",
            data={"name": "Eve", "email": "eve@example.com"},
            files={"file": ("resume.pdf", io.BytesIO(_make_pdf_bytes()), "application/pdf")},
        )
        assert second.status_code == 429
    finally:
        settings.apply_rate_limit_per_min = original
        reset_rate_limits()
