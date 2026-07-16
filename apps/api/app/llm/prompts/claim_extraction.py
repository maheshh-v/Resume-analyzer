from pydantic import BaseModel, Field

PROMPT_VERSION = "claim_extraction.v1"

SYSTEM_PROMPT = """You extract verifiable technical claims from a resume. A claim is anything \
a candidate asserts about their skills, employment, education, projects, or credentials that \
could in principle be checked. You are not summarizing the resume — you are producing a list \
of falsifiable statements.

Rules:
- One claim per fact. "4 years TensorFlow, led a team of 3" is two claims, not one.
- `quoted_source_text` MUST be copied verbatim, character-for-character, from the resume \
text you were given — the exact substring, not a paraphrase or a cleaned-up version. This is \
the only way the system can prove the claim actually appears in the document, so precision \
here matters more than completeness.
- claim_type is one of: skill, employment, education, project, credential.
- For employment claims, fill asserted_org, asserted_start, asserted_end (format "YYYY-MM", \
best effort) so the system can check date consistency.
- For skill claims with a stated duration ("3+ years of Python"), fill asserted_years and \
normalized_skill (lowercase canonical form, e.g. "python").
- Do not invent claims that aren't in the text. Do not infer skills from job titles alone."""


def build_user_prompt(resume_text: str) -> str:
    return f"Resume text:\n\n{resume_text}\n\nExtract every verifiable claim."


class ExtractedClaim(BaseModel):
    claim_type: str = Field(description="One of: skill, employment, education, project, credential")
    claim_text: str = Field(description="Human-readable restatement of the claim")
    normalized_skill: str | None = Field(default=None, description="Lowercase canonical skill name, if applicable")
    asserted_years: float | None = None
    asserted_start: str | None = Field(default=None, description="YYYY-MM if applicable")
    asserted_end: str | None = Field(default=None, description="YYYY-MM if applicable, null if 'present'")
    asserted_org: str | None = None
    quoted_source_text: str = Field(description="Verbatim substring of the resume this was extracted from")


class ExtractedClaims(BaseModel):
    claims: list[ExtractedClaim]
