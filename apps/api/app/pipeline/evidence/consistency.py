"""Free, universal, zero-LLM-cost internal-consistency checks.

Runs for every candidate regardless of whether they have a usable GitHub profile — this is
the evidence source that fills the recall gap GitHub leaves (most engineers' real work is
behind a firewall). Two deterministic checks for the MVP: overlapping employment claims, and
a claimed skill-years figure that exceeds the candidate's entire visible career span.

Ambiguity always degrades to no finding — a false "contradicted" can cost someone a job, so
this stays conservative by design (see docs/ARCHITECTURE.md section on evidence verdicts).
"""

from dataclasses import dataclass
from datetime import date


@dataclass
class ConsistencyClaim:
    id: str
    claim_type: str
    claim_text: str
    normalized_skill: str | None = None
    asserted_years: float | None = None
    asserted_start: str | None = None  # "YYYY-MM"
    asserted_end: str | None = None  # "YYYY-MM", None means "present"
    asserted_org: str | None = None


@dataclass
class ConsistencyFinding:
    finding_type: str  # date_overlap | years_exceed_career_span
    claim_ids: list[str]
    summary: str


def _parse_ym(value: str | None) -> date | None:
    if not value:
        return None
    try:
        year, month = value.split("-")
        return date(int(year), int(month), 1)
    except (ValueError, AttributeError):
        return None


def _overlap_months(a_start: date, a_end: date, b_start: date, b_end: date) -> int:
    latest_start = max(a_start, b_start)
    earliest_end = min(a_end, b_end)
    if latest_start >= earliest_end:
        return 0
    return (earliest_end.year - latest_start.year) * 12 + (earliest_end.month - latest_start.month)


def check_date_overlaps(claims: list[ConsistencyClaim], today: date | None = None) -> list[ConsistencyFinding]:
    today = today or date.today()
    employment = []
    for c in claims:
        if c.claim_type != "employment":
            continue
        start = _parse_ym(c.asserted_start)
        if start is None:
            continue
        end = _parse_ym(c.asserted_end) or today
        employment.append((c, start, end))

    findings: list[ConsistencyFinding] = []
    for i in range(len(employment)):
        for j in range(i + 1, len(employment)):
            claim_a, a_start, a_end = employment[i]
            claim_b, b_start, b_end = employment[j]
            overlap = _overlap_months(a_start, a_end, b_start, b_end)
            # Ignore small overlaps (<2mo) — common for legitimate transition periods.
            if overlap >= 2:
                findings.append(
                    ConsistencyFinding(
                        finding_type="date_overlap",
                        claim_ids=[claim_a.id, claim_b.id],
                        summary=(
                            f"'{claim_a.claim_text}' and '{claim_b.claim_text}' overlap by "
                            f"~{overlap} months. Worth asking about."
                        ),
                    )
                )
    return findings


def check_years_exceed_career_span(
    claims: list[ConsistencyClaim], today: date | None = None
) -> list[ConsistencyFinding]:
    today = today or date.today()
    employment_spans = []
    for c in claims:
        if c.claim_type != "employment":
            continue
        start = _parse_ym(c.asserted_start)
        if start is None:
            continue
        end = _parse_ym(c.asserted_end) or today
        employment_spans.append((start, end))

    if not employment_spans:
        return []

    career_start = min(s for s, _ in employment_spans)
    career_end = max(e for _, e in employment_spans)
    career_years = (career_end.year - career_start.year) + (career_end.month - career_start.month) / 12

    findings: list[ConsistencyFinding] = []
    for c in claims:
        if c.claim_type != "skill" or c.asserted_years is None:
            continue
        # Half-year buffer: skill practice can predate a first *listed* job (side projects, school).
        if c.asserted_years > career_years + 0.5:
            findings.append(
                ConsistencyFinding(
                    finding_type="years_exceed_career_span",
                    claim_ids=[c.id],
                    summary=(
                        f"'{c.claim_text}' claims {c.asserted_years:g} years, but the visible "
                        f"career span is only ~{career_years:.1f} years."
                    ),
                )
            )
    return findings


def run_consistency_checks(claims: list[ConsistencyClaim], today: date | None = None) -> list[ConsistencyFinding]:
    return check_date_overlaps(claims, today) + check_years_exceed_career_span(claims, today)
