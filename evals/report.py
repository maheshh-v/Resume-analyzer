"""Aggregate the three runners into a dated JSON + a human-readable latest.md.

Outputs (under evals/results/):
  - YYYY-MM-DD.json : the full run, per-case detail included, keyed by date for history.
  - latest.json     : a stable-filename copy the backend endpoint reads.
  - latest.md       : the table humans (and the /benchmarks page's methodology text) read.

Run:  python -m evals.report      (or: make eval-report)
"""

from __future__ import annotations

import asyncio
import json
import subprocess
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

from evals.harness.dataset import DEFAULT_DATASET, load_dataset
from evals.runners import run_citation_validity, run_claim_extraction, run_verdict_accuracy

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def _git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return out.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


async def collect() -> dict:
    cases = load_dataset(DEFAULT_DATASET)
    buckets = Counter(c.kind for c in cases)

    extraction, citation, verdict = await asyncio.gather(
        run_claim_extraction.run(),
        run_citation_validity.run(),
        run_verdict_accuracy.run(),
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(),
        "provider": "recorded-fixture",  # offline; see README. Live runs set this to the model id.
        "dataset": {
            "name": "golden_v1",
            "path": "evals/datasets/golden_v1.jsonl",
            "case_count": len(cases),
            "buckets": dict(buckets),
        },
        "metrics": {
            "claim_extraction": extraction["overall"],
            "citation_validity": citation["overall"],
            "verdict_accuracy": verdict["overall"],
        },
        "runs": {
            "claim_extraction": extraction,
            "citation_validity": citation,
            "verdict_accuracy": verdict,
        },
    }


def _fmt_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def render_markdown(report: dict) -> str:
    m = report["metrics"]
    ds = report["dataset"]
    ce, cv, va = m["claim_extraction"], m["citation_validity"], m["verdict_accuracy"]
    buckets = ", ".join(f"{k}: {v}" for k, v in ds["buckets"].items())

    lines = [
        "# RecruitX pipeline benchmarks — golden_v1",
        "",
        f"- **Generated:** {report['generated_at']}",
        f"- **Commit:** `{report['git_commit']}`",
        f"- **Provider:** `{report['provider']}` "
        "(offline recorded fixtures — see `evals/README.md` for what this does and does not prove)",
        f"- **Dataset:** `{ds['path']}` — {ds['case_count']} cases ({buckets})",
        "",
        "## Results",
        "",
        "| Metric | Score | Detail |",
        "|---|---|---|",
        f"| Claim-extraction F1 | **{_fmt_pct(ce['f1'])}** | "
        f"precision {_fmt_pct(ce['precision'])}, recall {_fmt_pct(ce['recall'])} "
        f"(tp {ce['tp']}, fp {ce['fp']}, fn {ce['fn']}) |",
        f"| Citation validity | **{_fmt_pct(cv['span_citation_validity'])}** | "
        f"{cv['accepted_claims_checked']} accepted claims, "
        f"{cv['invalid_span_citations']} invalid spans (target 100%) |",
        f"| Verdict match | **{_fmt_pct(va['verdict_match_rate'])}** | "
        f"{va['claims_scored']} claims scored |",
        f"| Fabrication safety | **{_fmt_pct(va['fabrication_safety_rate'])}** | "
        f"{va['fabricated_claims']} planted lies, {len(va['false_verifications'])} falsely verified "
        "(target 100%) |",
        "",
        "## What each number means",
        "",
        "- **Claim-extraction F1** — how completely and cleanly the pipeline turns a resume into "
        "citable claims, versus a human-labelled claim set.",
        "- **Citation validity** — of the claims the pipeline accepted, the share whose source span "
        "resolves to a literal substring of the resume. This is the guardrail against manufactured "
        "confidence; the target is 100% and anything less is a defect, not a tuning knob.",
        "- **Verdict match** — how often the system's verified / not-verified outcome agrees with "
        "ground truth.",
        "- **Fabrication safety** — of the deliberately planted lies (fake companies, impossible "
        "tenure, fake certs), the share the system did **not** mark verified. This is the most "
        "important number in the table.",
        "",
        "_The system never emits a score or an automated hire/reject decision; these metrics measure "
        "the evidence pipeline, not a hiring recommendation._",
        "",
    ]
    return "\n".join(lines)


def write_report(report: dict, results_dir: Path = RESULTS_DIR) -> dict[str, Path]:
    results_dir.mkdir(parents=True, exist_ok=True)
    dated = results_dir / f"{date.today().isoformat()}.json"
    latest_json = results_dir / "latest.json"
    latest_md = results_dir / "latest.md"

    payload = json.dumps(report, indent=2, ensure_ascii=False)
    dated.write_text(payload, encoding="utf-8")
    latest_json.write_text(payload, encoding="utf-8")
    latest_md.write_text(render_markdown(report), encoding="utf-8")
    return {"dated": dated, "latest_json": latest_json, "latest_md": latest_md}


def main() -> None:
    report = asyncio.run(collect())
    paths = write_report(report)
    print("Wrote:")
    for label, path in paths.items():
        print(f"  {label}: {path}")
    m = report["metrics"]
    print(
        "\nSummary: "
        f"extraction F1 {m['claim_extraction']['f1']:.3f} | "
        f"citation {m['citation_validity']['span_citation_validity']:.3f} | "
        f"verdict {m['verdict_accuracy']['verdict_match_rate']:.3f} | "
        f"fabrication-safety {m['verdict_accuracy']['fabrication_safety_rate']:.3f}"
    )


if __name__ == "__main__":
    main()
