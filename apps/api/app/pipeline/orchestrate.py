"""Wires the independently-testable pipeline stages into the resume-upload flow.

Runs as a FastAPI background task (see routers/candidates.py) so the upload request returns
immediately; the candidate's `status` column is what the frontend polls. Every collaborator
(LLM client, storage uploader, GitHub fetcher, session factory) is injectable so tests can
run this whole orchestration against SQLite + FakeProvider with zero network calls.
"""

import hashlib
import io
import logging

import httpx
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import get_settings
from app.llm.client import LLMClient, get_llm_client
from app.models.candidate import Candidate
from app.models.claim import Claim
from app.models.document import Document
from app.models.evidence import Evidence
from app.pipeline.evidence.consistency import ConsistencyClaim, run_consistency_checks
from app.pipeline.evidence.github import gather_github_evidence
from app.pipeline.extract_claims import extract_claims
from app.pipeline.text_extraction import extract_text_from_pdf

logger = logging.getLogger(__name__)


async def process_candidate_resume(
    *,
    candidate_id: str,
    filename: str,
    file_bytes: bytes,
    session_factory: async_sessionmaker,
    llm: LLMClient | None = None,
    uploader=None,
    github_fetcher=gather_github_evidence,
) -> None:
    llm = llm or get_llm_client()
    if uploader is None:
        settings = get_settings()
        if settings.supabase_url and settings.supabase_service_role_key:
            from app.storage.supabase_storage import upload_resume as uploader  # noqa: PLC0415
        else:
            from app.storage.local_storage import upload_resume as uploader  # noqa: PLC0415

    async with session_factory() as db:
        candidate = await db.get(Candidate, candidate_id)
        if candidate is None:
            logger.warning("process_candidate_resume: candidate %s not found", candidate_id)
            return

        try:
            candidate.status = "processing"
            await db.commit()

            extracted = extract_text_from_pdf(io.BytesIO(file_bytes))
            content_hash = hashlib.sha256(file_bytes).hexdigest()
            storage_path = await uploader(candidate_id=candidate_id, filename=filename, content=file_bytes)

            document = Document(
                candidate_id=candidate_id,
                kind="resume",
                filename=filename,
                content_hash=content_hash,
                storage_path=storage_path,
                extracted_text=extracted.full_text,
                page_offsets=extracted.page_offsets,
                size_bytes=len(file_bytes),
            )
            db.add(document)
            await db.flush()

            claim_result = await extract_claims(extracted.full_text, llm)
            claim_rows: list[Claim] = []
            for draft in claim_result.claims:
                claim = Claim(
                    candidate_id=candidate_id,
                    document_id=document.id,
                    claim_type=draft.claim_type,
                    claim_text=draft.claim_text,
                    normalized_skill=draft.normalized_skill,
                    asserted_years=draft.asserted_years,
                    asserted_start=draft.asserted_start,
                    asserted_end=draft.asserted_end,
                    asserted_org=draft.asserted_org,
                    source_span_start=draft.source_span_start,
                    source_span_end=draft.source_span_end,
                    extractor_model=draft.extractor_model,
                    prompt_version=draft.prompt_version,
                )
                db.add(claim)
                claim_rows.append(claim)
            await db.flush()

            consistency_inputs = [
                ConsistencyClaim(
                    id=c.id,
                    claim_type=c.claim_type,
                    claim_text=c.claim_text,
                    normalized_skill=c.normalized_skill,
                    asserted_years=c.asserted_years,
                    asserted_start=c.asserted_start,
                    asserted_end=c.asserted_end,
                    asserted_org=c.asserted_org,
                )
                for c in claim_rows
            ]
            for finding in run_consistency_checks(consistency_inputs):
                for claim_id in finding.claim_ids:
                    db.add(
                        Evidence(
                            claim_id=claim_id,
                            source_type="consistency",
                            verdict="contradicted",
                            summary=finding.summary,
                            artifact_url=None,
                            artifact_snippet=None,
                            model=None,
                            prompt_version="consistency.v1",
                        )
                    )

            if candidate.github_login:
                skill_claims = [(c.id, c.normalized_skill) for c in claim_rows if c.normalized_skill]
                settings = get_settings()
                try:
                    async with httpx.AsyncClient(timeout=15) as client:
                        github_drafts = await github_fetcher(
                            github_login=candidate.github_login,
                            claims=skill_claims,
                            client=client,
                            token=settings.github_token or None,
                        )
                except Exception:  # GitHub is opportunistic evidence — never fail the pipeline for it
                    logger.exception("GitHub evidence gathering failed for candidate %s", candidate_id)
                    github_drafts = []
                for d in github_drafts:
                    db.add(
                        Evidence(
                            claim_id=d.claim_id,
                            source_type="github",
                            verdict=d.verdict,
                            summary=d.summary,
                            artifact_url=d.artifact_url,
                            artifact_snippet=d.artifact_snippet,
                            model=None,
                            prompt_version="github.v1",
                        )
                    )

            candidate.status = "ready"
            candidate.status_detail = (
                f"{len(claim_rows)} claims extracted, {claim_result.discarded_uncitable} discarded (uncitable)"
            )
            await db.commit()
        except Exception as exc:
            await db.rollback()
            candidate.status = "failed"
            candidate.status_detail = str(exc)[:500]
            await db.commit()
            logger.exception("process_candidate_resume failed for candidate %s", candidate_id)
