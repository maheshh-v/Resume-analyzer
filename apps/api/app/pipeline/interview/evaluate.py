import re
from dataclasses import dataclass

from app.llm.client import LLMClient
from app.llm.prompts.interview_evaluation import PROMPT_VERSION, SYSTEM_PROMPT, AnswerEvaluation, build_user_prompt

# Behavioral flags are FLAGS for human review only — never an auto-reject signal, never a
# score. See docs/ARCHITECTURE.md: a false accusation of cheating harms a real person.
_PASTE_FLAG_THRESHOLD = 1
_FAST_ANSWER_MS_THRESHOLD = 5_000


@dataclass
class EvaluationResult:
    specificity_verdict: str
    specificity_notes: str
    rubric_points_hit: list[str]
    rubric_points_missed: list[str]
    model: str
    prompt_version: str


async def evaluate_answer(
    *, question_text: str, rubric_must_mention: list[str], answer_text: str, llm: LLMClient
) -> EvaluationResult:
    result = await llm.generate_structured(
        system=SYSTEM_PROMPT,
        user=build_user_prompt(
            question_text=question_text, rubric_must_mention=rubric_must_mention, answer_text=answer_text
        ),
        schema=AnswerEvaluation,
        prompt_version=PROMPT_VERSION,
        trace_name="interview_evaluate_answer",
    )
    data = result.data
    verdict = data.specificity_verdict if data.specificity_verdict in ("strong", "weak") else "weak"
    return EvaluationResult(
        specificity_verdict=verdict,
        specificity_notes=data.specificity_notes,
        rubric_points_hit=data.rubric_points_hit,
        rubric_points_missed=data.rubric_points_missed,
        model=result.model,
        prompt_version=result.prompt_version,
    )


def compute_behavioral_flags(
    *, time_to_first_keystroke_ms: int | None, total_time_ms: int | None, paste_event_count: int
) -> list[str]:
    """Flags for human review only. Never used to auto-reject or to compute any verdict."""
    flags: list[str] = []
    if paste_event_count > _PASTE_FLAG_THRESHOLD:
        flags.append(f"{paste_event_count} paste events during this answer — worth a look, not a conclusion.")
    if total_time_ms is not None and total_time_ms < _FAST_ANSWER_MS_THRESHOLD:
        flags.append("Answer submitted unusually fast for the length of the question.")
    return flags


_WHITESPACE_RE = re.compile(r"\s+")


def normalize_answer_text(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text).strip()
