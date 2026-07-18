"""Background ingestion for sheet-imported candidates whose resumes live behind URLs.

Runs after the import endpoint has responded. Each item is independent: a dead URL marks that
one candidate `failed` with a readable reason and the rest keep going. Successful fetches hand
off to the exact same process_candidate_resume pipeline as a manual upload.
"""

import logging
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.intake.fetch import ResumeFetchError, fetch_resume_pdf
from app.models.candidate import Candidate
from app.pipeline.orchestrate import process_candidate_resume

logger = logging.getLogger(__name__)


@dataclass
class ResumeFetchItem:
    candidate_id: str
    candidate_name: str
    resume_url: str


async def _mark_failed(candidate_id: str, detail: str, session_factory: async_sessionmaker) -> None:
    async with session_factory() as db:
        candidate = await db.get(Candidate, candidate_id)
        if candidate is not None:
            candidate.status = "failed"
            candidate.status_detail = detail[:500]
            await db.commit()


async def ingest_sheet_resumes(
    *,
    items: list[ResumeFetchItem],
    session_factory: async_sessionmaker,
    fetcher=fetch_resume_pdf,
    processor=process_candidate_resume,
) -> None:
    for item in items:
        try:
            content = await fetcher(item.resume_url)
        except ResumeFetchError as exc:
            await _mark_failed(item.candidate_id, f"Resume URL: {exc}", session_factory)
            continue
        except Exception:
            logger.exception("sheet import: unexpected error fetching resume for %s", item.candidate_id)
            await _mark_failed(item.candidate_id, "Resume URL: unexpected fetch error", session_factory)
            continue
        await processor(
            candidate_id=item.candidate_id,
            filename=f"{item.candidate_name}.pdf",
            file_bytes=content,
            session_factory=session_factory,
        )
