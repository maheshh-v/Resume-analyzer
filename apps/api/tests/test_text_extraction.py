import io

import fitz
import pytest

from app.pipeline.text_extraction import extract_text_from_pdf


def _make_pdf_bytes(pages: list[str]) -> bytes:
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


def test_extracts_text_and_page_offsets_for_multi_page_pdf():
    pdf_bytes = _make_pdf_bytes(["Page one content", "Page two content"])
    result = extract_text_from_pdf(io.BytesIO(pdf_bytes))

    assert "Page one content" in result.full_text
    assert "Page two content" in result.full_text
    assert len(result.page_offsets) == 2

    for start, end in result.page_offsets:
        assert 0 <= start <= end <= len(result.full_text)


def test_raises_on_empty_pdf():
    pdf_bytes = _make_pdf_bytes([""])
    with pytest.raises(ValueError):
        extract_text_from_pdf(io.BytesIO(pdf_bytes))
