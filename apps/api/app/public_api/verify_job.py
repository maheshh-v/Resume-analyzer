"""The async verification run behind POST /api/v1/public/verify.

Reuses the real pipeline stages (JD → requirements, resume → claims, consistency, match, report
assembly) against the mocked-in-tests LLM, then renders a branded PDF, stores it, and webhooks the
caller. It deliberately runs a lighter, un-ledgered path than the recruiter Candidate flow — no
GitHub/connector passes and no Evidence Ledger — which is a documented Phase 4 simplification.

Every failure marks the report `failed` with a short reason; the webhook still fires so the caller
learns the terminal state. Never raises out of the background task.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import asdict

import httpx
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.base import utcnow
from app.db.session import SessionLocal
from app.llm.client import LLMClient, get_llm_client
from app.models.public_report import PublicReport
from app.observability.context import llm_call_context
from app.pipeline.evidence.consistency import ConsistencyClaim, run_consistency_checks
from app.pipeline.extract_claims import extract_claims
from app.pipeline.extract_jd import extract_job_requirements
from app.pipeline.match import ClaimLike, RequirementLike, match_claims_to_requirements
from app.pipeline.report import EvidenceRow, build_hiring_summary
from app.public_api.pdf import render_report_pdf
from app.storage.report_storage import store_report_pdf

logger = logging.getLogger(__name__)


async def _default_webhook_post(url: str, payload: dict) -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(url, json=payload)


async def _fetch_logo(logo_url: str) -> bytes | None:
    """Best-effort fetch of the org logo for the PDF slot. A missing/broken logo is never fatal."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(logo_url, follow_redirects=True)
        return response.content if response.status_code == 200 else None
    except Exception:
        logger.info("public verify: could not fetch logo %s", logo_url, exc_info=True)
        return None


async def _safe_webhook(poster: Callable[[str, dict], Awaitable[None]], url: str, payload: dict) -> None:
    try:
        await poster(url, payload)
    except Exception:  # a caller's broken webhook must not surface anywhere
        logger.info("public verify: webhook POST to %s failed", url, exc_info=True)


async def run_public_verification(
    *,
    report_id: str,
    resume_text: str,
    jd_text: str,
    org_name: str,
    logo_url: str | None = None,
    logo_bytes: bytes | None = None,
    webhook_url: str | None = None,
    session_factory: async_sessionmaker = SessionLocal,
    llm: LLMClient | None = None,
    webhook_poster: Callable[[str, dict], Awaitable[None]] | None = None,
) -> None:
    llm = llm or get_llm_client()
    if logo_bytes is None and logo_url:
        logo_bytes = await _fetch_logo(logo_url)
    poster = webhook_poster or _default_webhook_post

    status = "failed"
    async with session_factory() as db:
        report = await db.get(PublicReport, report_id)
        if report is None:
            logger.warning("public verify: report %s vanished", report_id)
            return
        try:
            report.status = "processing"
            await db.commit()

            with llm_call_context(job_id=report_id):
                req_drafts = await extract_job_requirements(jd_text, llm)
                claim_result = await extract_claims(resume_text, llm)

            requirements = [
                RequirementLike(
                    id=f"r{i}", skill=d.skill, normalized_skill=d.normalized_skill,
                    importance=d.importance, min_years=d.min_years,
                )
                for i, d in enumerate(req_drafts)
            ]
            claims = [
                ClaimLike(id=f"c{i}", claim_text=c.claim_text, normalized_skill=c.normalized_skill, asserted_years=c.asserted_years)
                for i, c in enumerate(claim_result.claims)
            ]
            claim_text_by_id = {f"c{i}": c.claim_text for i, c in enumerate(claim_result.claims)}

            consistency_inputs = [
                ConsistencyClaim(
                    id=f"c{i}", claim_type=c.claim_type, claim_text=c.claim_text,
                    normalized_skill=c.normalized_skill, asserted_years=c.asserted_years,
                    asserted_start=c.asserted_start, asserted_end=c.asserted_end, asserted_org=c.asserted_org,
                )
                for i, c in enumerate(claim_result.claims)
            ]
            findings = run_consistency_checks(consistency_inputs)
            evidence = [
                EvidenceRow(claim_id=cid, source_type="consistency", verdict="contradicted", summary=f.summary, artifact_url=None)
                for f in findings
                for cid in f.claim_ids
            ]

            matches = match_claims_to_requirements(requirements, claims)
            summary = build_hiring_summary(
                matches=matches, evidence=evidence, consistency_findings=findings,
                transcript=[], claim_text_by_id=claim_text_by_id,
            )
            summary_dict = asdict(summary)

            pdf_bytes = render_report_pdf(summary=summary_dict, org_name=org_name, logo_bytes=logo_bytes)
            pdf_path = await store_report_pdf(report_id=report_id, content=pdf_bytes)

            report.report_json = summary_dict
            report.pdf_storage_path = pdf_path
            report.status = "ready"
            report.completed_at = utcnow()
            await db.commit()
            status = "ready"
        except Exception as exc:
            await db.rollback()
            report.status = "failed"
            report.error = str(exc)[:500]
            await db.commit()
            status = "failed"
            logger.exception("public verification failed for report %s", report_id)

    if webhook_url:
        await _safe_webhook(poster, webhook_url, {"report_id": report_id, "status": status})
    await llm.drain_cost_logs()
