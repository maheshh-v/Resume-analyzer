import pytest

from app.llm.client import LLMClient
from app.llm.prompts.claim_extraction import ExtractedClaim, ExtractedClaims
from app.llm.provider import FakeProvider
from app.pipeline.extract_claims import extract_claims

RESUME_TEXT = (
    "Jane Doe\nSenior ML Engineer\n\n"
    "Experience\nAcme Inc, 2021-01 to 2023-01: Led ML platform. Built TensorFlow pipelines for fraud detection.\n"
    "Skills: 4 years TensorFlow, Python, Docker.\n"
)


@pytest.mark.asyncio
async def test_valid_claims_with_real_spans_are_accepted():
    provider = FakeProvider(
        responses=[
            ExtractedClaims(
                claims=[
                    ExtractedClaim(
                        claim_type="employment",
                        claim_text="Led ML platform at Acme",
                        asserted_org="Acme Inc",
                        asserted_start="2021-01",
                        asserted_end="2023-01",
                        quoted_source_text="Led ML platform.",
                    ),
                    ExtractedClaim(
                        claim_type="skill",
                        claim_text="4 years TensorFlow",
                        normalized_skill="TensorFlow",
                        asserted_years=4,
                        quoted_source_text="4 years TensorFlow",
                    ),
                ]
            )
        ]
    )
    result = await extract_claims(RESUME_TEXT, LLMClient(provider=provider))

    assert result.total_extracted == 2
    assert result.discarded_uncitable == 0
    assert len(result.claims) == 2
    tf_claim = next(c for c in result.claims if c.claim_type == "skill")
    assert RESUME_TEXT[tf_claim.source_span_start : tf_claim.source_span_end] == "4 years TensorFlow"
    assert tf_claim.normalized_skill == "tensorflow"


@pytest.mark.asyncio
async def test_hallucinated_claim_is_discarded_not_saved():
    provider = FakeProvider(
        responses=[
            ExtractedClaims(
                claims=[
                    ExtractedClaim(
                        claim_type="skill",
                        claim_text="Expert in Kubernetes",
                        normalized_skill="kubernetes",
                        quoted_source_text="This text does not appear anywhere in the resume",
                    )
                ]
            )
        ]
    )
    result = await extract_claims(RESUME_TEXT, LLMClient(provider=provider))

    assert result.total_extracted == 1
    assert result.discarded_uncitable == 1
    assert result.claims == []
    assert result.hallucinated_citation_rate == 1.0


@pytest.mark.asyncio
async def test_invalid_claim_type_is_discarded():
    provider = FakeProvider(
        responses=[
            ExtractedClaims(
                claims=[
                    ExtractedClaim(claim_type="not_a_real_type", claim_text="???", quoted_source_text="Jane Doe")
                ]
            )
        ]
    )
    result = await extract_claims(RESUME_TEXT, LLMClient(provider=provider))
    assert result.claims == []
    assert result.discarded_uncitable == 1
