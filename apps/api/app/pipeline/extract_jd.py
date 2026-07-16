"""JD text -> structured, recruiter-reviewable requirements.

The JD defines what's worth verifying downstream, so getting this stage right (and letting
the recruiter correct it in ~30 seconds) is what keeps garbage from propagating through
claim matching and the interview.
"""

from dataclasses import dataclass

from app.llm.client import LLMClient
from app.llm.prompts.jd_extraction import PROMPT_VERSION, SYSTEM_PROMPT, ExtractedRequirements, build_user_prompt
from app.pipeline.citation import find_span_for_text


@dataclass
class RequirementDraft:
    skill: str
    normalized_skill: str
    category: str
    importance: str
    min_years: float | None
    evidence_criteria: str
    source_span_start: int | None
    source_span_end: int | None
    extractor_model: str
    prompt_version: str


async def extract_job_requirements(jd_text: str, llm: LLMClient) -> list[RequirementDraft]:
    result = await llm.generate_structured(
        system=SYSTEM_PROMPT,
        user=build_user_prompt(jd_text),
        schema=ExtractedRequirements,
        prompt_version=PROMPT_VERSION,
        trace_name="extract_jd",
    )

    drafts: list[RequirementDraft] = []
    for req in result.data.requirements:
        span = find_span_for_text(jd_text, req.quoted_source_text)
        drafts.append(
            RequirementDraft(
                skill=req.skill,
                normalized_skill=req.normalized_skill.lower().strip(),
                category=req.category,
                importance=req.importance if req.importance in ("must_have", "nice_to_have") else "nice_to_have",
                min_years=req.min_years,
                evidence_criteria=req.evidence_criteria,
                source_span_start=span[0] if span else None,
                source_span_end=span[1] if span else None,
                extractor_model=result.model,
                prompt_version=result.prompt_version,
            )
        )
    return drafts
