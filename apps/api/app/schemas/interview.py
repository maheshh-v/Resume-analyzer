from datetime import datetime

from pydantic import BaseModel, ConfigDict


class InterviewCreateOut(BaseModel):
    id: str
    token: str
    status: str
    expires_at: datetime
    interview_url_path: str  # frontend builds the full URL; backend doesn't know its own domain


class InterviewQuestionPublicOut(BaseModel):
    """What the candidate sees — no rubric, no rationale, no internal ids beyond the question."""

    id: str
    ordinal: int
    question_text: str


class InterviewStateOut(BaseModel):
    status: str
    current_question: InterviewQuestionPublicOut | None
    questions_answered: int
    is_complete: bool


class AnswerSubmit(BaseModel):
    answer_text: str
    time_to_first_keystroke_ms: int | None = None
    total_time_ms: int | None = None
    paste_event_count: int = 0
    revision_count: int = 0


class InterviewQuestionRecruiterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ordinal: int
    depth: int
    targets_claim_id: str
    question_text: str
    grounding_artifact_url: str | None
    rubric: dict
    rationale: str


class InterviewAnswerRecruiterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    question_id: str
    answer_text: str
    specificity_verdict: str
    specificity_notes: str
    review_flags: list[str]


class InterviewTranscriptOut(BaseModel):
    interview_id: str
    status: str
    questions: list[InterviewQuestionRecruiterOut]
    answers: list[InterviewAnswerRecruiterOut]
