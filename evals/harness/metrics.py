"""Pure, dependency-free metric functions for the eval harness.

Everything here is deliberately free of I/O, LLM calls, and pipeline imports so it can be
unit-tested in isolation and reasoned about line by line. The runners do the messy work of
producing predictions; this module only scores them.

Two design choices worth calling out:

- Claim matching is *key-based*, not string-equality. A model rarely reproduces a ground-truth
  claim verbatim, so we normalize both sides to a comparison key (the canonical skill name when
  present, otherwise a normalized slice of the claim text) and allow substring containment. This
  is lenient on purpose: extraction recall should not be punished for cosmetic wording.
- Verdict matching collapses the pipeline's per-claim verdict to a single boolean "did the
  system end up treating this claim as verified", because that is the only thing that can
  manufacture false confidence about a real person. A fabricated claim that is *not* verified is
  a success even if its exact verdict label is "unverified" vs "contradicted".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[^a-z0-9+#. ]")


def normalize_text(text: str) -> str:
    """Lowercase, drop punctuation (keeping +, #, . for things like 'c++', 'c#', 'node.js'),
    and collapse whitespace. Deterministic and boring on purpose."""
    lowered = text.lower().strip()
    lowered = _PUNCT.sub(" ", lowered)
    return _WS.sub(" ", lowered).strip()


def claim_key(claim_text: str, normalized_skill: str | None = None) -> str:
    """The comparison key for a claim. Prefer the canonical skill name — two systems agree far
    more often on 'python' than on the sentence they wrapped it in — and fall back to the
    normalized claim text otherwise."""
    if normalized_skill and normalized_skill.strip():
        return normalize_text(normalized_skill)
    return normalize_text(claim_text)


def keys_match(a: str, b: str) -> bool:
    """Equal after normalization, or a containment match on non-trivial keys. The length gate
    stops 'c' or 'go' from matching everything."""
    if not a or not b:
        return False
    if a == b:
        return True
    if len(a) >= 4 and len(b) >= 4 and (a in b or b in a):
        return True
    return False


@dataclass
class MatchResult:
    true_positives: int
    false_positives: int
    false_negatives: int
    matched_truth_keys: list[str] = field(default_factory=list)
    unmatched_truth_keys: list[str] = field(default_factory=list)
    unmatched_pred_keys: list[str] = field(default_factory=list)


def match_predictions(predicted_keys: list[str], truth_keys: list[str]) -> MatchResult:
    """Greedy one-to-one matching of predicted claim keys against ground-truth keys.

    Each ground-truth claim consumes at most one prediction. Leftover predictions are false
    positives (the model extracted something not in the truth set); leftover truths are false
    negatives (the model missed a real claim)."""
    remaining = list(predicted_keys)
    tp = 0
    matched: list[str] = []
    missed: list[str] = []
    for truth in truth_keys:
        hit_index = next((i for i, pred in enumerate(remaining) if keys_match(truth, pred)), None)
        if hit_index is None:
            missed.append(truth)
            continue
        tp += 1
        matched.append(truth)
        remaining.pop(hit_index)
    return MatchResult(
        true_positives=tp,
        false_positives=len(remaining),
        false_negatives=len(missed),
        matched_truth_keys=matched,
        unmatched_truth_keys=missed,
        unmatched_pred_keys=remaining,
    )


@dataclass(frozen=True)
class PRF:
    precision: float
    recall: float
    f1: float
    true_positives: int
    false_positives: int
    false_negatives: int


def precision_recall_f1(true_positives: int, false_positives: int, false_negatives: int) -> PRF:
    """Standard P/R/F1 with the usual zero-denominator convention (0.0, not a crash). An empty
    prediction set against an empty truth set is a perfect, uninteresting 1.0."""
    tp, fp, fn = true_positives, false_positives, false_negatives
    if tp == fp == fn == 0:
        return PRF(1.0, 1.0, 1.0, 0, 0, 0)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return PRF(precision, recall, f1, tp, fp, fn)


def rate(values: list[bool]) -> float:
    """Fraction of True values. An empty list is 1.0 (vacuously true) — the runners report the
    denominator alongside so a 1.0 over zero samples is never mistaken for a real result."""
    if not values:
        return 1.0
    return sum(1 for v in values if v) / len(values)
