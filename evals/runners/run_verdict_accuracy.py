"""Runner: verdict accuracy + fabrication safety.

For each ground-truth claim we ask: did the pipeline end up treating it as verified, and does
that match what a human said should happen? Predictions come from the real consistency checker
(pure Python) plus recorded connector evidence — exactly the signals orchestrate.py wires up.

Two numbers matter, and the second matters more:
  - verdict_match_rate: fraction of claims whose verified/not-verified outcome matches ground truth.
  - fabrication_safety_rate: of the PLANTED LIES, the fraction that did NOT end up verified. This
    is the number that must be 1.0 — a fabricated claim marked 'verified' is the exact failure the
    product exists to prevent. Any such case is listed explicitly.

Run:  python -m evals.runners.run_verdict_accuracy
"""

from __future__ import annotations

import argparse
import asyncio
import json

from evals.harness.dataset import DEFAULT_DATASET, DEFAULT_FIXTURE_DIR, LLMFixture, load_dataset
from evals.harness.metrics import claim_key, keys_match, rate
from evals.harness.pipeline import predicted_verdicts, run_extraction

METRIC_NAME = "verdict_accuracy"


def _verdict_for(truth_key: str, verdicts: dict[str, str]) -> str:
    """Look up the pipeline's verdict for a ground-truth claim. A claim the model never
    extracted has no verdict at all, which is exactly 'unverified' — absence never verifies."""
    for pred_key, verdict in verdicts.items():
        if keys_match(truth_key, pred_key):
            return verdict
    return "unverified"


async def run(dataset_path=DEFAULT_DATASET, fixture_dir=DEFAULT_FIXTURE_DIR) -> dict:
    cases = load_dataset(dataset_path)
    match_flags: list[bool] = []
    fabrication_safe_flags: list[bool] = []
    false_verifications: list[dict] = []
    per_case: list[dict] = []

    for case in cases:
        fixture = LLMFixture.load(case.id, fixture_dir)
        extraction = await run_extraction(fixture, case.resume_text)
        verdicts = predicted_verdicts(extraction, fixture)

        case_flags: list[bool] = []
        for gt in case.ground_truth_claims:
            truth_key = claim_key(gt.text, gt.normalized_skill)
            verdict = _verdict_for(truth_key, verdicts)
            predicted_verified = verdict == "verified"
            matched = predicted_verified == gt.is_verified
            case_flags.append(matched)
            match_flags.append(matched)
            if gt.is_fabricated:
                safe = not predicted_verified
                fabrication_safe_flags.append(safe)
                if not safe:
                    false_verifications.append({"id": case.id, "claim": gt.text, "verdict": verdict})

        per_case.append(
            {
                "id": case.id,
                "kind": case.kind,
                "claims": len(case.ground_truth_claims),
                "verdict_match": round(rate(case_flags), 4),
            }
        )

    return {
        "metric": METRIC_NAME,
        "case_count": len(cases),
        "overall": {
            "verdict_match_rate": round(rate(match_flags), 4),
            "claims_scored": len(match_flags),
            "fabrication_safety_rate": round(rate(fabrication_safe_flags), 4),
            "fabricated_claims": len(fabrication_safe_flags),
            "false_verifications": false_verifications,
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
