"""The Evidence Ledger: a per-candidate, hash-chained audit trail of the entire verification.

Every consequential action — ingestion, extraction, evidence, each interview exchange, the
human decision — is appended as a LedgerEvent whose hash covers its content AND the previous
event's hash. Verification replays the chain: any edit, insertion, or deletion after the fact
breaks every hash downstream and is pinpointed to the exact event. Free text stored in other
tables (question/answer text, decision rationale) is referenced by SHA-256, so editing those
rows later is equally detectable ("content attestation").

Events are appended on the same session as the action they describe and committed together,
so the ledger can never assert something the database doesn't show.
"""

import hashlib
import json
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import as_utc, utcnow
from app.models.ledger import GENESIS_HASH, LedgerEvent


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _compute_event_hash(
    *,
    candidate_id: str,
    seq: int,
    event_type: str,
    actor_type: str,
    actor_id: str | None,
    payload: dict,
    created_at_iso: str,
    prev_hash: str,
) -> str:
    canonical = "|".join(
        [
            candidate_id,
            str(seq),
            event_type,
            actor_type,
            actor_id or "",
            json.dumps(payload, sort_keys=True, separators=(",", ":")),
            created_at_iso,
            prev_hash,
        ]
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def append_event(
    db: AsyncSession,
    *,
    candidate_id: str,
    event_type: str,
    actor_type: str,
    actor_id: str | None = None,
    payload: dict | None = None,
) -> LedgerEvent:
    """Append the next link to the candidate's chain. Does NOT commit — the caller commits the
    event atomically with the action it records."""
    payload = payload or {}
    result = await db.execute(
        select(LedgerEvent)
        .where(LedgerEvent.candidate_id == candidate_id)
        .order_by(LedgerEvent.seq.desc())
        .limit(1)
    )
    last = result.scalar_one_or_none()
    seq = (last.seq + 1) if last else 0
    prev_hash = last.event_hash if last else GENESIS_HASH

    created_at = utcnow()
    event = LedgerEvent(
        candidate_id=candidate_id,
        seq=seq,
        event_type=event_type,
        actor_type=actor_type,
        actor_id=actor_id,
        payload=payload,
        prev_hash=prev_hash,
        event_hash=_compute_event_hash(
            candidate_id=candidate_id,
            seq=seq,
            event_type=event_type,
            actor_type=actor_type,
            actor_id=actor_id,
            payload=payload,
            created_at_iso=created_at.isoformat(),
            prev_hash=prev_hash,
        ),
        created_at=created_at,
    )
    db.add(event)
    await db.flush()
    return event


@dataclass
class ChainVerification:
    ok: bool
    event_count: int
    # seq of the first event whose hash/linkage doesn't replay — None when the chain holds
    first_broken_seq: int | None = None
    # content attestations that no longer match the referenced rows, e.g. an edited answer
    content_mismatches: list[dict] = field(default_factory=list)


async def verify_chain(db: AsyncSession, candidate_id: str) -> ChainVerification:
    """Replay the candidate's chain from genesis and re-attest referenced content."""
    result = await db.execute(
        select(LedgerEvent).where(LedgerEvent.candidate_id == candidate_id).order_by(LedgerEvent.seq)
    )
    events = list(result.scalars().all())

    expected_prev = GENESIS_HASH
    for i, event in enumerate(events):
        recomputed = _compute_event_hash(
            candidate_id=event.candidate_id,
            seq=event.seq,
            event_type=event.event_type,
            actor_type=event.actor_type,
            actor_id=event.actor_id,
            payload=event.payload,
            created_at_iso=as_utc(event.created_at).isoformat(),
            prev_hash=event.prev_hash,
        )
        if event.seq != i or event.prev_hash != expected_prev or event.event_hash != recomputed:
            return ChainVerification(ok=False, event_count=len(events), first_broken_seq=event.seq)
        expected_prev = event.event_hash

    mismatches = await _verify_content_attestations(db, events)
    return ChainVerification(ok=not mismatches, event_count=len(events), content_mismatches=mismatches)


async def _verify_content_attestations(db: AsyncSession, events: list[LedgerEvent]) -> list[dict]:
    """Re-hash rows the ledger attested to (question/answer text, decision rationale) and
    report any that have been altered since their event was written."""
    from app.models.decision import Decision  # noqa: PLC0415 — avoid module-level model imports here
    from app.models.interview import InterviewAnswer, InterviewQuestion  # noqa: PLC0415

    mismatches: list[dict] = []
    for event in events:
        payload = event.payload
        row_text: str | None = None
        attested: str | None = None
        if event.event_type == "question_asked" and payload.get("question_sha256"):
            question = await db.get(InterviewQuestion, payload.get("question_id"))
            row_text = question.question_text if question else None
            attested = payload["question_sha256"]
        elif event.event_type == "answer_recorded" and payload.get("answer_sha256"):
            answer = await db.get(InterviewAnswer, payload.get("answer_id"))
            row_text = answer.answer_text if answer else None
            attested = payload["answer_sha256"]
        elif event.event_type == "decision_recorded" and payload.get("rationale_sha256"):
            decision = await db.get(Decision, payload.get("decision_id"))
            row_text = decision.rationale if decision else None
            attested = payload["rationale_sha256"]
        else:
            continue

        if row_text is None or sha256_text(row_text) != attested:
            mismatches.append(
                {
                    "seq": event.seq,
                    "event_type": event.event_type,
                    "problem": "referenced row deleted" if row_text is None else "referenced text was altered",
                }
            )
    return mismatches
