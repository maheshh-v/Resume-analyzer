"""Public, unauthenticated benchmarks endpoint.

Serves the numbers the eval harness produced (evals/results/latest.json + latest.md) so the
public /benchmarks page can render honest, reproducible accuracy figures. Read-only, no auth,
no database. If no run exists yet it returns `available: false` with a 200 — an empty benchmark
is a normal state (fresh clone, CI hasn't run the harness), not a server error.
"""

import json
import logging
from pathlib import Path

from fastapi import APIRouter

from app.config import get_settings
from app.schemas.benchmark import BenchmarkDataset, BenchmarkReport

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/benchmarks", tags=["benchmarks"])

# apps/api/app/routers/benchmarks.py -> parents[4] is the repo root.
_REPO_ROOT = Path(__file__).resolve().parents[4]
_DATASET_URL = "https://github.com/maheshh-v/Resume-analyzer/blob/main/evals/datasets/golden_v1.jsonl"


def _results_dir() -> Path:
    override = get_settings().benchmarks_results_dir
    return Path(override) if override else _REPO_ROOT / "evals" / "results"


@router.get("/latest", response_model=BenchmarkReport)
async def latest_benchmarks() -> BenchmarkReport:
    results_dir = _results_dir()
    latest_json = results_dir / "latest.json"
    latest_md = results_dir / "latest.md"

    if not latest_json.exists():
        return BenchmarkReport(
            available=False,
            detail="No benchmark run found. Run `make eval-report` to generate one.",
            dataset_url=_DATASET_URL,
        )

    try:
        data = json.loads(latest_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("benchmarks: could not read %s: %s", latest_json, exc)
        return BenchmarkReport(
            available=False,
            detail="Benchmark results are present but unreadable.",
            dataset_url=_DATASET_URL,
        )

    markdown = latest_md.read_text(encoding="utf-8") if latest_md.exists() else None
    ds = data.get("dataset") or {}
    return BenchmarkReport(
        available=True,
        generated_at=data.get("generated_at"),
        git_commit=data.get("git_commit"),
        provider=data.get("provider"),
        dataset=BenchmarkDataset(**ds) if ds else None,
        metrics=data.get("metrics", {}),
        markdown=markdown,
        dataset_url=_DATASET_URL,
    )
