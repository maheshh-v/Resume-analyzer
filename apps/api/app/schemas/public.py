"""Request/response shapes for the white-label public API."""

from pydantic import BaseModel, Field


class VerifyRequest(BaseModel):
    resume: str = Field(description="Base64-encoded PDF, or plain resume text.")
    jd: str = Field(description="Job description text.")
    webhook_url: str | None = Field(default=None, description="Optional URL POSTed when the report is ready.")


class VerifyAccepted(BaseModel):
    report_id: str
    status: str
    status_url: str


class PublicReportOut(BaseModel):
    report_id: str
    status: str  # pending | processing | ready | failed
    report: dict | None = None
    pdf_storage_path: str | None = None
    pdf_url: str | None = None  # signed URL when Supabase Storage is configured
    error: str | None = None
    created_at: str | None = None
    completed_at: str | None = None
