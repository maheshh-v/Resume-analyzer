"""Import every model module so SQLAlchemy's mapper registry resolves all string-based
relationship() references before metadata is used (Alembic autogenerate, create_all, tests)."""

from app.db.base import Base
from app.models.candidate import Candidate
from app.models.claim import Claim
from app.models.decision import Decision
from app.models.document import Document
from app.models.evidence import Evidence
from app.models.interview import Interview, InterviewAnswer, InterviewQuestion
from app.models.job import Job, JobRequirement
from app.models.ledger import LedgerEvent
from app.models.llm_call_log import LLMCallLog
from app.models.user import User

__all__ = [
    "Base",
    "User",
    "Job",
    "JobRequirement",
    "Candidate",
    "Document",
    "Claim",
    "Evidence",
    "Interview",
    "InterviewQuestion",
    "InterviewAnswer",
    "Decision",
    "LedgerEvent",
    "LLMCallLog",
]
