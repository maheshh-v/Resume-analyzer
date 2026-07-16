from pydantic import BaseModel, Field

PROMPT_VERSION = "interview_question.v1"

SYSTEM_PROMPT = """You are an experienced senior engineer conducting a technical screening \
interview. You write ONE question that tests whether a candidate's specific claim is real.

Rules:
- Ground the question in the most specific artifact available (a line from their resume, or \
a file/commit from their GitHub if provided). Reference it concretely.
- Ask for a DECISION and its TRADEOFF, never a definition. Bad: "What is Docker?" Good: \
"You mention using multi-stage Docker builds — walk me through a case where that saved you \
meaningfully, and what you gave up to get it."
- Never ask something a generic AI chatbot with no knowledge of this candidate could answer \
just as well. The question must require having actually done the specific thing claimed.
- Write the rubric BEFORE you'd see any answer: what would someone who really did this \
mention (specific numbers, named tools, a failure mode, a tradeoff)? What's the generic, \
fluent-but-empty answer that a bluffer gives?
- Keep the question to 1-3 sentences. No preamble like "Great, let's dive in."""


def build_user_prompt(*, claim_text: str, artifact_context: str | None, requirement_context: str) -> str:
    artifact_block = f"\nArtifact context (from their GitHub, if relevant):\n{artifact_context}\n" if artifact_context else ""
    return (
        f"Job requirement this targets: {requirement_context}\n"
        f"Candidate's claim (unverified so far): {claim_text}\n"
        f"{artifact_block}\n"
        "Write one grounded interview question and its rubric."
    )


def build_followup_user_prompt(
    *, original_question: str, answer_text: str, rubric_must_mention: list[str]
) -> str:
    missed = ", ".join(rubric_must_mention) if rubric_must_mention else "specific details"
    return (
        f"Original question: {original_question}\n"
        f"Candidate's answer: {answer_text}\n"
        f"The answer was vague and did not clearly cover: {missed}\n\n"
        "Write ONE deeper follow-up probe (not a full new topic) that pushes for the specific "
        "detail this answer was missing. Keep it to the same claim."
    )


class QuestionDraft(BaseModel):
    question_text: str
    rubric_must_mention: list[str] = Field(description="Specific things a real practitioner would mention")
    rubric_bluffer_tells: list[str] = Field(description="Signs of a generic/fluent-but-empty answer")
    rationale: str = Field(description="One sentence: why this question, shown to the recruiter")
