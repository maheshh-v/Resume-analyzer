from app.pipeline.citation import find_span_for_text, snippet_is_literal_substring, span_is_valid


def test_span_is_valid_accepts_in_range():
    assert span_is_valid("hello world", 0, 5) is True


def test_span_is_valid_rejects_out_of_range():
    assert span_is_valid("hello world", -1, 5) is False
    assert span_is_valid("hello world", 5, 5) is False
    assert span_is_valid("hello world", 0, 999) is False


def test_find_span_for_text_locates_literal_substring():
    text = "Led ML platform at Acme, 2021-2023. Built TensorFlow pipelines."
    span = find_span_for_text(text, "Built TensorFlow pipelines.")
    assert span is not None
    start, end = span
    assert text[start:end] == "Built TensorFlow pipelines."


def test_find_span_for_text_returns_none_for_hallucinated_text():
    text = "Led ML platform at Acme, 2021-2023."
    assert find_span_for_text(text, "Something not in the document") is None


def test_find_span_for_text_returns_none_for_empty_needle():
    assert find_span_for_text("some text", "") is None


def test_snippet_is_literal_substring():
    assert snippet_is_literal_substring("the quick brown fox", "quick brown") is True
    assert snippet_is_literal_substring("the quick brown fox", "slow red fox") is False
    assert snippet_is_literal_substring("the quick brown fox", "") is False
