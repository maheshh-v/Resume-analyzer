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
from app.ledger import append_event
from app.llm.client import LLMClient, get_llm_client
from app.observability.context import llm_call_context
from app.models.candidate import Candidate
from app.models.claim import Claim
from app.models.document import Document
from app.models.evidence import Evidence
from app.pipeline.evidence.consistency import ConsistencyClaim, run_consistency_checks
from app.pipeline.evidence.github import gather_github_evidence
from app.pipeline.evidence.google_patents import gather_patent_evidence
from app.pipeline.evidence.package_ownership import gather_package_ownership_evidence
from app.pipeline.evidence.semantic_scholar import gather_semantic_scholar_evidence
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
            await append_event(
                db,
                candidate_id=candidate_id,
                event_type="resume_ingested",
                actor_type="system",
                payload={"filename": filename, "file_sha256": content_hash, "size_bytes": len(file_bytes)},
            )

            with llm_call_context(candidate_id=candidate_id, job_id=candidate.job_id):
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
            await append_event(
                db,
                candidate_id=candidate_id,
                event_type="claims_extracted",
                actor_type="model",
                actor_id=claim_result.claims[0].extractor_model if claim_result.claims else None,
                payload={
                    "claim_count": len(claim_rows),
                    "discarded_uncitable": claim_result.discarded_uncitable,
                },
            )

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
            consistency_findings = run_consistency_checks(consistency_inputs)
            for finding in consistency_findings:
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
            await append_event(
                db,
                candidate_id=candidate_id,
                event_type="consistency_checked",
                actor_type="system",
                payload={
                    "claims_checked": len(consistency_inputs),
                    "contradictions_found": len(consistency_findings),
                },
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
                await append_event(
                    db,
                    candidate_id=candidate_id,
                    event_type="github_evidence",
                    actor_type="system",
                    payload={"github_login": candidate.github_login, "evidence_count": len(github_drafts)},
                )

            await _gather_connector_evidence(db, candidate=candidate, claim_rows=claim_rows)

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

    # Flush cost telemetry now that all pipeline commits are done — no lock contention, and the
    # per-candidate cost endpoint is populated the moment processing finishes.
    await llm.drain_cost_logs()


async def _gather_connector_evidence(db, *, candidate: Candidate, claim_rows: list[Claim]) -> None:
    """Opportunistic external evidence — Semantic Scholar, Google Patents, package ownership.

    Each source is behind its own config flag (all off by default) and each has ALREADY passed the
    URL+substring citation guardrail inside the connector, so anything returned here is safe to
    write. Like the GitHub pass, this never fails the pipeline and absence writes nothing.
    """
    settings = get_settings()
    if not (
        settings.enable_semantic_scholar
        or settings.enable_google_patents
        or settings.enable_package_ownership
    ):
        return

    research_claim = next(
        (c for c in claim_rows if c.claim_type in ("project", "education", "credential")), None
    )
    package_claim = next((c for c in claim_rows if c.claim_type in ("project", "skill")), None)

    drafts = []
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            if settings.enable_semantic_scholar and research_claim and candidate.name:
                drafts += await gather_semantic_scholar_evidence(
                    author_name=candidate.name, claim_id=research_claim.id, client=client
                )
            if settings.enable_google_patents and research_claim and candidate.name:
                drafts += await gather_patent_evidence(
                    inventor_name=candidate.name, claim_id=research_claim.id, client=client
                )
            if settings.enable_package_ownership and package_claim and candidate.github_login:
                drafts += await gather_package_ownership_evidence(
                    claim_id=package_claim.id, client=client, npm_handle=candidate.github_login
                )
    except Exception:  # external evidence is opportunistic — never fail the pipeline for it
        logger.exception("Connector evidence gathering failed for candidate %s", candidate.id)
        return

    for d in drafts:
        db.add(
            Evidence(
                claim_id=d.claim_id,
                source_type=d.source_type,
                verdict=d.verdict,
                summary=d.summary,
                artifact_url=d.artifact_url,
                artifact_snippet=d.artifact_snippet,
                model=None,
                prompt_version=f"{d.source_type}.v1",
            )
        )
    if drafts:
        await append_event(
            db,
            candidate_id=candidate.id,
            event_type="connector_evidence",
            actor_type="system",
            payload={"evidence_count": len(drafts), "sources": sorted({d.source_type for d in drafts})},
        )
