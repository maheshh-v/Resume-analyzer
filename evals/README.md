# RecruitX evaluation harness

Measurable, reproducible accuracy for the verification pipeline. This is what lets us put honest
numbers on the `/benchmarks` page instead of adjectives.

## What it measures

Three runners, each scoring the **real backend pipeline** (not a reimplementation — the harness
imports `apps/api` at runtime) against a hand-labelled dataset:

| Runner | Metric | Target |
|---|---|---|
| `run_claim_extraction` | precision / recall / F1 of extracted claims vs. ground truth | high, not gamed |
| `run_citation_validity` | share of accepted claims whose source span resolves to a literal substring of the resume | **100%** |
| `run_verdict_accuracy` | verdict-match rate **and** fabrication-safety rate (planted lies never marked verified) | verdict: high · fabrication-safety: **100%** |

The two 100% targets are not tuning knobs. A citation that doesn't resolve, or a fabricated claim
marked "verified", is a product-ending bug — the whole point of the system is to *not* manufacture
false confidence about a real person.

## How to run

```bash
make eval          # run all three runners, print JSON to stdout (writes nothing)
make eval-report   # aggregate into evals/results/{latest.json, latest.md, <date>.json}
make eval-test     # run the harness's own unit + integration tests
make eval-build    # regenerate golden_v1.jsonl + fixtures from the authoring script
```

Or directly (from the repo root, using the backend venv):

```bash
python -m evals.runners.run_claim_extraction
python -m evals.report
```

The backend endpoint `GET /api/v1/benchmarks/latest` reads `evals/results/latest.json` + `latest.md`
and serves them to the public page.

## Methodology, and what these numbers do and do NOT prove

- **Dataset** (`datasets/golden_v1.jsonl`, 15 cases): 5 real-ish resumes, 5 with planted lies
  (fake company, two concurrent full-time roles, fake cert, impossible skill-years, false OSS
  authorship), and 5 edge cases (career gap, non-English names, firewall-only work, sparse
  project-only resume, partial GitHub match). Each ground-truth claim is labelled by a human with
  `is_verified`, `is_fabricated`, and the expected evidence type.

- **Offline by default.** Runs use *recorded LLM fixtures* (`fixtures/llm/<id>.json`), not a live
  model — so CI is deterministic, free, and never hits a paid API. The fixtures represent a
  plausible strong model run with deliberate imperfections baked in (one missed claim, one spurious
  claim, one hallucinated-uncitable claim the guardrail must discard), so the numbers are non-trivial
  rather than a rigged 100%. The `provider` field in the report reads `recorded-fixture` to make this
  explicit.

- **What is genuinely being measured:** the pipeline's own processing — the citation guardrail
  discarding uncitable claims, skill normalization, the consistency checker catching impossible
  tenure and inflated years, and verdict assignment. These are the parts that carry the product's
  safety guarantees, and they run for real against every case.

- **What this does NOT prove:** live model extraction quality. The recorded fixtures stand in for the
  model. To measure the live model, re-record the fixtures against it (a paid run — ask first) and
  re-run; set `provider` to the model id. See `datasets/MAKE_MORE.md`.

- **Reproducibility:** consistency checks are pinned to a fixed reference date (`EVAL_TODAY`) so
  open-ended ("present") employment doesn't drift with the wall clock.

## Layout

```
evals/
  datasets/
    golden_v1.jsonl       # ground truth — one case per line (no model output)
    build_golden.py       # authoring script; asserts every quote is a literal substring
    MAKE_MORE.md          # how to add cases
  fixtures/llm/<id>.json  # recorded model output + recorded evidence, per case
  harness/
    dataset.py            # loading + typed schema
    metrics.py            # pure P/R/F1, matching, rates (unit-tested)
    pipeline.py           # bridge into apps/api pipeline stages (FakeProvider, no network)
  runners/                # the three metric runners
  report.py               # aggregator -> results/
  results/                # generated: latest.json, latest.md, <date>.json
  tests/                  # unit tests (metrics) + integration test (2 cases, mocked LLM)
```
