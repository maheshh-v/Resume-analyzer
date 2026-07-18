"""Branded PDF rendering for the white-label report, using PyMuPDF (already a dependency for
resume text extraction — no new package). Renders the mechanical HiringSummary: coverage,
requirement matrix, conflicts, and follow-ups, with an org name + optional logo slot.

Like the on-screen report, it states plainly that it records evidence and is not a hiring
recommendation.
"""

from __future__ import annotations

import logging

import fitz

logger = logging.getLogger(__name__)

_LEFT = 50
_TOP = 60
_BOTTOM = 780
_MAX_CHARS = 95


def _truncate(text: str) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= _MAX_CHARS else text[: _MAX_CHARS - 1] + "…"


def render_report_pdf(*, summary: dict, org_name: str, logo_bytes: bytes | None = None) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    y = _TOP

    if logo_bytes:
        try:
            page.insert_image(fitz.Rect(430, 28, 560, 88), stream=logo_bytes)
        except Exception:  # a bad logo must never break report generation
            logger.info("pdf: could not render logo for %s", org_name)

    def write(text: str, *, size: int = 11, gap: int = 16, bold: bool = False) -> None:
        nonlocal y, page
        if y > _BOTTOM:
            page = doc.new_page()
            y = _TOP
        page.insert_text((_LEFT, y), _truncate(text), fontsize=size, fontname="hebo" if bold else "helv")
        y += gap

    write(org_name or "RecruitX", size=17, gap=26, bold=True)
    write("Evidence Verification Report", size=13, gap=24, bold=True)
    write(
        f"Evidence coverage: {summary.get('evidence_coverage_count', 0)} of "
        f"{summary.get('evidence_coverage_total', 0)} requirements corroborated.",
        gap=22,
    )

    write("Requirements", size=12, gap=18, bold=True)
    for row in summary.get("matrix", []):
        write(
            f"• {row.get('skill')}  [{row.get('importance')}]  "
            f"match: {row.get('match_status')}  ·  verdict: {row.get('best_verdict')}"
        )
    if not summary.get("matrix"):
        write("• (no requirements matched)")

    conflicts = summary.get("conflicts", [])
    if conflicts:
        y += 6
        write("Conflicts flagged", size=12, gap=18, bold=True)
        for c in conflicts:
            write(f"• {c}")

    followups = summary.get("suggested_followups", [])
    if followups:
        y += 6
        write("Suggested follow-ups", size=12, gap=18, bold=True)
        for f in followups[:12]:
            write(f"• {f}")

    y += 12
    write(
        "This report records evidence about documents. It is not a hiring recommendation; "
        "a human decides.",
        size=9,
        gap=12,
    )

    data = doc.tobytes()
    doc.close()
    return data
