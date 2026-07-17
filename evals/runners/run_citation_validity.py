"""Runner: citation validity — the guardrail's core promise, measured end to end.

The product's central safety claim is that every accepted claim carries a source citation that
*actually resolves to the quoted text* — no hallucinated spans. This runner replays each case,
takes every claim the pipeline accepted, and independently re-checks (using `citation.py`'s own
`resolve_span` + `snippet_is_literal_substring`) that its stored span resolves to a literal
substring of the resume. The target is 100%: a single failure here is a product-ending bug.

Recorded connector evidence carries `artifact_url`s. Those are validated live (URL 200 + literal
snippet) by the Phase 3 connector tests against recorded fixtures — not here, because the golden
evidence URLs are synthetic. This runner reports how many URL citations it saw so the number is
never mistaken for a live-resolution result.

Run:  python -m evals.runners.run_citation_validity
"""

from __future__ import annotations

import argparse
import asyncio
import json

from evals.harness.dataset import DEFAULT_DATASET, DEFAULT_FIXTURE_DIR, LLMFixture, load_dataset
from evals.harness.metrics import rate
from evals.harness.pipeline import check_claim_citation, run_extraction

METRIC_NAME = "citation_validity"


async def run(dataset_path=DEFAULT_DATASET, fixture_dir=DEFAULT_FIXTURE_DIR) -> dict:
    cases = load_dataset(dataset_path)
    all_results: list[bool] = []
    url_citations_seen = 0
    per_case: list[dict] = []

    for case in cases:
        fixture = LLMFixture.load(case.id, fixture_dir)
        extraction = await run_extraction(fixture, case.resume_text)
        results = [check_claim_citation(case.resume_text, c) for c in extraction.claims]
        all_results.extend(results)
        url_citations_seen += len(fixture.evidence)
        per_case.append(
            {
                "id": case.id,
                "accepted_claims": len(extraction.claims),
                "valid_span_citations": sum(1 for r in results if r),
                "invalid_span_citations": sum(1 for r in results if not r),
                "span_validity": round(rate(results), 4),
            }
        )

    return {
        "metric": METRIC_NAME,
        "case_count": len(cases),
        "overall": {
            "span_citation_validity": round(rate(all_results), 4),
            "accepted_claims_checked": len(all_results),
            "invalid_span_citations": sum(1 for r in all_results if not r),
            "url_citations_seen": url_citations_seen,
            "url_citations_resolved_live": 0,
            "note": "URL resolution is exercised by the connector tests, not the offline golden run.",
        },
        "per_case": per_case,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--fixtures", default=str(DEFAULT_FIXTURE_DIR))
    args = parser.parse_args()
    result = asyncio.run(run(args.dataset, args.fixtures))
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
