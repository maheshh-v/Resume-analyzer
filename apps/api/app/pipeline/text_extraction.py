"""PDF text extraction with per-page character offsets into the concatenated text.

The offsets are what let a claim's source_span cite an exact location: given
(source_span_start, source_span_end), citation.py can resolve which page it's on and
validate that the span is a literal substring of the extracted text.
"""

from dataclasses import dataclass
from typing import BinaryIO

import fitz  # PyMuPDF


@dataclass
class ExtractedDocument:
    full_text: str
    page_offsets: list[list[int]]  # [[start, end), ...] one pair per page, into full_text


def extract_text_from_pdf(pdf_input: str | BinaryIO) -> ExtractedDocument:
    if isinstance(pdf_input, str):
        pdf_doc = fitz.open(pdf_input)
    else:
        pdf_doc = fitz.open("pdf", pdf_input.read())

    full_text = ""
    page_offsets: list[list[int]] = []
    try:
        for page in pdf_doc:
            page_text = page.get_text()
            start = len(full_text)
            full_text += page_text
            page_offsets.append([start, len(full_text)])
    finally:
        pdf_doc.close()

    if not full_text.strip():
        raise ValueError("No text found in PDF")

    return ExtractedDocument(full_text=full_text, page_offsets=page_offsets)
