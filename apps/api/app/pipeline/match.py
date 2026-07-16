"""Claims x requirements -> strengths / gaps / matching claims.

Deterministic, zero LLM cost. This is a derived view, not persisted state — recompute it
whenever claims or requirements change rather than trying to keep a cached match table in
sync. Matching is by normalized_skill string equality for the MVP; this is the first thing
to upgrade (e.g. a small synonym table: "js" == "javascript") if eval data shows misses.
"""

from dataclasses import dataclass, field


@dataclass
class RequirementLike:
    id: str
    skill: str
    normalized_skill: str
    importance: str
    min_years: float | None


@dataclass
class ClaimLike:
    id: str
    claim_text: str
    normalized_skill: str | None
    asserted_years: float | None


@dataclass
class RequirementMatch:
    requirement_id: str
    skill: str
    importance: str
    status: str  # matched | partial | gap
    matching_claim_ids: list[str] = field(default_factory=list)
    note: str = ""


def match_claims_to_requirements(
    requirements: list[RequirementLike], claims: list[ClaimLike]
) -> list[RequirementMatch]:
    results: list[RequirementMatch] = []
    for req in requirements:
        matches = [c for c in claims if c.normalized_skill == req.normalized_skill]
        if not matches:
            results.append(
                RequirementMatch(
                    requirement_id=req.id,
                    skill=req.skill,
                    importance=req.importance,
                    status="gap",
                    note="No claim found for this requirement.",
                )
            )
            continue

        if req.min_years is not None:
            best_years = max((c.asserted_years or 0) for c in matches)
            if best_years >= req.min_years:
                status, note = "matched", f"Claims {best_years:g}+ years (requires {req.min_years:g}+)."
            else:
                status, note = (
                    "partial",
                    f"Claims {best_years:g} years, below the {req.min_years:g}-year bar.",
                )
        else:
            status, note = "matched", "Claim present."

        results.append(
            RequirementMatch(
                requirement_id=req.id,
                skill=req.skill,
                importance=req.importance,
                status=status,
                matching_claim_ids=[c.id for c in matches],
                note=note,
            )
        )
    return results
