"""Recruiter-side interview management + the PUBLIC, unauthenticated candidate portal.

The candidate-facing routes (`/interview/{token}/*`) intentionally take no auth dependency —
a tokenized link is the whole point (see docs/ARCHITECTURE.md). They only ever expose
question text, never the rubric or rationale, and they never resolve to any other candidate's
data because every lookup is scoped by the unguessable token, not by id.
"""

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import get_current_user
from app.config import get_settings
from app.db.base import as_utc
from app.db.session import get_db
from app.ledger import append_event, sha256_text
from app.llm.client import LLMClient, get_llm_client
from app.models.candidate import Candidate
from app.models.evidence import Evidence
from app.models.interview import Interview, InterviewAnswer, InterviewQuestion
from app.models.job import Job
from app.models.user import User
from app.pipeline.interview.evaluate import compute_behavioral_flags, evaluate_answer, normalize_answer_text
from app.pipeline.interview.generate import generate_base_question, generate_followup_question
from app.pipeline.interview.state_machine import AskedQuestion, ClaimTarget, decide_next_action
from app.pipeline.match import ClaimLike, RequirementLike, match_claims_to_requirements
from app.pipeline.report import best_verdict
from app.routers.candidates import get_owned_candidate
from app.schemas.interview import (
    AnswerSubmit,
    InterviewAnswerRecruiterOut,
    InterviewCreateOut,
    InterviewQuestionPublicOut,
    InterviewQuestionRecruiterOut,
    InterviewStateOut,
    InterviewTranscriptOut,
)

router = APIRouter(tags=["interviews"])

_MAX_TARGET_CLAIMS = 8


async def _select_target_claims(candidate: Candidate, job: Job, db: AsyncSession) -> list[dict]:
    """Must-have requirements whose best evidence verdict is unverified/partial, ranked by
    JD order, capped at _MAX_TARGET_CLAIMS. A requirement with no matching claim at all can't
    be targeted — there's nothing to ground a question in."""
    requirements = [
        RequirementLike(id=r.id, skill=r.skill, normalized_skill=r.normalized_skill, importance=r.importance, min_years=r.min_years)
        for r in job.requirements
        if r.importance == "must_have"
    ]
    claims_by_id = {c.id: c for c in candidate.claims}
    claims = [
        ClaimLike(id=c.id, claim_text=c.claim_text, normalized_skill=c.normalized_skill, asserted_years=c.asserted_years)
        for c in candidate.claims
    ]
    matches = match_claims_to_requirements(requirements, claims)

    claim_ids = [c.id for c in candidate.claims]
    evidence_by_claim: dict[str, list[Evidence]] = {}
    if claim_ids:
        result = await db.execute(select(Evidence).where(Evidence.claim_id.in_(claim_ids)))
        for e in result.scalars().all():
            evidence_by_claim.setdefault(e.claim_id, []).append(e)

    req_by_id = {r.id: r for r in requirements}
    targets: list[dict] = []
    for m in matches:
        if not m.matching_claim_ids:
            continue
        claim_id = m.matching_claim_ids[0]
        verdict = best_verdict(evidence_by_claim.get(claim_id, []))
        if verdict not in ("unverified", "partial"):
            continue
        claim = claims_by_id[claim_id]
        targets.append(
            {
                "claim_id": claim_id,
                "requirement_id": m.requirement_id,
                "claim_text": claim.claim_text,
                "requirement_label": req_by_id[m.requirement_id].skill,
            }
        )
        if len(targets) >= _MAX_TARGET_CLAIMS:
            break
    return targets


@router.post("/candidates/{candidate_id}/interviews", response_model=InterviewCreateOut, status_code=status.HTTP_201_CREATED)
async def create_interview(
    candidate_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> InterviewCreateOut:
    candidate = await get_owned_candidate(candidate_id, user, db)
    if candidate.status != "ready":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Resume is still processing; try again shortly")

    job_result = await db.execute(select(Job).options(selectinload(Job.requirements)).where(Job.id == candidate.job_id))
    job = job_result.scalar_one()

    target_claims = await _select_target_claims(candidate, job, db)
    if not target_claims:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "No unverified must-have claims to target — nothing for the interview to probe.",
        )

    settings = get_settings()
    interview = Interview(
        candidate_id=candidate.id,
        job_id=job.id,
        token=secrets.token_urlsafe(32),
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.interview_token_ttl_hours),
        target_claims=target_claims,
    )
    db.add(interview)
    await db.flush()
    await append_event(
        db,
        candidate_id=candidate.id,
        event_type="interview_created",
        actor_type="human",
        actor_id=user.email,
        payload={
            "interview_id": interview.id,
            "target_claim_count": len(target_claims),
            "expires_at": interview.expires_at.isoformat(),
        },
    )
    await db.commit()
    await db.refresh(interview)

    return InterviewCreateOut(
        id=interview.id,
        token=interview.token,
        status=interview.status,
        expires_at=interview.expires_at,
        interview_url_path=f"/interview/{interview.token}",
    )


