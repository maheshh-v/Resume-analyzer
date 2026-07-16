"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-16

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("auth_id", sa.String(36), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_auth_id", "users", ["auth_id"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("jd_raw", sa.Text(), nullable=False),
        sa.Column("requirements_status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_jobs_owner_user_id", "jobs", ["owner_user_id"])

    op.create_table(
        "job_requirements",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skill", sa.String(255), nullable=False),
        sa.Column("normalized_skill", sa.String(255), nullable=False),
        sa.Column("category", sa.String(50), nullable=False, server_default="technical"),
        sa.Column("importance", sa.String(20), nullable=False, server_default="nice_to_have"),
        sa.Column("min_years", sa.Float(), nullable=True),
        sa.Column("evidence_criteria", sa.Text(), nullable=False),
        sa.Column("source_span_start", sa.Integer(), nullable=True),
        sa.Column("source_span_end", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_job_requirements_job_id", "job_requirements", ["job_id"])
    op.create_index("ix_job_requirements_normalized_skill", "job_requirements", ["normalized_skill"])

    op.create_table(
        "candidates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("github_login", sa.String(255), nullable=True),
        sa.Column("linkedin_url", sa.String(512), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("status_detail", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_candidates_owner_user_id", "candidates", ["owner_user_id"])
    op.create_index("ix_candidates_job_id", "candidates", ["job_id"])

    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("candidate_id", sa.String(36), sa.ForeignKey("candidates.id"), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False, server_default="resume"),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("storage_path", sa.String(1024), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column("page_offsets", sa.JSON(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_documents_candidate_id", "documents", ["candidate_id"])
    op.create_index("ix_documents_content_hash", "documents", ["content_hash"])

    op.create_table(
        "claims",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("candidate_id", sa.String(36), sa.ForeignKey("candidates.id"), nullable=False),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("claim_type", sa.String(20), nullable=False),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("normalized_skill", sa.String(255), nullable=True),
        sa.Column("asserted_years", sa.Float(), nullable=True),
        sa.Column("asserted_start", sa.String(20), nullable=True),
        sa.Column("asserted_end", sa.String(20), nullable=True),
        sa.Column("asserted_org", sa.String(255), nullable=True),
        sa.Column("source_span_start", sa.Integer(), nullable=False),
        sa.Column("source_span_end", sa.Integer(), nullable=False),
        sa.Column("extractor_model", sa.String(100), nullable=False),
        sa.Column("prompt_version", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_claims_candidate_id", "claims", ["candidate_id"])
    op.create_index("ix_claims_document_id", "claims", ["document_id"])
    op.create_index("ix_claims_normalized_skill", "claims", ["normalized_skill"])

    op.create_table(
        "evidence",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("claim_id", sa.String(36), sa.ForeignKey("claims.id"), nullable=False),
        sa.Column("source_type", sa.String(20), nullable=False),
        sa.Column("verdict", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("artifact_url", sa.String(1024), nullable=True),
        sa.Column("artifact_snippet", sa.Text(), nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("prompt_version", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_evidence_claim_id", "evidence", ["claim_id"])

    op.create_table(
        "interviews",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("candidate_id", sa.String(36), sa.ForeignKey("candidates.id"), nullable=False),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("token", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("invited_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("target_claims", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_interviews_candidate_id", "interviews", ["candidate_id"])
    op.create_index("ix_interviews_job_id", "interviews", ["job_id"])
    op.create_index("ix_interviews_token", "interviews", ["token"], unique=True)

    op.create_table(
        "interview_questions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("interview_id", sa.String(36), sa.ForeignKey("interviews.id"), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("parent_question_id", sa.String(36), sa.ForeignKey("interview_questions.id"), nullable=True),
        sa.Column("targets_claim_id", sa.String(36), sa.ForeignKey("claims.id"), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("grounding_artifact_url", sa.String(1024), nullable=True),
        sa.Column("rubric", sa.JSON(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_interview_questions_interview_id", "interview_questions", ["interview_id"])

    op.create_table(
        "interview_answers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("question_id", sa.String(36), sa.ForeignKey("interview_questions.id"), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("specificity_verdict", sa.String(20), nullable=False),
        sa.Column("specificity_notes", sa.Text(), nullable=False),
        sa.Column("time_to_first_keystroke_ms", sa.Integer(), nullable=True),
        sa.Column("total_time_ms", sa.Integer(), nullable=True),
        sa.Column("paste_event_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("revision_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("review_flags", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_interview_answers_question_id", "interview_answers", ["question_id"], unique=True)

    op.create_table(
        "decisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("candidate_id", sa.String(36), sa.ForeignKey("candidates.id"), nullable=False),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("decided_by_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("verdict", sa.String(20), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_decisions_candidate_id", "decisions", ["candidate_id"])
    op.create_index("ix_decisions_job_id", "decisions", ["job_id"])


def downgrade() -> None:
    op.drop_table("decisions")
    op.drop_table("interview_answers")
    op.drop_table("interview_questions")
    op.drop_table("interviews")
    op.drop_table("evidence")
    op.drop_table("claims")
    op.drop_table("documents")
    op.drop_table("candidates")
    op.drop_table("job_requirements")
    op.drop_table("jobs")
    op.drop_table("users")
