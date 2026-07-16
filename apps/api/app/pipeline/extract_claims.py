"""Resume text -> claims, each with a verified source span.

This is where the citation guardrail bites for the first time: any extracted claim whose
`quoted_source_text` does not literally appear in the resume is DISCARDED, not saved with a
weaker verdict. A claim with no verifiable span is worse than no claim — see
docs/ARCHITECTURE.md section 4 ("citation validation guardrail").
"""

from dataclasses import dataclass

from app.llm.client import LLMClient
from app.llm.prompts.claim_extraction import PROMPT_VERSION, SYSTEM_PROMPT, ExtractedClaims, build_user_prompt
from app.pipeline.citation import find_span_for_text

_VALID_CLAIM_TYPES = {"skill", "employment", "education", "project", "credential"}


@dataclass
class ClaimDraft:
    claim_type: str
    claim_text: str
    normalized_skill: str | None
    asserted_years: float | None
    asserted_start: str | None
    asserted_end: str | None
    asserted_org: str | None
    source_span_start: int
    source_span_end: int
    extractor_model: str
    prompt_version: str


@dataclass
class ClaimExtractionResult:
    claims: list[ClaimDraft]
    total_extracted: int
    discarded_uncitable: int

    @property
    def hallucinated_citation_rate(self) -> float:
        if self.total_extracted == 0:
            return 0.0
        return self.discarded_uncitable / self.total_extracted


async def extract_claims(resume_text: str, llm: LLMClient) -> ClaimExtractionResult:
    result = await llm.generate_structured(
        system=SYSTEM_PROMPT,
        user=build_user_prompt(resume_text),
        schema=ExtractedClaims,
        prompt_version=PROMPT_VERSION,
        trace_name="extract_claims",
    )

    accepted: list[ClaimDraft] = []
    discarded = 0
    for claim in result.data.claims:
        if claim.claim_type not in _VALID_CLAIM_TYPES:
            discarded += 1
            continue
        span = find_span_for_text(resume_text, claim.quoted_source_text)
        if span is None:
            discarded += 1
            continue
        accepted.append(
            ClaimDraft(
                claim_type=claim.claim_type,
                claim_text=claim.claim_text,
                normalized_skill=claim.normalized_skill.lower().strip() if claim.normalized_skill else None,
                asserted_years=claim.asserted_years,
                asserted_start=claim.asserted_start,
                asserted_end=claim.asserted_end,
                asserted_org=claim.asserted_org,
                source_span_start=span[0],
                source_span_end=span[1],
                extractor_model=result.model,
                prompt_version=result.prompt_version,
            )
        )

    return ClaimExtractionResult(
        claims=accepted,
        total_extracted=len(result.data.claims),
        discarded_uncitable=discarded,
    )