async def _get_interview_by_token(token: str, db: AsyncSession) -> Interview:
    # populate_existing: submit_answer() writes a new InterviewAnswer and then re-fetches the
    # interview (via get_interview_state) on the same session to recompute the next action.
    # Without this, the already-loaded questions[].answer relationship stays stale and the
    # state machine would think the just-answered question is still unanswered. See the
    # identical fix + explanation on get_owned_job in routers/jobs.py.
    result = await db.execute(
        select(Interview)
        .options(selectinload(Interview.questions).selectinload(InterviewQuestion.answer))
        .where(Interview.token == token)
        .execution_options(populate_existing=True)
    )
    interview = result.scalar_one_or_none()
    if interview is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Interview not found")
    if as_utc(interview.expires_at) < datetime.now(timezone.utc) and interview.status not in ("submitted",):
        interview.status = "expired"
        await db.commit()
    return interview


def _targets_from_interview(interview: Interview) -> list[ClaimTarget]:
    return [
        ClaimTarget(
            claim_id=t["claim_id"],
            requirement_id=t["requirement_id"],
            claim_text=t["claim_text"],
            requirement_label=t["requirement_label"],
        )
        for t in interview.target_claims
    ]


def _asked_from_interview(interview: Interview) -> list[AskedQuestion]:
    return [
        AskedQuestion(
            claim_id=q.targets_claim_id,
            depth=q.depth,
            specificity_verdict=q.answer.specificity_verdict if q.answer else None,
        )
        for q in interview.questions
    ]


@router.get("/interview/{token}", response_model=InterviewStateOut)
async def get_interview_state(token: str, db: AsyncSession = Depends(get_db)) -> InterviewStateOut:
    interview = await _get_interview_by_token(token, db)
    if interview.status == "expired":
        raise HTTPException(status.HTTP_410_GONE, "This interview link has expired")
    if interview.status == "submitted":
        return InterviewStateOut(status=interview.status, current_question=None, questions_answered=len(interview.questions), is_complete=True)

    targets = _targets_from_interview(interview)
    asked = _asked_from_interview(interview)
    action = decide_next_action(targets, asked)

    if action.kind == "done":
        interview.status = "submitted"
        interview.submitted_at = datetime.now(timezone.utc)
        await append_event(
            db,
            candidate_id=interview.candidate_id,
            event_type="interview_submitted",
            actor_type="candidate",
            payload={"interview_id": interview.id, "questions_answered": len(interview.questions)},
        )
        await db.commit()
        return InterviewStateOut(status=interview.status, current_question=None, questions_answered=len(interview.questions), is_complete=True)

    if action.kind == "await_answer":
        pending_question = next(q for q in interview.questions if q.targets_claim_id == action.claim.claim_id and q.depth == action.depth)
        return InterviewStateOut(
            status=interview.status,
            current_question=InterviewQuestionPublicOut(id=pending_question.id, ordinal=pending_question.ordinal, question_text=pending_question.question_text),
            questions_answered=sum(1 for q in interview.questions if q.answer is not None),
            is_complete=False,
        )

    # ask_base or ask_followup: generate the next question now (lazy — only when the
    # candidate actually reaches this point, so an abandoned interview costs nothing).
    llm = get_llm_client()
    if action.kind == "ask_base":
        generated = await generate_base_question(claim=action.claim, artifact_context=None, llm=llm)
    else:
        prev_question = next(
            q for q in interview.questions if q.targets_claim_id == action.claim.claim_id and q.depth == action.previous_question.depth
        )
        generated = await generate_followup_question(
            original_question_text=prev_question.question_text,
            answer_text=prev_question.answer.answer_text if prev_question.answer else "",
            rubric_must_mention=prev_question.rubric.get("must_mention", []),
            llm=llm,
        )

    if interview.status == "pending":
        interview.status = "in_progress"
        interview.started_at = datetime.now(timezone.utc)

    question = InterviewQuestion(
        interview_id=interview.id,
        ordinal=len(interview.questions),
        depth=action.depth,
        targets_claim_id=action.claim.claim_id,
        question_text=generated.question_text,
        rubric=generated.rubric,
        rationale=generated.rationale,
    )
    db.add(question)
    await db.flush()
    await append_event(
        db,
        candidate_id=interview.candidate_id,
        event_type="question_asked",
        actor_type="model",
        payload={
            "interview_id": interview.id,
            "question_id": question.id,
            "ordinal": question.ordinal,
            "depth": question.depth,
            "targets_claim_id": question.targets_claim_id,
            "question_sha256": sha256_text(question.question_text),
        },
    )
    await db.commit()
    await db.refresh(question)

    return InterviewStateOut(
        status=interview.status,
        current_question=InterviewQuestionPublicOut(id=question.id, ordinal=question.ordinal, question_text=question.question_text),
        questions_answered=sum(1 for q in interview.questions if q.answer is not None),
        is_complete=False,
    )


