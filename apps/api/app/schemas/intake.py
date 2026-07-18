from pydantic import BaseModel

from app.schemas.candidate import CandidateOut


class BulkUploadOut(BaseModel):
    created: list[CandidateOut]
    errors: list[str]  # per-file reasons; a bad file never blocks the rest of the batch


class SheetImportOut(BaseModel):
    created: list[CandidateOut]
    errors: list[str]  # per-row reasons, numbered as the user sees them in their spreadsheet
    fetching_count: int  # rows whose resume is being fetched from a URL in the background


class ApplyLinkOut(BaseModel):
    apply_token: str
    apply_url_path: str  # frontend route: /apply/{token}


class PublicJobOut(BaseModel):
    job_title: str
    jd_preview: str


class ApplicationReceivedOut(BaseModel):
    status: str = "received"
