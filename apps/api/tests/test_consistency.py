from datetime import date

from app.pipeline.evidence.consistency import ConsistencyClaim, check_date_overlaps, check_years_exceed_career_span


def test_no_findings_for_clean_career():
    claims = [
        ConsistencyClaim(id="c1", claim_type="employment", claim_text="Acme 2019-2021", asserted_start="2019-01", asserted_end="2021-01", asserted_org="Acme"),
        ConsistencyClaim(id="c2", claim_type="employment", claim_text="Beta 2021-2023", asserted_start="2021-02", asserted_end="2023-01", asserted_org="Beta"),
    ]
    assert check_date_overlaps(claims) == []


def test_detects_overlapping_employment():
    claims = [
        ConsistencyClaim(id="c1", claim_type="employment", claim_text="Led ML platform at Acme, 2021-2023", asserted_start="2021-01", asserted_end="2023-01", asserted_org="Acme"),
        ConsistencyClaim(id="c2", claim_type="employment", claim_text="MS Stanford, 2022-2024 full-time", asserted_start="2022-01", asserted_end="2024-01", asserted_org="Stanford"),
    ]
    findings = check_date_overlaps(claims)
    assert len(findings) == 1
    assert findings[0].finding_type == "date_overlap"
    assert set(findings[0].claim_ids) == {"c1", "c2"}


def test_ignores_small_transition_overlap():
    claims = [
        ConsistencyClaim(id="c1", claim_type="employment", claim_text="Acme", asserted_start="2020-01", asserted_end="2021-06", asserted_org="Acme"),
        ConsistencyClaim(id="c2", claim_type="employment", claim_text="Beta", asserted_start="2021-07", asserted_end="2022-01", asserted_org="Beta"),
    ]
    assert check_date_overlaps(claims) == []


def test_ignores_non_employment_claims():
    claims = [
        ConsistencyClaim(id="c1", claim_type="skill", claim_text="Python", normalized_skill="python", asserted_years=5),
        ConsistencyClaim(id="c2", claim_type="project", claim_text="Built a thing"),
    ]
    assert check_date_overlaps(claims) == []


def test_years_within_career_span_is_fine():
    today = date(2026, 1, 1)
    claims = [
        ConsistencyClaim(id="c1", claim_type="employment", claim_text="Acme", asserted_start="2020-01", asserted_end=None, asserted_org="Acme"),
        ConsistencyClaim(id="c2", claim_type="skill", claim_text="4 years TensorFlow", normalized_skill="tensorflow", asserted_years=4),
    ]
    assert check_years_exceed_career_span(claims, today=today) == []


def test_years_exceeding_career_span_flagged():
    today = date(2023, 1, 1)
    claims = [
        ConsistencyClaim(id="c1", claim_type="employment", claim_text="Acme, 2021-2023", asserted_start="2021-01", asserted_end="2023-01", asserted_org="Acme"),
        ConsistencyClaim(id="c2", claim_type="skill", claim_text="Kubernetes, 5 years", normalized_skill="kubernetes", asserted_years=5),
    ]
    findings = check_years_exceed_career_span(claims, today=today)
    assert len(findings) == 1
    assert findings[0].finding_type == "years_exceed_career_span"
    assert findings[0].claim_ids == ["c2"]


def test_no_findings_with_no_employment_history():
    claims = [ConsistencyClaim(id="c1", claim_type="skill", claim_text="Python", normalized_skill="python", asserted_years=10)]
    assert check_years_exceed_career_span(claims) == []
