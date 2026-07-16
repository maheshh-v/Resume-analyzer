"""Assembles the hiring summary from already-validated data. Deliberately NOT an LLM call:

this is the stage where trust matters most, so it's a mechanical rendering of claims,
matches, evidence, and interview transcripts that were already validated upstream — not a
fresh generation step that could invent something unfalsifiable at the last mile.

No score. No ranking. No auto-verdict. "Evidence coverage" is a count of requirements that
have at least one corroborating evidence row — a fact about documents, not a score of a
person. See docs/ARCHITECTURE.md / docs/PRODUCT_PLAN.md section 3.2 for why.
"""

from dataclasses import dataclass, field
from typing import Protocol, Sequence

from app.pipeline.evidence.consistency import ConsistencyFinding
from app.pipeline.match import RequirementMatch


class HasVerdict(Protocol):
    verdict: str


@dataclass
class EvidenceRow:
    claim_id: str
    source_type: str
    verdict: str
    summary: str
    artifact_url: str | None


@dataclass
class QAExchange:
    depth: int
    question_text: str
    rationale: str
    answer_text: str | None
    specificity_verdict: str | None
    specificity_notes: str | None
    review_flags: list[str] = field(default_factory=list)


@dataclass
class MatrixRow:
    requirement_id: str
    skill: str
    importance: str
    match_status: str  # matched | partial | gap
    claim_texts: list[str]
    best_verdict: str  # verified | partial | contradicted | unverified
    evidence_summaries: list[str]
    evidence_urls: list[str]


@dataclass
class HiringSummary:
    evidence_coverage_count: int
    evidence_coverage_total: int
    conflicts: list[str]
    matrix: list[MatrixRow]
    verified_skills: list[MatrixRow]
    needs_manual_verification: list[MatrixRow]
    technical_strengths: list[str]
    weak_areas: list[str]
    suggested_followups: list[str]
    transcript: list[QAExchange]


# Display priority, not sentiment: a contradiction must never be masked by a coexisting
# "verified" from another source — it's the most actionable signal in the product (see
# docs/PRODUCT_PLAN.md "contradicted is the money shot"), so it always wins the rollup.
_VERDICT_DISPLAY_PRIORITY = {"contradicted": 3, "verified": 2, "partial": 1, "unverified": 0}


def best_verdict(evidence_for_claims: Sequence[HasVerdict]) -> str:
    if not evidence_for_claims:
        return "unverified"
    return max((e.verdict for e in evidence_for_claims), key=lambda v: _VERDICT_DISPLAY_PRIORITY.get(v, 0))


def build_hiring_summary(
    *,
    matches: list[RequirementMatch],
    evidence: list[EvidenceRow],
    consistency_findings: list[ConsistencyFinding],
    transcript: list[QAExchange],
    claim_text_by_id: dict[str, str],
) -> HiringSummary:
    evidence_by_claim: dict[str, list[EvidenceRow]] = {}
    for e in evidence:
        evidence_by_claim.setdefault(e.claim_id, []).append(e)

    matrix: list[MatrixRow] = []
    for m in matches:
        claim_evidence = [e for cid in m.matching_claim_ids for e in evidence_by_claim.get(cid, [])]
        matrix.append(
            MatrixRow(
                requirement_id=m.requirement_id,
                skill=m.skill,
                importance=m.importance,
                match_status=m.status,
                claim_texts=[claim_text_by_id.get(cid, "") for cid in m.matching_claim_ids],
                best_verdict=best_verdict(claim_evidence),
                evidence_summaries=[e.summary for e in claim_evidence],
                evidence_urls=[e.artifact_url for e in claim_evidence if e.artifact_url],
            )
        )

    coverage_count = sum(1 for row in matrix if row.evidence_summaries)
    verified_skills = [row for row in matrix if row.best_verdict == "verified"]
    needs_manual_verification = [
        row for row in matrix if row.best_verdict == "unverified" and row.importance == "must_have"
    ]

    technical_strengths = [
        f"{row.skill}: {row.evidence_summaries[0]}" for row in verified_skills if row.evidence_summaries
    ]
    weak_areas = [
        f"{row.skill}: {row.evidence_summaries[0]}" for row in matrix if row.best_verdict == "contradicted"
    ] + [f"{row.skill}: claimed but no matching evidence found" for row in matrix if row.match_status == "gap"]

    followups: list[str] = [f.summary for f in consistency_findings]
    for row in needs_manual_verification:
        followups.append(f"{row.skill} — claimed, must-have, no public/internal evidence. Probe live.")
    for exchange in transcript:
        if exchange.specificity_verdict == "weak":
            followups.append(f"Answer thinned out on: \"{exchange.question_text}\"")

    return HiringSummary(
        evidence_coverage_count=coverage_count,
        evidence_coverage_total=len(matrix),
        conflicts=[f.summary for f in consistency_findings],
        matrix=matrix,
        verified_skills=verified_skills,
        needs_manual_verification=needs_manual_verification,
        technical_strengths=technical_strengths,
        weak_areas=weak_areas,
        suggested_followups=followups,
        transcript=transcript,
    )
