"""Bridge from the root-level eval harness into the real backend pipeline in `apps/api`.

The harness lives at the repo root but must exercise the *actual* production code — extraction,
the citation guardrail, the consistency checker — not a reimplementation of them, or the numbers
would be meaningless. This module puts `apps/api` on the import path and wraps the pipeline
stages so a runner can feed a recorded LLM fixture through them with zero network calls.

Nothing here calls a paid API. The LLM is always a FakeProvider seeded from the recorded
fixture, exactly as the backend's own test suite does it.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

# Fixed "now" so consistency checks that depend on open-ended ('present') employment are
# reproducible run-to-run instead of drifting with the wall clock.
EVAL_TODAY = date(2026, 1, 1)

_API_ROOT = Path(__file__).resolve().parents[2] / "apps" / "api"
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

# Imported after the path insert so `app.*` resolves. noqa: E402 (intentional late import).
from app.llm.client import LLMClient  # noqa: E402
from app.llm.provider import FakeProvider  # noqa: E402
from app.pipeline.citation import resolve_span, snippet_is_literal_substring  # noqa: E402
from app.pipeline.evidence.consistency import ConsistencyClaim, run_consistency_checks  # noqa: E402
from app.pipeline.extract_claims import ClaimExtractionResult, extract_claims  # noqa: E402

from .dataset import GoldenCase, LLMFixture  # noqa: E402
from .metrics import claim_key


def build_fake_client(extracted_claims: dict) -> LLMClient:
    """An LLMClient whose only provider is a FakeProvider queued with one recorded response.
    The injected-provider path in LLMClient disables the live fallback, so this can never reach
    the network even if env vars are set."""
    provider = FakeProvider(responses=[extracted_claims])
    return LLMClient(provider=provider)


async def run_extraction(fixture: LLMFixture, resume_text: str) -> ClaimExtractionResult:
    """Run the real `extract_claims` stage (citation guardrail included) over recorded output."""
    client = build_fake_client(fixture.extracted_claims)
    return await extract_claims(resume_text, client)


def predicted_verdicts(
    extraction: ClaimExtractionResult, fixture: LLMFixture
) -> dict[str, str]:
    """Reproduce the pipeline's per-claim verdict offline: consistency (pure Python, real) plus
    recorded external evidence. Priority mirrors orchestrate.py's intent — a contradiction is the
    strongest signal, then positive evidence, else the default 'unverified'."""
    consistency_inputs = [
        ConsistencyClaim(
            id=str(i),
            claim_type=c.claim_type,
            claim_text=c.claim_text,
            normalized_skill=c.normalized_skill,
            asserted_years=c.asserted_years,
            asserted_start=c.asserted_start,
            asserted_end=c.asserted_end,
            asserted_org=c.asserted_org,
        )
        for i, c in enumerate(extraction.claims)
    ]
    contradicted_ids = {
        cid
        for finding in run_consistency_checks(consistency_inputs, today=EVAL_TODAY)
        for cid in finding.claim_ids
    }

    verdicts: dict[str, str] = {}
    for i, claim in enumerate(extraction.claims):
        key = claim_key(claim.claim_text, claim.normalized_skill)
        if str(i) in contradicted_ids:
            verdicts[key] = "contradicted"
            continue
        match = next(
            (e for e in fixture.evidence if _evidence_matches(e.claim_key, claim, key)), None
        )
        verdicts[key] = match.verdict if match else "unverified"
    return verdicts


def _evidence_matches(evidence_key: str, claim, key: str) -> bool:
    from .metrics import keys_match

    evidence_key_norm = claim_key(evidence_key, evidence_key)
    return keys_match(evidence_key_norm, key) or (
        claim.normalized_skill is not None
        and keys_match(evidence_key_norm, claim_key(claim.normalized_skill, claim.normalized_skill))
    )


def predicted_claim_keys(extraction: ClaimExtractionResult) -> list[str]:
    return [claim_key(c.claim_text, c.normalized_skill) for c in extraction.claims]


def check_claim_citation(resume_text: str, claim) -> bool:
    """Re-verify, using the guardrail's OWN functions, that an accepted claim's stored span
    resolves to a real literal substring of the source. This is the one thing the product is
    not allowed to be 'mostly right' about, so the eval checks it independently of extraction."""
    resolved = resolve_span(resume_text, claim.source_span_start, claim.source_span_end)
    return resolved is not None and snippet_is_literal_substring(resume_text, resolved)