@router.post("/interview/{token}/questions/{question_id}/answer", response_model=InterviewStateOut)
async def submit_answer(
    token: str,
    question_id: str,
    payload: AnswerSubmit,
    db: AsyncSession = Depends(get_db),
    llm: LLMClient = Depends(get_llm_client),
) -> InterviewStateOut:
    interview = await _get_interview_by_token(token, db)
    if interview.status not in ("in_progress", "pending"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This interview is not accepting answers")

    question = next((q for q in interview.questions if q.id == question_id), None)
    if question is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found on this interview")
    if question.answer is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This question was already answered")

    answer_text = normalize_answer_text(payload.answer_text)
    evaluation = await evaluate_answer(
        question_text=question.question_text,
        rubric_must_mention=question.rubric.get("must_mention", []),
        answer_text=answer_text,
        llm=llm,
    )
    flags = compute_behavioral_flags(
        time_to_first_keystroke_ms=payload.time_to_first_keystroke_ms,
        total_time_ms=payload.total_time_ms,
        paste_event_count=payload.paste_event_count,
    )

    answer = InterviewAnswer(
        question_id=question.id,
        answer_text=answer_text,
        specificity_verdict=evaluation.specificity_verdict,
        specificity_notes=evaluation.specificity_notes,
        time_to_first_keystroke_ms=payload.time_to_first_keystroke_ms,
        total_time_ms=payload.total_time_ms,
        paste_event_count=payload.paste_event_count,
        revision_count=payload.revision_count,
        review_flags=flags,
    )
    db.add(answer)
    await db.flush()
    await append_event(
        db,
        candidate_id=interview.candidate_id,
        event_type="answer_recorded",
        actor_type="candidate",
        payload={
            "interview_id": interview.id,
            "question_id": question.id,
            "answer_id": answer.id,
            "answer_sha256": sha256_text(answer_text),
            "specificity_verdict": evaluation.specificity_verdict,
            "review_flags": flags,
        },
    )

    # Write interview evidence for the targeted claim: a strong answer verifies it, a weak
    # one leaves it at whatever the evidence pass already established (never contradicts on
    # interview alone — that would be far too aggressive for a single answer).
    if evaluation.specificity_verdict == "strong":
        db.add(
            Evidence(
                claim_id=question.targets_claim_id,
                source_type="interview",
                verdict="verified",
                summary=f"Interview: {evaluation.specificity_notes}",
                artifact_url=None,
                artifact_snippet=answer_text[:500],
                model=None,
                prompt_version="interview_evaluation.v1",
            )
        )

    await db.commit()

    return await get_interview_state(token, db)


@router.get("/candidates/{candidate_id}/interviews/{interview_id}/transcript", response_model=InterviewTranscriptOut)
async def get_transcript(
    candidate_id: str,
    interview_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InterviewTranscriptOut:
    await get_owned_candidate(candidate_id, user, db)  # ownership check
    result = await db.execute(
        select(Interview)
        .options(selectinload(Interview.questions).selectinload(InterviewQuestion.answer))
        .where(Interview.id == interview_id, Interview.candidate_id == candidate_id)
    )
    interview = result.scalar_one_or_none()
    if interview is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Interview not found")

    return InterviewTranscriptOut(
        interview_id=interview.id,
        status=interview.status,
        questions=[InterviewQuestionRecruiterOut.model_validate(q) for q in interview.questions],
        answers=[InterviewAnswerRecruiterOut.model_validate(q.answer) for q in interview.questions if q.answer],
    )
