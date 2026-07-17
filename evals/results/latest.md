# RecruitX pipeline benchmarks — golden_v1

- **Generated:** 2026-07-17T18:59:19.069209+00:00
- **Commit:** `e99a37b`
- **Provider:** `recorded-fixture` (offline recorded fixtures — see `evals/README.md` for what this does and does not prove)
- **Dataset:** `evals/datasets/golden_v1.jsonl` — 15 cases (real: 5, planted_lie: 5, edge: 5)

## Results

| Metric | Score | Detail |
|---|---|---|
| Claim-extraction F1 | **98.4%** | precision 98.4%, recall 98.4% (tp 60, fp 1, fn 1) |
| Citation validity | **100.0%** | 61 accepted claims, 0 invalid spans (target 100%) |
| Verdict match | **100.0%** | 61 claims scored |
| Fabrication safety | **100.0%** | 6 planted lies, 0 falsely verified (target 100%) |

## What each number means

- **Claim-extraction F1** — how completely and cleanly the pipeline turns a resume into citable claims, versus a human-labelled claim set.
- **Citation validity** — of the claims the pipeline accepted, the share whose source span resolves to a literal substring of the resume. This is the guardrail against manufactured confidence; the target is 100% and anything less is a defect, not a tuning knob.
- **Verdict match** — how often the system's verified / not-verified outcome agrees with ground truth.
- **Fabrication safety** — of the deliberately planted lies (fake companies, impossible tenure, fake certs), the share the system did **not** mark verified. This is the most important number in the table.

_The system never emits a score or an automated hire/reject decision; these metrics measure the evidence pipeline, not a hiring recommendation._
