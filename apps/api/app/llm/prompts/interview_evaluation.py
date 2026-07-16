from pydantic import BaseModel, Field

PROMPT_VERSION = "interview_evaluation.v1"

SYSTEM_PROMPT = """You evaluate one interview answer against a rubric written before the \
answer existed. Score CONTENT only — never how the answer is phrased, its tone, grammar, or \
fluency. Fluent-but-generic is exactly the failure mode you're looking for: AI-generated \
text is reliably fluent and reliably non-specific.

A "strong" answer names specific numbers, tools, timeframes, or a concrete failure mode / \
tradeoff that only someone who actually did the thing would know. A "weak" answer is vague, \
generic, textbook-definition-shaped, or dodges the specific question asked.

Be decisive. Most real answers to a good grounded question are strong; most bluffed answers \
are weak. Do not be lenient just because the answer is articulate."""


def build_user_prompt(*, question_text: str, rubric_must_mention: list[str], answer_text: str) -> str:
    rubric = "\n".join(f"- {item}" for item in rubric_must_mention) or "(no explicit rubric items)"
    return (
        f"Question: {question_text}\n\n"
        f"What a real practitioner would likely mention:\n{rubric}\n\n"
        f"Candidate's answer:\n{answer_text}\n\n"
        "Evaluate this answer."
    )


class AnswerEvaluation(BaseModel):
    specificity_verdict: str = Field(description="One of: strong, weak")
    specificity_notes: str = Field(description="One or two sentences explaining the verdict, shown to the recruiter")
    rubric_points_hit: list[str] = Field(default_factory=list)
    rubric_points_missed: list[str] = Field(default_factory=list)
