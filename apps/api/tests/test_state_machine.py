from app.pipeline.interview.state_machine import MAX_DEPTH, AskedQuestion, ClaimTarget, decide_next_action

TARGETS = [
    ClaimTarget(claim_id="c1", requirement_id="r1", claim_text="4 years TensorFlow", requirement_label="TensorFlow"),
    ClaimTarget(claim_id="c2", requirement_id="r2", claim_text="Docker in prod", requirement_label="Docker"),
]


def test_first_call_asks_base_question_for_first_target():
    action = decide_next_action(TARGETS, [])
    assert action.kind == "ask_base"
    assert action.claim.claim_id == "c1"
    assert action.depth == 0


def test_awaits_answer_when_question_asked_but_not_evaluated():
    asked = [AskedQuestion(claim_id="c1", depth=0, specificity_verdict=None)]
    action = decide_next_action(TARGETS, asked)
    assert action.kind == "await_answer"
    assert action.claim.claim_id == "c1"


def test_strong_answer_advances_to_next_claim():
    asked = [AskedQuestion(claim_id="c1", depth=0, specificity_verdict="strong")]
    action = decide_next_action(TARGETS, asked)
    assert action.kind == "ask_base"
    assert action.claim.claim_id == "c2"


def test_weak_answer_triggers_one_followup():
    asked = [AskedQuestion(claim_id="c1", depth=0, specificity_verdict="weak")]
    action = decide_next_action(TARGETS, asked)
    assert action.kind == "ask_followup"
    assert action.claim.claim_id == "c1"
    assert action.depth == 1


def test_advances_after_hitting_max_depth_even_if_weak():
    asked = [AskedQuestion(claim_id="c1", depth=d, specificity_verdict="weak") for d in range(MAX_DEPTH + 1)]
    action = decide_next_action(TARGETS, asked)
    assert action.kind == "ask_base"
    assert action.claim.claim_id == "c2"


def test_done_when_all_targets_resolved():
    asked = [
        AskedQuestion(claim_id="c1", depth=0, specificity_verdict="strong"),
        AskedQuestion(claim_id="c2", depth=0, specificity_verdict="strong"),
    ]
    action = decide_next_action(TARGETS, asked)
    assert action.kind == "done"


def test_never_exceeds_max_depth():
    # Simulate an unbroken chain of weak answers on claim c1 — depth must never exceed MAX_DEPTH.
    asked: list[AskedQuestion] = []
    for _ in range(MAX_DEPTH + 2):
        action = decide_next_action(TARGETS, asked)
        if action.kind != "ask_followup" and action.claim and action.claim.claim_id != "c1":
            break
        assert action.depth <= MAX_DEPTH
        asked.append(AskedQuestion(claim_id="c1", depth=action.depth, specificity_verdict="weak"))
