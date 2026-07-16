from app.pipeline.match import ClaimLike, RequirementLike, match_claims_to_requirements


def test_gap_when_no_claim_matches():
    reqs = [RequirementLike(id="r1", skill="Kubernetes", normalized_skill="kubernetes", importance="must_have", min_years=None)]
    matches = match_claims_to_requirements(reqs, [])
    assert matches[0].status == "gap"


def test_matched_when_claim_present_no_years_required():
    reqs = [RequirementLike(id="r1", skill="Docker", normalized_skill="docker", importance="nice_to_have", min_years=None)]
    claims = [ClaimLike(id="c1", claim_text="3 years Docker", normalized_skill="docker", asserted_years=3)]
    matches = match_claims_to_requirements(reqs, claims)
    assert matches[0].status == "matched"
    assert matches[0].matching_claim_ids == ["c1"]


def test_matched_when_years_meet_bar():
    reqs = [RequirementLike(id="r1", skill="TensorFlow", normalized_skill="tensorflow", importance="must_have", min_years=3)]
    claims = [ClaimLike(id="c1", claim_text="4 years TensorFlow", normalized_skill="tensorflow", asserted_years=4)]
    matches = match_claims_to_requirements(reqs, claims)
    assert matches[0].status == "matched"


def test_partial_when_years_below_bar():
    reqs = [RequirementLike(id="r1", skill="TensorFlow", normalized_skill="tensorflow", importance="must_have", min_years=3)]
    claims = [ClaimLike(id="c1", claim_text="1 year TensorFlow", normalized_skill="tensorflow", asserted_years=1)]
    matches = match_claims_to_requirements(reqs, claims)
    assert matches[0].status == "partial"


def test_picks_best_years_among_multiple_matching_claims():
    reqs = [RequirementLike(id="r1", skill="Python", normalized_skill="python", importance="must_have", min_years=3)]
    claims = [
        ClaimLike(id="c1", claim_text="1 year Python at side project", normalized_skill="python", asserted_years=1),
        ClaimLike(id="c2", claim_text="4 years Python at Acme", normalized_skill="python", asserted_years=4),
    ]
    matches = match_claims_to_requirements(reqs, claims)
    assert matches[0].status == "matched"
    assert set(matches[0].matching_claim_ids) == {"c1", "c2"}
