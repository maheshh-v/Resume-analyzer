from dataclasses import dataclass

from app.llm.client import LLMClient
from app.llm.prompts.interview_question import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    QuestionDraft,
    build_followup_user_prompt,
    build_user_prompt,
)
from app.pipeline.interview.state_machine import ClaimTarget


@dataclass
class GeneratedQuestion:
    question_text: str
    rubric: dict
    rationale: str
    model: str
    prompt_version: str


async def generate_base_question(
    *, claim: ClaimTarget, artifact_context: str | None, llm: LLMClient
) -> GeneratedQuestion:
    result = await llm.generate_structured(
        system=SYSTEM_PROMPT,
        user=build_user_prompt(
            claim_text=claim.claim_text,
            artifact_context=artifact_context,
            requirement_context=claim.requirement_label,
        ),
        schema=QuestionDraft,
        prompt_version=PROMPT_VERSION,
        trace_name="interview_generate_base",
    )
    draft = result.data
    return GeneratedQuestion(
        question_text=draft.question_text,
        rubric={"must_mention": draft.rubric_must_mention, "bluffer_tells": draft.rubric_bluffer_tells},
        rationale=draft.rationale,
        model=result.model,
        prompt_version=result.prompt_version,
    )


async def generate_followup_question(
    *, original_question_text: str, answer_text: str, rubric_must_mention: list[str], llm: LLMClient
) -> GeneratedQuestion:
    result = await llm.generate_structured(
        system=SYSTEM_PROMPT,
        user=build_followup_user_prompt(
            original_question=original_question_text,
            answer_text=answer_text,
            rubric_must_mention=rubric_must_mention,
        ),
        schema=QuestionDraft,
        prompt_version=PROMPT_VERSION,
        trace_name="interview_generate_followup",
    )
    draft = result.data
    return GeneratedQuestion(
        question_text=draft.question_text,
        rubric={"must_mention": draft.rubric_must_mention, "bluffer_tells": draft.rubric_bluffer_tells},
        rationale=draft.rationale,
        model=result.model,
        prompt_version=result.prompt_version,
    )
