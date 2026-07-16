"""Pure adaptive-interview state machine — no LLM calls, no I/O, fully unit-testable.

For each targeted claim: ask a base question, then evaluate. A strong answer resolves the
claim and advances. A weak answer gets exactly one follow-up probe before advancing anyway —
`MAX_DEPTH` caps how deep any single claim can go, so one bad topic can never consume the
candidate's whole interview budget. Callers (the interviews router) hold the LLM calls;
this module only decides what happens next given what's already on the record.
"""

from dataclasses import dataclass

MAX_DEPTH = 3


@dataclass
class ClaimTarget:
    claim_id: str
    requirement_id: str
    claim_text: str
    requirement_label: str


@dataclass
class AskedQuestion:
    claim_id: str
    depth: int
    specificity_verdict: str | None  # None = asked but not yet answered/evaluated


@dataclass
class NextAction:
    kind: str  # "ask_base" | "ask_followup" | "done" | "await_answer"
    claim: ClaimTarget | None = None
    depth: int = 0
    previous_question: AskedQuestion | None = None


def _is_resolved(questions_for_claim: list[AskedQuestion]) -> bool:
    if not questions_for_claim:
        return False
    last = questions_for_claim[-1]
    if last.specificity_verdict is None:
        return False  # still waiting on an answer — caller shouldn't be asking for next action yet
    return last.specificity_verdict == "strong" or last.depth >= MAX_DEPTH


def decide_next_action(targets: list[ClaimTarget], asked: list[AskedQuestion]) -> NextAction:
    for target in targets:
        questions_for_claim = [a for a in asked if a.claim_id == target.claim_id]

        if not questions_for_claim:
            return NextAction(kind="ask_base", claim=target, depth=0)

        last = questions_for_claim[-1]
        if last.specificity_verdict is None:
            return NextAction(kind="await_answer", claim=target, depth=last.depth, previous_question=last)

        if _is_resolved(questions_for_claim):
            continue

        return NextAction(
            kind="ask_followup",
            claim=target,
            depth=last.depth + 1,
            previous_question=last,
        )

    return NextAction(kind="done")
