from datetime import datetime

from pydantic import BaseModel, ConfigDict


class JobCreate(BaseModel):
    title: str
    jd_raw: str


class JobRequirementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ordinal: int
    skill: str
    normalized_skill: str
    category: str
    importance: str
    min_years: float | None
    evidence_criteria: str
    source_span_start: int | None
    source_span_end: int | None


class JobRequirementUpdate(BaseModel):
    skill: str
    normalized_skill: str
    category: str
    importance: str
    min_years: float | None = None
    evidence_criteria: str


class JobRequirementsReplace(BaseModel):
    requirements: list[JobRequirementUpdate]


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    jd_raw: str
    requirements_status: str
    apply_token: str | None = None
    created_at: datetime
    requirements: list[JobRequirementOut] = []


class JobSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    requirements_status: str
    created_at: datetime
    candidate_count: int = 0
