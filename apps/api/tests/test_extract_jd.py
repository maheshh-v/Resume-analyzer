import pytest

from app.llm.client import LLMClient
from app.llm.prompts.jd_extraction import ExtractedRequirement, ExtractedRequirements
from app.llm.provider import FakeProvider
from app.pipeline.extract_jd import extract_job_requirements

JD_TEXT = "We need a Senior Backend Engineer.\nRequirements:\n- 3+ years of Python\n- Experience with Kubernetes"


@pytest.mark.asyncio
async def test_requirement_span_resolves_when_quote_is_exact():
    provider = FakeProvider(
        responses=[
            ExtractedRequirements(
                requirements=[
                    ExtractedRequirement(
                        skill="Python",
                        normalized_skill="Python",
                        category="technical",
                        importance="must_have",
                        min_years=3,
                        evidence_criteria="A repo or role using Python for 3+ years",
                        quoted_source_text="3+ years of Python",
                    )
                ]
            )
        ]
    )
    drafts = await extract_job_requirements(JD_TEXT, LLMClient(provider=provider))
    assert len(drafts) == 1
    draft = drafts[0]
    assert draft.normalized_skill == "python"
    assert draft.source_span_start is not None
    assert JD_TEXT[draft.source_span_start : draft.source_span_end] == "3+ years of Python"


@pytest.mark.asyncio
async def test_requirement_kept_even_when_quote_does_not_resolve():
    """Unlike claims, a JD requirement without a resolvable span is still kept — the
    recruiter reviews requirements before anything downstream runs, so a missing citation
    here is a UI nicety (no highlight) rather than a trust-critical failure."""
    provider = FakeProvider(
        responses=[
            ExtractedRequirements(
                requirements=[
                    ExtractedRequirement(
                        skill="Kubernetes",
                        normalized_skill="Kubernetes",
                        category="technical",
                        importance="nice_to_have",
                        min_years=None,
                        evidence_criteria="A repo using k8s manifests",
                        quoted_source_text="paraphrased, not an exact quote",
                    )
                ]
            )
        ]
    )
    drafts = await extract_job_requirements(JD_TEXT, LLMClient(provider=provider))
    assert len(drafts) == 1
    assert drafts[0].source_span_start is None
    assert drafts[0].skill == "Kubernetes"


@pytest.mark.asyncio
async def test_invalid_importance_defaults_to_nice_to_have():
    provider = FakeProvider(
        responses=[
            ExtractedRequirements(
                requirements=[
                    ExtractedRequirement(
                        skill="Python",
                        normalized_skill="python",
                        category="technical",
                        importance="super_critical",
                        min_years=None,
                        evidence_criteria="x",
                        quoted_source_text="Python",
                    )
                ]
            )
        ]
    )
    drafts = await extract_job_requirements(JD_TEXT, LLMClient(provider=provider))
    assert drafts[0].importance == "nice_to_have"
