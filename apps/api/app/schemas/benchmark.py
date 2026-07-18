"""Response shape for the public benchmarks endpoint.

Deliberately a thin passthrough of what the eval harness wrote (evals/results/latest.json),
plus the rendered markdown and a link to the dataset. `metrics` is left loosely typed because
each metric contributes its own detail keys and the schema should not have to change every time
the harness adds a number.
"""

from pydantic import BaseModel


class BenchmarkDataset(BaseModel):
    name: str
    path: str
    case_count: int
    buckets: dict[str, int] = {}


class BenchmarkReport(BaseModel):
    available: bool
    detail: str | None = None
    generated_at: str | None = None
    git_commit: str | None = None
    provider: str | None = None
    dataset: BenchmarkDataset | None = None
    metrics: dict[str, dict] = {}
    markdown: str | None = None
    dataset_url: str | None = None
