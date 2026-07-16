"""The citation validation guardrail.

A hallucinated citation is a product-ending bug: if the report says "verified — see this
span" and the span doesn't actually say that, we've automated manufacturing false confidence
about a real person's career. So every claim's source span is checked here BEFORE it's
allowed to exist, and every piece of evidence's snippet is checked before the evidence row
is written. Failure never raises into a 500 — it degrades the row to invalid/unverified.
This function is the one thing in the whole codebase that is not allowed to be "mostly right."
"""


def span_is_valid(text: str, start: int, end: int) -> bool:
    if start < 0 or end <= start or end > len(text):
        return False
    return True


def resolve_span(text: str, start: int, end: int) -> str | None:
    if not span_is_valid(text, start, end):
        return None
    return text[start:end]


def snippet_is_literal_substring(document_text: str, snippet: str) -> bool:
    """Used for artifact_snippet validation: the quoted evidence text must literally
    appear in the source document/artifact, not be a paraphrase the model invented."""
    if not snippet or not snippet.strip():
        return False
    return snippet in document_text


def find_span_for_text(document_text: str, needle: str) -> tuple[int, int] | None:
    """Best-effort: locate a literal occurrence of `needle` in `document_text` and return
    its span. Used to convert a model's quoted claim text into a verifiable span when the
    model didn't (or couldn't) return exact offsets itself."""
    if not needle or not needle.strip():
        return None
    idx = document_text.find(needle)
    if idx == -1:
        return None
    return idx, idx + len(needle)
