"""Loading and typing for the golden dataset and the recorded LLM fixtures.

The golden dataset (`datasets/golden_v1.jsonl`) is the human-authored ground truth: one JSON
object per line. It contains NO model output — only the resume, the JD, and what a careful
human says is true about the claims. Model output lives separately in `fixtures/llm/<id>.json`
so a fresh model run can be recorded without touching the ground truth, and so the two can
never be silently conflated.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

EVALS_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = EVALS_ROOT / "datasets" / "golden_v1.jsonl"
DEFAULT_FIXTURE_DIR = EVALS_ROOT / "fixtures" / "llm"


@dataclass(frozen=True)
class GroundTruthClaim:
    text: str
    category: str  # skill | employment | education | project | credential
    is_verified: bool  # should the pipeline end up treating this as verified?
    evidence_type: str  # expected corroborating source: github | consistency | none | ...
    is_fabricated: bool  # a planted lie — must NEVER end up verified
    normalized_skill: str | None = None  # canonical key for skill claims, aids matching


@dataclass(frozen=True)
class GoldenCase:
    id: str
    resume_text: str
    jd_text: str
    ground_truth_claims: list[GroundTruthClaim]
    kind: str = "unspecified"  # real | planted_lie | edge — informational, for reporting buckets
    notes: str = ""

    @property
    def fabricated_claims(self) -> list[GroundTruthClaim]:
        return [c for c in self.ground_truth_claims if c.is_fabricated]


def _parse_case(raw: dict) -> GoldenCase:
    claims = [
        GroundTruthClaim(
            text=c["text"],
            category=c["category"],
            is_verified=bool(c["is_verified"]),
            evidence_type=c.get("evidence_type", "none"),
            is_fabricated=bool(c.get("is_fabricated", False)),
            normalized_skill=c.get("normalized_skill"),
        )
        for c in raw["ground_truth_claims"]
    ]
    return GoldenCase(
        id=raw["id"],
        resume_text=raw["resume_text"],
        jd_text=raw["jd_text"],
        ground_truth_claims=claims,
        kind=raw.get("kind", "unspecified"),
        notes=raw.get("notes", ""),
    )


def load_dataset(path: Path | str = DEFAULT_DATASET) -> list[GoldenCase]:
    path = Path(path)
    cases: list[GoldenCase] = []
    with path.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            try:
                cases.append(_parse_case(json.loads(line)))
            except (json.JSONDecodeError, KeyError) as exc:
                raise ValueError(f"{path}:{line_no}: malformed golden case: {exc}") from exc
    if not cases:
        raise ValueError(f"{path}: no cases loaded")
    return cases


@dataclass(frozen=True)
class RecordedEvidence:
    """A recorded evidence draft from a connector (github/semantic_scholar/...) for offline
    replay. `claim_key` is how it attaches to an extracted claim (normalized skill or text)."""

    claim_key: str
    source_type: str
    verdict: str  # verified | partial
    artifact_url: str
    artifact_snippet: str
    summary: str = ""


@dataclass(frozen=True)
class LLMFixture:
    """One case's recorded model outputs + recorded external evidence. Authored to represent a
    plausible real model run (imperfections included) so offline metrics are non-trivial."""

    extracted_claims: dict  # a serialized ExtractedClaims payload (fed to FakeProvider)
    evidence: list[RecordedEvidence]

    @classmethod
    def load(cls, case_id: str, fixture_dir: Path | str = DEFAULT_FIXTURE_DIR) -> LLMFixture:
        path = Path(fixture_dir) / f"{case_id}.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        evidence = [
            RecordedEvidence(
                claim_key=e["claim_key"],
                source_type=e["source_type"],
                verdict=e["verdict"],
                artifact_url=e["artifact_url"],
                artifact_snippet=e["artifact_snippet"],
                summary=e.get("summary", ""),
            )
            for e in raw.get("evidence", [])
        ]
        return cls(extracted_claims=raw["extracted_claims"], evidence=evidence)
