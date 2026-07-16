from pydantic import BaseModel, Field

PROMPT_VERSION = "jd_extraction.v1"

SYSTEM_PROMPT = """You are a technical recruiter's assistant. You read a job description and \
extract the concrete, testable requirements from it — not marketing fluff, not culture-fit \
language. For each requirement, also state what evidence would actually satisfy it: what \
would a recruiter need to see or hear to believe a candidate really has this?

Rules:
- Only extract requirements a candidate's resume or interview answer could actually verify \
(skills, technologies, years of experience, domains, credentials). Skip "fast-paced \
environment", "team player", benefits, and company description.
- `quoted_source_text` MUST be copied verbatim, character-for-character, from the job \
description you were given. Never paraphrase it. This is used to locate the requirement in \
the original document, so an inexact quote is useless.
- `importance` is "must_have" only if the JD text itself signals it's required (e.g. \
"required", "must have", listed under "Requirements" rather than "Nice to have" / "Bonus").
- `evidence_criteria` should be concrete: "a public repo using this framework", "a specific \
project or role where this was applied for at least N months", not vague restatement."""


def build_user_prompt(jd_text: str) -> str:
    return f"Job description:\n\n{jd_text}\n\nExtract the structured requirements."


class ExtractedRequirement(BaseModel):
    skill: str = Field(description="The requirement as a short human-readable label, e.g. 'Kubernetes'")
    normalized_skill: str = Field(description="Lowercase, canonical form, e.g. 'kubernetes'")
    category: str = Field(description="One of: technical, domain, credential, soft")
    importance: str = Field(description="One of: must_have, nice_to_have")
    min_years: float | None = Field(default=None, description="Minimum years of experience if stated")
    evidence_criteria: str = Field(description="What evidence would actually satisfy this requirement")
    quoted_source_text: str = Field(description="Verbatim substring of the JD this was extracted from")


class ExtractedRequirements(BaseModel):
    requirements: list[ExtractedRequirement]
