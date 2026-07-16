from pydantic import BaseModel


class MatrixRowOut(BaseModel):
    requirement_id: str
    skill: str
    importance: str
    match_status: str
    claim_texts: list[str]
    best_verdict: str
    evidence_summaries: list[str]
    evidence_urls: list[str]


class QAExchangeOut(BaseModel):
    depth: int
    question_text: str
    rationale: str
    answer_text: str | None
    specificity_verdict: str | None
    specificity_notes: str | None
    review_flags: list[str]


class HiringSummaryOut(BaseModel):
    evidence_coverage_count: int
    evidence_coverage_total: int
    evidence_coverage_note: str = "A count of requirements with supporting evidence. Not a score, not a ranking."
    conflicts: list[str]
    matrix: list[MatrixRowOut]
    verified_skills: list[MatrixRowOut]
    needs_manual_verification: list[MatrixRowOut]
    technical_strengths: list[str]
    weak_areas: list[str]
    suggested_followups: list[str]
    transcript: list[QAExchangeOut]


class DecisionCreate(BaseModel):
    verdict: str  # advance | hold | decline
    rationale: str


class DecisionOut(BaseModel):
    id: str
    candidate_id: str
    verdict: str
    rationale: str
    decided_by_user_id: str
