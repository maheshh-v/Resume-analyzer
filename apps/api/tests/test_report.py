from app.pipeline.evidence.consistency import ConsistencyFinding
from app.pipeline.match import RequirementMatch
from app.pipeline.report import EvidenceRow, QAExchange, build_hiring_summary


def test_evidence_coverage_counts_only_requirements_with_evidence():
    matches = [
        RequirementMatch(requirement_id="r1", skill="Python", importance="must_have", status="matched", matching_claim_ids=["c1"]),
        RequirementMatch(requirement_id="r2", skill="Kubernetes", importance="must_have", status="gap"),
    ]
    evidence = [EvidenceRow(claim_id="c1", source_type="github", verdict="verified", summary="found in repo", artifact_url="https://github.com/x")]

    summary = build_hiring_summary(
        matches=matches, evidence=evidence, consistency_findings=[], transcript=[], claim_text_by_id={"c1": "5 years Python"}
    )

    assert summary.evidence_coverage_total == 2
    assert summary.evidence_coverage_count == 1
    assert len(summary.verified_skills) == 1
    assert summary.verified_skills[0].skill == "Python"


def test_gap_requirements_appear_in_weak_areas():
    matches = [RequirementMatch(requirement_id="r1", skill="Kubernetes", importance="must_have", status="gap")]
    summary = build_hiring_summary(matches=matches, evidence=[], consistency_findings=[], transcript=[], claim_text_by_id={})
    assert any("Kubernetes" in w for w in summary.weak_areas)


def test_must_have_unverified_lands_in_needs_manual_verification():
    matches = [RequirementMatch(requirement_id="r1", skill="Kubernetes", importance="must_have", status="matched", matching_claim_ids=["c1"])]
    summary = build_hiring_summary(matches=matches, evidence=[], consistency_findings=[], transcript=[], claim_text_by_id={"c1": "2 years k8s"})
    assert len(summary.needs_manual_verification) == 1
    assert any("Kubernetes" in f for f in summary.suggested_followups)


def test_no_score_field_exists_on_summary_object():
    # Structural guardrail: the report has no score/rank concept anywhere.
    summary = build_hiring_summary(matches=[], evidence=[], consistency_findings=[], transcript=[], claim_text_by_id={})
    field_names = {f for f in summary.__dataclass_fields__}
    assert not any("score" in f.lower() or "rank" in f.lower() for f in field_names)


def test_consistency_findings_become_conflicts_and_followups():
    findings = [ConsistencyFinding(finding_type="date_overlap", claim_ids=["c1", "c2"], summary="Overlapping employment dates")]
    summary = build_hiring_summary(matches=[], evidence=[], consistency_findings=findings, transcript=[], claim_text_by_id={})
    assert summary.conflicts == ["Overlapping employment dates"]
    assert "Overlapping employment dates" in summary.suggested_followups


def test_weak_interview_answer_surfaces_as_followup():
    transcript = [
        QAExchange(depth=0, question_text="Walk me through your caching layer", rationale="probe", answer_text="idk", specificity_verdict="weak", specificity_notes="vague")
    ]
    summary = build_hiring_summary(matches=[], evidence=[], consistency_findings=[], transcript=transcript, claim_text_by_id={})
    assert any("caching layer" in f for f in summary.suggested_followups)
    assert summary.transcript == transcript


def test_contradicted_evidence_ranks_above_verified_for_best_verdict():
    matches = [RequirementMatch(requirement_id="r1", skill="Docker", importance="must_have", status="matched", matching_claim_ids=["c1"])]
    evidence = [
        EvidenceRow(claim_id="c1", source_type="github", verdict="verified", summary="found", artifact_url="https://x"),
        EvidenceRow(claim_id="c1", source_type="consistency", verdict="contradicted", summary="dates overlap", artifact_url=None),
    ]
    summary = build_hiring_summary(matches=matches, evidence=evidence, consistency_findings=[], transcript=[], claim_text_by_id={"c1": "3 years Docker"})
    assert summary.matrix[0].best_verdict == "contradicted"
