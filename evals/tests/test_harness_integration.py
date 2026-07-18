"""End-to-end harness test on two fixture cases with a mocked LLM (no network, no paid API).

Builds a 2-case dataset (one clean 'real' resume, one planted-lie resume whose fabrications the
consistency checker must catch), then runs all three runners through the REAL pipeline stages with
the LLM output supplied entirely by recorded fixtures. Asserts the metrics come out as expected —
this is the guard that the whole harness wires together correctly.
"""

import asyncio
import json
from pathlib import Path

from evals.harness.dataset import DEFAULT_DATASET, DEFAULT_FIXTURE_DIR
from evals.runners import run_citation_validity, run_claim_extraction, run_verdict_accuracy

CLEAN_CASE = "real_01_backend_python"
LIE_CASE = "lie_02_overlapping_fulltime"  # two concurrent full-time roles -> consistency contradiction


def _two_case_dataset(tmp_path: Path) -> Path:
    wanted = {CLEAN_CASE, LIE_CASE}
    kept = []
    for line in DEFAULT_DATASET.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        if json.loads(line)["id"] in wanted:
            kept.append(line)
    assert len(kept) == 2, f"expected 2 cases, selected {len(kept)}"
    path = tmp_path / "two_cases.jsonl"
    path.write_text("\n".join(kept) + "\n", encoding="utf-8")
    return path


def test_claim_extraction_runner_end_to_end(tmp_path):
    dataset = _two_case_dataset(tmp_path)
    result = asyncio.run(run_claim_extraction.run(dataset, DEFAULT_FIXTURE_DIR))
    assert result["case_count"] == 2
    # Both cases are authored so the model extracts every claim verbatim and invents nothing.
    assert result["overall"]["f1"] == 1.0
    assert result["overall"]["fp"] == 0
    assert result["overall"]["fn"] == 0


def test_citation_validity_runner_end_to_end(tmp_path):
    dataset = _two_case_dataset(tmp_path)
    result = asyncio.run(run_citation_validity.run(dataset, DEFAULT_FIXTURE_DIR))
    # The guardrail's core promise: every accepted claim's span resolves to literal source text.
    assert result["overall"]["span_citation_validity"] == 1.0
    assert result["overall"]["invalid_span_citations"] == 0
    assert result["overall"]["accepted_claims_checked"] > 0


def test_verdict_accuracy_runner_catches_planted_lie(tmp_path):
    dataset = _two_case_dataset(tmp_path)
    result = asyncio.run(run_verdict_accuracy.run(dataset, DEFAULT_FIXTURE_DIR))
    overall = result["overall"]
    # The overlapping-tenure fabrication must be caught (never verified) — the number that matters.
    assert overall["fabrication_safety_rate"] == 1.0
    assert overall["fabricated_claims"] >= 2
    assert overall["false_verifications"] == []
    assert overall["verdict_match_rate"] == 1.0


def test_fixtures_exist_for_selected_cases():
    for case_id in (CLEAN_CASE, LIE_CASE):
        assert (DEFAULT_FIXTURE_DIR / f"{case_id}.json").exists()
