"""Observability: Langfuse tracing context + per-call cost/latency logging.

The LLM client (app/llm/client.py) is the single choke point every model call flows through;
this package gives it (a) ambient candidate/job context to tag traces with, and (b) a best-effort
sink for cost/latency metadata. Both are no-ops when unconfigured or when there is no active
candidate context, so tests and offline tooling are unaffected.
"""
