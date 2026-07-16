from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LedgerEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    seq: int
    event_type: str
    actor_type: str
    actor_id: str | None
    payload: dict
    prev_hash: str
    event_hash: str
    created_at: datetime


class LedgerOut(BaseModel):
    candidate_id: str
    events: list[LedgerEventOut]


class ContentMismatchOut(BaseModel):
    seq: int
    event_type: str
    problem: str


class LedgerVerificationOut(BaseModel):
    ok: bool
    event_count: int
    first_broken_seq: int | None
    content_mismatches: list[ContentMismatchOut]
    verified_at: datetime
