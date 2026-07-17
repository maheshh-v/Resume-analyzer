"""Response shapes for the per-candidate LLM cost endpoint."""

from pydantic import BaseModel


class LLMStageCost(BaseModel):
    pipeline_stage: str
    calls: int
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms_total: int
    max_retry_count: int
    models: list[str]


class LLMCostSummary(BaseModel):
    candidate_id: str
    total_cost_usd: float
    total_calls: int
    total_input_tokens: int
    total_output_tokens: int
    total_latency_ms: int
    per_stage: list[LLMStageCost]
