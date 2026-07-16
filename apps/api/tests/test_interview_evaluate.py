from app.pipeline.interview.evaluate import compute_behavioral_flags, normalize_answer_text


def test_normalize_answer_text_collapses_whitespace():
    assert normalize_answer_text("  hello\n\nworld   foo  ") == "hello world foo"


def test_behavioral_flags_empty_for_normal_answer():
    flags = compute_behavioral_flags(time_to_first_keystroke_ms=3000, total_time_ms=45000, paste_event_count=0)
    assert flags == []


def test_behavioral_flags_include_paste_note():
    flags = compute_behavioral_flags(time_to_first_keystroke_ms=1000, total_time_ms=30000, paste_event_count=2)
    assert len(flags) == 1
    assert "paste" in flags[0].lower()


def test_behavioral_flags_include_fast_answer_note():
    flags = compute_behavioral_flags(time_to_first_keystroke_ms=100, total_time_ms=2000, paste_event_count=0)
    assert any("fast" in f.lower() for f in flags)


def test_behavioral_flags_are_advisory_only_never_a_verdict():
    flags = compute_behavioral_flags(time_to_first_keystroke_ms=100, total_time_ms=1000, paste_event_count=5)
    joined = " ".join(flags).lower()
    assert "reject" not in joined
    assert "fail" not in joined
