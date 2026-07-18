"""Runner: claim-extraction precision / recall / F1 against the golden ground truth.

For each case we replay the recorded model output through the real `extract_claims` stage
(citation guardrail and all), then match the accepted claims against the human-authored claim
set. Predictions the model invented but quoted from real resume text are false positives;
real claims the model missed are false negatives; claims it hallucinated with an uncitable
quote are silently discarded by the guardrail and correctly count as neither.

Run:  python -m evals.runners.run_claim_extraction
"""

from __future__ import annotations

import argparse
import asyncio
import json

from evals.harness.dataset import DEFAULT_DATASET, DEFAULT_FIXTURE_DIR, LLMFixture, load_dataset
from evals.harness.metrics import claim_key, match_predictions, precision_recall_f1
from evals.harness.pipeline import predicted_claim_keys, run_extraction

METRIC_NAME = "claim_extraction"


async def run(dataset_path=DEFAULT_DATASET, fixture_dir=DEFAULT_FIXTURE_DIR) -> dict:
    cases = load_dataset(dataset_path)
    total_tp = total_fp = total_fn = 0
    per_case: list[dict] = []

    for case in cases:
        fixture = LLMFixture.load(case.id, fixture_dir)
        extraction = await run_extraction(fixture, case.resume_text)
        pred_keys = predicted_claim_keys(extraction)
        truth_keys = [claim_key(c.text, c.normalized_skill) for c in case.ground_truth_claims]
        match = match_predictions(pred_keys, truth_keys)
        prf = precision_recall_f1(match.true_positives, match.false_positives, match.false_negatives)
        total_tp += match.true_positives
        total_fp += match.false_positives
        total_fn += match.false_negatives
        per_case.append(
            {
                "id": case.id,
                "kind": case.kind,
                "precision": round(prf.precision, 4),
                "recall": round(prf.recall, 4),
                "f1": round(prf.f1, 4),
                "tp": match.true_positives,
                "fp": match.false_positives,
                "fn": match.false_negatives,
                "discarded_uncitable": extraction.discarded_uncitable,
                "missed": match.unmatched_truth_keys,
                "spurious": match.unmatched_pred_keys,
            }
        )

    overall = precision_recall_f1(total_tp, total_fp, total_fn)
    return {
        "metric": METRIC_NAME,
        "case_count": len(cases),
        "overall": {
            "precision": round(overall.precision, 4),
            "recall": round(overall.recall, 4),
            "f1": round(overall.f1, 4),
            "tp": total_tp,
            "fp": total_fp,
            "fn": total_fn,
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
