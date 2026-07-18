"""Shared shape for evidence produced by the external connectors.

Mirrors the GitHub connector's draft (claim_id + verdict + summary + artifact_url + snippet) but
carries its own `source_type` so each connector labels its rows for the report matrix. Orchestrate
turns these into append-only Evidence rows exactly like the GitHub path.
"""

from dataclasses import dataclass


@dataclass
class EvidenceDraft:
    claim_id: str
    source_type: str  # semantic_scholar | google_patents | package_ownership
    verdict: str  # verified | partial  (connectors never emit unverified/contradicted — absence is silence)
    summary: str
    artifact_url: str
    artifact_snippet: str
