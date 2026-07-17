"""Authoring tool for golden_v1.jsonl + the matching recorded-LLM fixtures.

Why a builder instead of hand-editing JSONL: the extraction stage DISCARDS any claim whose
`quoted_source_text` is not a verbatim substring of the resume (the citation guardrail). If a
hand-typed quote is off by one character, the claim vanishes and the metrics quietly lie. This
script asserts every quote is a real substring at build time, so a broken case fails loudly here
instead of skewing a benchmark number later.

It writes two things per case, kept deliberately separate:
  - the GROUND TRUTH (resume, JD, what a human says is true) -> datasets/golden_v1.jsonl
  - a plausible RECORDED MODEL RUN (what the LLM returned, imperfections included) -> fixtures/llm/<id>.json

Regenerate with:  python evals/datasets/build_golden.py
See MAKE_MORE.md for how to add a case.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVALS_ROOT = HERE.parent
DATASET_PATH = HERE / "golden_v1.jsonl"
FIXTURE_DIR = EVALS_ROOT / "fixtures" / "llm"


def _quote(resume: str, phrase: str) -> str:
    """Return `phrase` after proving it appears verbatim in `resume`. This is the guardrail the
    real pipeline applies, enforced at authoring time so a case can never ship uncitable."""
    if phrase not in resume:
        raise AssertionError(f"quote not found verbatim in resume:\n  quote={phrase!r}")
    return phrase


def claim(
    *,
    text: str,
    category: str,
    quote: str,
    is_verified: bool = False,
    evidence_type: str = "none",
    is_fabricated: bool = False,
    normalized_skill: str | None = None,
    asserted_years: float | None = None,
    asserted_start: str | None = None,
    asserted_end: str | None = None,
    asserted_org: str | None = None,
    model_extracts: bool = True,
) -> dict:
    """One ground-truth claim plus how the recorded model reproduces it. `model_extracts=False`
    represents a real claim the model missed (a false negative for recall)."""
    return {
        "text": text,
        "category": category,
        "quote": quote,
        "is_verified": is_verified,
        "evidence_type": evidence_type,
        "is_fabricated": is_fabricated,
        "normalized_skill": normalized_skill,
        "asserted_years": asserted_years,
        "asserted_start": asserted_start,
        "asserted_end": asserted_end,
        "asserted_org": asserted_org,
        "model_extracts": model_extracts,
    }


def evidence(*, claim_key: str, source_type: str, verdict: str, url: str, snippet: str, summary: str = "") -> dict:
    return {
        "claim_key": claim_key,
        "source_type": source_type,
        "verdict": verdict,
        "artifact_url": url,
        "artifact_snippet": snippet,
        "summary": summary,
    }


# --------------------------------------------------------------------------------------------
# CASES. Each case: id, kind, resume_text, jd_text, claims[], optional model_noise[], evidence[].
# `kind` is one of real | planted_lie | edge and only affects reporting buckets.
# --------------------------------------------------------------------------------------------

CASES: list[dict] = []


def add_case(**case) -> None:
    CASES.append(case)


# ---- A. Real-ish (5) -----------------------------------------------------------------------

_r = (
    "Priya Nandakumar\n"
    "Backend Engineer\n\n"
    "Experience:\n"
    "Senior Backend Engineer, Cloudhatch Systems (2021-03 to present). Built payment "
    "reconciliation services in Python and Go, handling 4M events/day.\n"
    "Backend Engineer, Northwind Retail (2018-06 to 2021-02). Owned the inventory API in "
    "Python and PostgreSQL.\n\n"
    "Skills: 6 years of Python, 3 years of Go, PostgreSQL, Kafka, Docker.\n"
    "GitHub: github.com/priya-nk"
)
add_case(
    id="real_01_backend_python",
    kind="real",
    notes="Straightforward senior backend resume; Python verifiable via a real public repo.",
    resume_text=_r,
    jd_text="Senior Backend Engineer. Must have: Python, PostgreSQL, distributed systems. Nice to have: Go, Kafka.",
    claims=[
        claim(text="Senior Backend Engineer at Cloudhatch Systems", category="employment",
              quote=_quote(_r, "Senior Backend Engineer, Cloudhatch Systems (2021-03 to present)"),
              asserted_org="Cloudhatch Systems", asserted_start="2021-03", asserted_end=None),
        claim(text="Backend Engineer at Northwind Retail", category="employment",
              quote=_quote(_r, "Backend Engineer, Northwind Retail (2018-06 to 2021-02)"),
              asserted_org="Northwind Retail", asserted_start="2018-06", asserted_end="2021-02"),
        claim(text="6 years of Python", category="skill", normalized_skill="python",
              quote=_quote(_r, "6 years of Python"), asserted_years=6.0,
              is_verified=True, evidence_type="github"),
        claim(text="3 years of Go", category="skill", normalized_skill="go",
              quote=_quote(_r, "3 years of Go"), asserted_years=3.0),
        claim(text="PostgreSQL", category="skill", normalized_skill="postgresql",
              quote=_quote(_r, "PostgreSQL")),
    ],
    evidence=[
        evidence(claim_key="python", source_type="github", verdict="verified",
                 url="https://github.com/priya-nk/reconcile",
                 snippet="Python: 184320 bytes",
                 summary="'python' appears as a primary language in their repo 'reconcile'."),
    ],
)

_r = (
    "Marcus Bell — Frontend Engineer\n\n"
    "Frontend Engineer, Lumen Health (2020-01 to present). Rebuilt the patient portal in "
    "React and TypeScript, cut load time by 40%.\n"
    "Junior Web Developer, Bright Agency (2017-09 to 2019-12).\n\n"
    "Skills: 5 years of React, TypeScript, Next.js, CSS, accessibility (WCAG 2.1).\n"
    "GitHub: github.com/marcusbell-dev"
)
add_case(
    id="real_02_frontend_react",
    kind="real",
    notes="Frontend resume. Model over-extracts a 'jest' claim not present in ground truth (a false positive).",
    resume_text=_r,
    jd_text="Frontend Engineer. Must have: React, TypeScript, accessibility. Nice to have: Next.js.",
    claims=[
        claim(text="Frontend Engineer at Lumen Health", category="employment",
              quote=_quote(_r, "Frontend Engineer, Lumen Health (2020-01 to present)"),
              asserted_org="Lumen Health", asserted_start="2020-01", asserted_end=None),
        claim(text="5 years of React", category="skill", normalized_skill="react",
              quote=_quote(_r, "5 years of React"), asserted_years=5.0,
              is_verified=True, evidence_type="github"),
        claim(text="TypeScript", category="skill", normalized_skill="typescript",
              quote=_quote(_r, "TypeScript")),
        claim(text="accessibility (WCAG 2.1)", category="skill", normalized_skill="accessibility",
              quote=_quote(_r, "accessibility (WCAG 2.1)")),
    ],
    # The model hallucinates a skill the resume never mentions — but quotes real text, so it
    # passes the guardrail and lands as a genuine precision miss.
    model_noise=[
        {"claim_type": "skill", "claim_text": "Jest testing", "normalized_skill": "jest",
         "quote": _quote(_r, "cut load time by 40%")},
    ],
    evidence=[
        evidence(claim_key="react", source_type="github", verdict="verified",
                 url="https://github.com/marcusbell-dev/portal",
                 snippet="TypeScript: 402113 bytes",
                 summary="'react' project surfaces in their repo 'portal'."),
    ],
)

_r = (
    "Dr. Wei Chen\n"
    "Machine Learning Engineer\n\n"
    "ML Engineer, Fathom Analytics (2019-04 to present). Shipped a churn model in Python and "
    "PyTorch; deployed feature pipelines on Spark.\n"
    "Research Assistant, State University (2016-09 to 2019-03).\n\n"
    "Skills: Python, PyTorch, Spark, SQL, 4 years of production ML.\n"
    "Education: PhD candidate, Computer Science, State University."
)
add_case(
    id="real_03_ml_engineer",
    kind="real",
    notes="ML resume. Model MISSES the Spark skill (a recall/false-negative case). No public repo -> mostly unverified.",
    resume_text=_r,
    jd_text="ML Engineer. Must have: Python, PyTorch, production ML. Nice to have: Spark, SQL.",
    claims=[
        claim(text="ML Engineer at Fathom Analytics", category="employment",
              quote=_quote(_r, "ML Engineer, Fathom Analytics (2019-04 to present)"),
              asserted_org="Fathom Analytics", asserted_start="2019-04", asserted_end=None),
        claim(text="Python", category="skill", normalized_skill="python",
              quote=_quote(_r, "Python")),
        claim(text="PyTorch", category="skill", normalized_skill="pytorch",
              quote=_quote(_r, "PyTorch")),
        # The model fails to extract Spark from the skills line -> false negative.
        claim(text="Spark", category="skill", normalized_skill="spark",
              quote=_quote(_r, "Spark"), model_extracts=False),
        claim(text="PhD candidate in Computer Science", category="education",
              quote=_quote(_r, "PhD candidate, Computer Science, State University")),
    ],
    evidence=[],
)

_r = (
    "Sofia Ramirez\n"
    "Site Reliability Engineer\n\n"
    "SRE, Beacon Cloud (2020-07 to present). Ran a 200-node Kubernetes fleet; wrote Terraform "
    "modules and Go operators; cut incident MTTR by half.\n"
    "Systems Engineer, Orbit Telecom (2017-01 to 2020-06).\n\n"
    "Skills: Kubernetes, Terraform, Go, AWS, Prometheus, 7 years total."
)
add_case(
    id="real_04_sre_devops",
    kind="real",
    notes="SRE resume, clean and internally consistent.",
    resume_text=_r,
    jd_text="Site Reliability Engineer. Must have: Kubernetes, Terraform, AWS. Nice to have: Go.",
    claims=[
        claim(text="SRE at Beacon Cloud", category="employment",
              quote=_quote(_r, "SRE, Beacon Cloud (2020-07 to present)"),
              asserted_org="Beacon Cloud", asserted_start="2020-07", asserted_end=None),
        claim(text="Systems Engineer at Orbit Telecom", category="employment",
              quote=_quote(_r, "Systems Engineer, Orbit Telecom (2017-01 to 2020-06)"),
              asserted_org="Orbit Telecom", asserted_start="2017-01", asserted_end="2020-06"),
        claim(text="Kubernetes", category="skill", normalized_skill="kubernetes",
              quote=_quote(_r, "Kubernetes")),
        claim(text="Terraform", category="skill", normalized_skill="terraform",
              quote=_quote(_r, "Terraform")),
        claim(text="AWS", category="skill", normalized_skill="aws", quote=_quote(_r, "AWS")),
    ],
    evidence=[],
)

_r = (
    "Tom O'Brien\n"
    "Full-Stack Engineer\n\n"
    "Full-Stack Engineer, Mapleworks (2019-11 to present). Built a logistics dashboard end to "
    "end: React front end, Node.js and Express API, PostgreSQL.\n"
    "Web Developer, Corner Studio (2016-03 to 2019-10).\n\n"
    "Skills: JavaScript, Node.js, React, PostgreSQL, 8 years total.\n"
    "GitHub: github.com/tobrien-codes"
)
add_case(
    id="real_05_fullstack",
    kind="real",
    notes="Full-stack resume; Node.js verifiable via a public repo.",
    resume_text=_r,
    jd_text="Full-Stack Engineer. Must have: JavaScript, React, Node.js, SQL.",
    claims=[
        claim(text="Full-Stack Engineer at Mapleworks", category="employment",
              quote=_quote(_r, "Full-Stack Engineer, Mapleworks (2019-11 to present)"),
              asserted_org="Mapleworks", asserted_start="2019-11", asserted_end=None),
        claim(text="Node.js", category="skill", normalized_skill="node.js",
              quote=_quote(_r, "Node.js"), is_verified=True, evidence_type="github"),
        claim(text="React", category="skill", normalized_skill="react", quote=_quote(_r, "React")),
        claim(text="PostgreSQL", category="skill", normalized_skill="postgresql",
              quote=_quote(_r, "PostgreSQL")),
    ],
    evidence=[
        evidence(claim_key="node.js", source_type="github", verdict="verified",
                 url="https://github.com/tobrien-codes/logistics",
                 snippet="JavaScript: 251004 bytes",
                 summary="'node.js' project surfaces in their repo 'logistics'."),
    ],
)

# ---- B. Planted lies (5) -------------------------------------------------------------------

_r = (
    "Aidan Cross\n"
    "Software Engineer\n\n"
    "Senior Engineer, Vertex Quantum Labs (2021-05 to present). Led the core platform team.\n"
    "Software Engineer, Real Systems Inc (2018-02 to 2021-04).\n\n"
    "Skills: Python, Rust, distributed systems, 6 years total."
)
add_case(
    id="lie_01_fake_company",
    kind="planted_lie",
    notes="'Vertex Quantum Labs' is a fabricated employer with no public existence. Must stay unverified.",
    resume_text=_r,
    jd_text="Senior Software Engineer. Must have: Python, distributed systems. Nice to have: Rust.",
    claims=[
        claim(text="Senior Engineer at Vertex Quantum Labs", category="employment",
              quote=_quote(_r, "Senior Engineer, Vertex Quantum Labs (2021-05 to present)"),
              asserted_org="Vertex Quantum Labs", asserted_start="2021-05", asserted_end=None,
              is_fabricated=True, is_verified=False, evidence_type="none"),
        claim(text="Software Engineer at Real Systems Inc", category="employment",
              quote=_quote(_r, "Software Engineer, Real Systems Inc (2018-02 to 2021-04)"),
              asserted_org="Real Systems Inc", asserted_start="2018-02", asserted_end="2021-04"),
        claim(text="Python", category="skill", normalized_skill="python", quote=_quote(_r, "Python")),
        claim(text="Rust", category="skill", normalized_skill="rust", quote=_quote(_r, "Rust")),
    ],
    evidence=[],  # a fabricated company yields no corroborating artifact
)

_r = (
    "Bianca Ferro\n"
    "Engineering Manager\n\n"
    "VP of Engineering, Stellar Grid (2022-01 to present). Full-time.\n"
    "Head of Platform, Nimbus Data (2021-06 to present). Full-time.\n\n"
    "Skills: leadership, Python, 9 years total."
)
add_case(
    id="lie_02_overlapping_fulltime",
    kind="planted_lie",
    notes="Two concurrent full-time roles (both 'present'). Consistency check should flag date_overlap.",
    resume_text=_r,
    jd_text="Engineering Manager. Must have: leadership, platform experience.",
    claims=[
        claim(text="VP of Engineering at Stellar Grid", category="employment",
              quote=_quote(_r, "VP of Engineering, Stellar Grid (2022-01 to present)"),
              asserted_org="Stellar Grid", asserted_start="2022-01", asserted_end=None,
              is_fabricated=True, is_verified=False, evidence_type="consistency"),
        claim(text="Head of Platform at Nimbus Data", category="employment",
              quote=_quote(_r, "Head of Platform, Nimbus Data (2021-06 to present)"),
              asserted_org="Nimbus Data", asserted_start="2021-06", asserted_end=None,
              is_fabricated=True, is_verified=False, evidence_type="consistency"),
        claim(text="Python", category="skill", normalized_skill="python", quote=_quote(_r, "Python")),
    ],
    evidence=[],
)

_r = (
    "Carl Denton\n"
    "Cloud Engineer\n\n"
    "Cloud Engineer, Pinnacle Cloud (2020-03 to present). Migrated workloads to AWS.\n\n"
    "Certifications: AWS Certified Solutions Architect – Professional (credential ID AWS-PRO-9981).\n"
    "Skills: AWS, Python, Terraform."
)
add_case(
    id="lie_03_fake_certification",
    kind="planted_lie",
    notes="The AWS cert credential ID is fabricated; it resolves to nothing. Claim must stay unverified.",
    resume_text=_r,
    jd_text="Cloud Engineer. Must have: AWS, Terraform. Certification a plus.",
    claims=[
        claim(text="Cloud Engineer at Pinnacle Cloud", category="employment",
              quote=_quote(_r, "Cloud Engineer, Pinnacle Cloud (2020-03 to present)"),
              asserted_org="Pinnacle Cloud", asserted_start="2020-03", asserted_end=None),
        claim(text="AWS Certified Solutions Architect – Professional", category="credential",
              quote=_quote(_r, "AWS Certified Solutions Architect – Professional (credential ID AWS-PRO-9981)"),
              is_fabricated=True, is_verified=False, evidence_type="none"),
        claim(text="AWS", category="skill", normalized_skill="aws", quote=_quote(_r, "AWS")),
        claim(text="Terraform", category="skill", normalized_skill="terraform",
              quote=_quote(_r, "Terraform")),
    ],
    evidence=[],
)

_r = (
    "Dana Whitmore\n"
    "Junior Developer\n\n"
    "Junior Developer, Small Shop LLC (2023-01 to present).\n\n"
    "Skills: 12 years of Python, JavaScript.\n"
    "Education: BSc Computer Science, 2022."
)
add_case(
    id="lie_04_years_exceed_career",
    kind="planted_lie",
    notes="Claims 12 years of Python but the visible career is ~1 year. Consistency: years_exceed_career_span.",
    resume_text=_r,
    jd_text="Python Developer. Must have: Python. Nice to have: JavaScript.",
    claims=[
        claim(text="Junior Developer at Small Shop LLC", category="employment",
              quote=_quote(_r, "Junior Developer, Small Shop LLC (2023-01 to present)"),
              asserted_org="Small Shop LLC", asserted_start="2023-01", asserted_end=None),
        claim(text="12 years of Python", category="skill", normalized_skill="python",
              quote=_quote(_r, "12 years of Python"), asserted_years=12.0,
              is_fabricated=True, is_verified=False, evidence_type="consistency"),
        claim(text="JavaScript", category="skill", normalized_skill="javascript",
              quote=_quote(_r, "JavaScript")),
    ],
    evidence=[],
)

_r = (
    "Evan Sokolov\n"
    "Software Engineer\n\n"
    "Software Engineer, Delta Corp (2019-08 to present).\n\n"
    "Open source: sole author and creator of the 'requests' Python library, used by millions.\n"
    "Skills: Python, HTTP, API design."
)
add_case(
    id="lie_05_false_oss_authorship",
    kind="planted_lie",
    notes="Falsely claims sole authorship of a famous OSS project they don't own. Must stay unverified.",
    resume_text=_r,
    jd_text="Backend Engineer. Must have: Python, API design.",
    claims=[
        claim(text="Software Engineer at Delta Corp", category="employment",
              quote=_quote(_r, "Software Engineer, Delta Corp (2019-08 to present)"),
              asserted_org="Delta Corp", asserted_start="2019-08", asserted_end=None),
        claim(text="Sole author of the 'requests' Python library", category="project",
              quote=_quote(_r, "sole author and creator of the 'requests' Python library"),
              is_fabricated=True, is_verified=False, evidence_type="none"),
        claim(text="Python", category="skill", normalized_skill="python", quote=_quote(_r, "Python")),
    ],
    evidence=[],  # ownership cannot be corroborated -> no evidence, stays unverified
)

# ---- C. Edge cases (5) ---------------------------------------------------------------------

_r = (
    "Fatima Al-Sayed\n"
    "Backend Engineer\n\n"
    "Backend Engineer, Harbor Systems (2022-02 to present).\n"
    "Career break (2019-06 to 2022-01) — full-time caregiving.\n"
    "Backend Engineer, Delta Freight (2016-01 to 2019-05).\n\n"
    "Skills: Java, Spring, PostgreSQL, 6 years total."
)
add_case(
    id="edge_01_career_gap",
    kind="edge",
    notes="Legitimate multi-year career gap. Consistency must NOT flag it as a contradiction.",
    resume_text=_r,
    jd_text="Backend Engineer. Must have: Java, Spring, SQL.",
    claims=[
        claim(text="Backend Engineer at Harbor Systems", category="employment",
              quote=_quote(_r, "Backend Engineer, Harbor Systems (2022-02 to present)"),
              asserted_org="Harbor Systems", asserted_start="2022-02", asserted_end=None),
        claim(text="Backend Engineer at Delta Freight", category="employment",
              quote=_quote(_r, "Backend Engineer, Delta Freight (2016-01 to 2019-05)"),
              asserted_org="Delta Freight", asserted_start="2016-01", asserted_end="2019-05"),
        claim(text="Java", category="skill", normalized_skill="java", quote=_quote(_r, "Java")),
        claim(text="Spring", category="skill", normalized_skill="spring", quote=_quote(_r, "Spring")),
    ],
    evidence=[],
)

_r = (
    "Bjørn Þórarinsson\n"
    "Systems Programmer\n\n"
    "Systems Programmer, Reykjavík Data ehf (2018-09 to present). Wrote C and Rust for a "
    "high-throughput packet processor.\n\n"
    "Skills: C, Rust, Linux, 8 years total."
)
add_case(
    id="edge_02_non_english_name",
    kind="edge",
    notes="Non-ASCII candidate and employer names must not break extraction or span citation.",
    resume_text=_r,
    jd_text="Systems Programmer. Must have: C, Linux. Nice to have: Rust.",
    claims=[
        claim(text="Systems Programmer at Reykjavík Data ehf", category="employment",
              quote=_quote(_r, "Systems Programmer, Reykjavík Data ehf (2018-09 to present)"),
              asserted_org="Reykjavík Data ehf", asserted_start="2018-09", asserted_end=None),
        claim(text="C", category="skill", normalized_skill="c", quote=_quote(_r, "C and Rust")),
        claim(text="Rust", category="skill", normalized_skill="rust", quote=_quote(_r, "Rust")),
        claim(text="Linux", category="skill", normalized_skill="linux", quote=_quote(_r, "Linux")),
    ],
    evidence=[],
)

_r = (
    "Grace Miller\n"
    "Defense Software Engineer\n\n"
    "Software Engineer, Classified Program (2017-04 to present). Work is on an air-gapped "
    "network; no public code or artifacts can be shared.\n\n"
    "Skills: C++, Ada, real-time systems, 10 years total."
)
add_case(
    id="edge_03_firewall_only_work",
    kind="edge",
    notes="All work is behind a firewall; nothing is publicly verifiable. Everything unverified, nothing fabricated.",
    resume_text=_r,
    jd_text="Embedded Software Engineer. Must have: C++, real-time systems. Nice to have: Ada.",
    claims=[
        claim(text="Software Engineer on a classified program", category="employment",
              quote=_quote(_r, "Software Engineer, Classified Program (2017-04 to present)"),
              asserted_org="Classified Program", asserted_start="2017-04", asserted_end=None,
              is_verified=False, evidence_type="none"),
        claim(text="C++", category="skill", normalized_skill="c++", quote=_quote(_r, "C++"),
              is_verified=False, evidence_type="none"),
        claim(text="Ada", category="skill", normalized_skill="ada", quote=_quote(_r, "Ada"),
              is_verified=False, evidence_type="none"),
        claim(text="real-time systems", category="skill", normalized_skill="real-time systems",
              quote=_quote(_r, "real-time systems"), is_verified=False, evidence_type="none"),
    ],
    evidence=[],
)

_r = (
    "Hiro Tanaka\n"
    "Developer\n\n"
    "Freelance Developer (2020-01 to present). Various short client contracts.\n\n"
    "Projects: built a personal budgeting app in Flutter and Dart.\n"
    "Skills: Flutter, Dart."
)
add_case(
    id="edge_04_sparse_projects_only",
    kind="edge",
    notes="Sparse resume, skills stated only via a project. Model also emits one uncitable claim the guardrail must discard.",
    resume_text=_r,
    jd_text="Mobile Developer. Must have: Flutter, Dart.",
    claims=[
        claim(text="Freelance Developer", category="employment",
              quote=_quote(_r, "Freelance Developer (2020-01 to present)"),
              asserted_org=None, asserted_start="2020-01", asserted_end=None),
        claim(text="budgeting app in Flutter and Dart", category="project",
              quote=_quote(_r, "built a personal budgeting app in Flutter and Dart")),
        claim(text="Flutter", category="skill", normalized_skill="flutter", quote=_quote(_r, "Flutter")),
        claim(text="Dart", category="skill", normalized_skill="dart", quote=_quote(_r, "Dart")),
    ],
    # The model invents a Kotlin claim quoting text that ISN'T in the resume -> the guardrail
    # must discard it (it should not count as an accepted claim / precision miss).
    model_noise=[
        {"claim_type": "skill", "claim_text": "Kotlin", "normalized_skill": "kotlin",
         "quote": "5 years of Kotlin on Android"},
    ],
    evidence=[],
)

_r = (
    "Isabella Rossi\n"
    "Data Engineer\n\n"
    "Data Engineer, Fjord Analytics (2021-10 to present). Built ETL in Python and dbt on "
    "Snowflake.\n"
    "Analyst, Market Insights (2019-01 to 2021-09).\n\n"
    "Skills: Python, SQL, dbt, Snowflake, Airflow, 5 years total.\n"
    "GitHub: github.com/irossi-data"
)
add_case(
    id="edge_05_partial_github_match",
    kind="edge",
    notes="GitHub verifies only one of several skills; the rest correctly remain unverified (absence never subtracts).",
    resume_text=_r,
    jd_text="Data Engineer. Must have: Python, SQL. Nice to have: dbt, Snowflake, Airflow.",
    claims=[
        claim(text="Data Engineer at Fjord Analytics", category="employment",
              quote=_quote(_r, "Data Engineer, Fjord Analytics (2021-10 to present)"),
              asserted_org="Fjord Analytics", asserted_start="2021-10", asserted_end=None),
        claim(text="Python", category="skill", normalized_skill="python",
              quote=_quote(_r, "Python"), is_verified=True, evidence_type="github"),
        claim(text="SQL", category="skill", normalized_skill="sql", quote=_quote(_r, "SQL")),
        claim(text="dbt", category="skill", normalized_skill="dbt", quote=_quote(_r, "dbt")),
        claim(text="Snowflake", category="skill", normalized_skill="snowflake",
              quote=_quote(_r, "Snowflake")),
    ],
    evidence=[
        evidence(claim_key="python", source_type="github", verdict="verified",
                 url="https://github.com/irossi-data/etl-kit",
                 snippet="Python: 98211 bytes",
                 summary="'python' appears as a primary language in their repo 'etl-kit'."),
    ],
)


# --------------------------------------------------------------------------------------------
# Emit
# --------------------------------------------------------------------------------------------

def _golden_line(case: dict) -> dict:
    return {
        "id": case["id"],
        "kind": case["kind"],
        "notes": case.get("notes", ""),
        "resume_text": case["resume_text"],
        "jd_text": case["jd_text"],
        "ground_truth_claims": [
            {
                "text": c["text"],
                "category": c["category"],
                "is_verified": c["is_verified"],
                "evidence_type": c["evidence_type"],
                "is_fabricated": c["is_fabricated"],
                "normalized_skill": c["normalized_skill"],
            }
            for c in case["claims"]
        ],
    }


def _fixture(case: dict) -> dict:
    extracted = []
    for c in case["claims"]:
        if not c["model_extracts"]:
            continue  # a claim the model missed -> absent from recorded output
        extracted.append(
            {
                "claim_type": c["category"],
                "claim_text": c["text"],
                "normalized_skill": c["normalized_skill"],
                "asserted_years": c["asserted_years"],
                "asserted_start": c["asserted_start"],
                "asserted_end": c["asserted_end"],
                "asserted_org": c["asserted_org"],
                "quoted_source_text": c["quote"],
            }
        )
    for n in case.get("model_noise", []):
        extracted.append(
            {
                "claim_type": n["claim_type"],
                "claim_text": n["claim_text"],
                "normalized_skill": n.get("normalized_skill"),
                "asserted_years": n.get("asserted_years"),
                "asserted_start": n.get("asserted_start"),
                "asserted_end": n.get("asserted_end"),
                "asserted_org": n.get("asserted_org"),
                "quoted_source_text": n["quote"],
            }
        )
    return {"extracted_claims": {"claims": extracted}, "evidence": case.get("evidence", [])}


def main() -> None:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    seen = set()
    with DATASET_PATH.open("w", encoding="utf-8") as fh:
        for case in CASES:
            if case["id"] in seen:
                raise AssertionError(f"duplicate case id: {case['id']}")
            seen.add(case["id"])
            fh.write(json.dumps(_golden_line(case), ensure_ascii=False) + "\n")
            (FIXTURE_DIR / f"{case['id']}.json").write_text(
                json.dumps(_fixture(case), ensure_ascii=False, indent=2), encoding="utf-8"
            )
    kinds = {}
    for case in CASES:
        kinds[case["kind"]] = kinds.get(case["kind"], 0) + 1
    print(f"Wrote {len(CASES)} cases to {DATASET_PATH.relative_to(EVALS_ROOT.parent)}")
    print(f"Wrote {len(CASES)} fixtures to {FIXTURE_DIR.relative_to(EVALS_ROOT.parent)}/")
    print(f"Buckets: {kinds}")


if __name__ == "__main__":
    main()
