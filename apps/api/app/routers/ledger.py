from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.base import utcnow
from app.db.session import get_db
from app.ledger import verify_chain
from app.models.ledger import LedgerEvent
from app.models.user import User
from app.routers.candidates import get_owned_candidate
from app.schemas.ledger import LedgerEventOut, LedgerOut, LedgerVerificationOut

router = APIRouter(tags=["ledger"])


@router.get("/candidates/{candidate_id}/ledger", response_model=LedgerOut)
async def get_ledger(
    candidate_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> LedgerOut:
    candidate = await get_owned_candidate(candidate_id, user, db)
    result = await db.execute(
        select(LedgerEvent).where(LedgerEvent.candidate_id == candidate.id).order_by(LedgerEvent.seq)
    )
    return LedgerOut(
        candidate_id=candidate.id,
        events=[LedgerEventOut.model_validate(e) for e in result.scalars().all()],
    )


@router.get("/candidates/{candidate_id}/ledger/verify", response_model=LedgerVerificationOut)
async def verify_ledger(
    candidate_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> LedgerVerificationOut:
    candidate = await get_owned_candidate(candidate_id, user, db)
    verification = await verify_chain(db, candidate.id)
    return LedgerVerificationOut(
        ok=verification.ok,
        event_count=verification.event_count,
        first_broken_seq=verification.first_broken_seq,
        content_mismatches=verification.content_mismatches,
        verified_at=utcnow(),
    )
