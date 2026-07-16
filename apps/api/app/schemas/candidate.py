from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CandidateCreate(BaseModel):
    name: str
    email: str | None = None
    github_login: str | None = None
    linkedin_url: str | None = None


class CandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    name: str
    email: str | None
    github_login: str | None
    linkedin_url: str | None
    status: str
    status_detail: str | None
    created_at: datetime


class ClaimOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    claim_type: str
    claim_text: str
    normalized_skill: str | None
    asserted_years: float | None
    asserted_start: str | None
    asserted_end: str | None
    asserted_org: str | None
    source_span_start: int
    source_span_end: int


class EvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    claim_id: str
    source_type: str
    verdict: str
    summary: str
    artifact_url: str | None
    artifact_snippet: str | None


class MatchRowOut(BaseModel):
    requirement_id: str
    skill: str
    importance: str
    status: str
    matching_claim_ids: list[str]
    note: str


class CandidateDetailOut(BaseModel):
    candidate: CandidateOut
    claims: list[ClaimOut]
    evidence: list[EvidenceOut]
    matches: list[MatchRowOut]
    extraction_stats: dict
