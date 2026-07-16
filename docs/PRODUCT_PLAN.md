# Evidence-First Hiring Verification — Product & Technical Plan

> Working name: **Corroborate** (placeholder). The noun that matters is **evidence**.
>
> Status: plan, pre-build. Author: product/architecture review of `maheshh-v/Resume-analyzer`.

---

## 0. TL;DR of the argument

Generative AI destroyed the two signals hiring has always run on: **the resume** and **the remote interview**. ~74% of resumes at top employers now contain AI-generated content, ~88% contain logical inconsistencies, 38.5% of candidates get flagged for AI assistance during live interviews, and deepfake attempts in hiring rose ~1300% YoY. Meanwhile 62% of hiring professionals admit candidates are now better at faking than they are at catching it.

Every incumbent ATS (Greenhouse 2012, Lever 2012, Workable 2012, Ashby 2018) was architected before this. They score claims. **Scoring fiction faster is not a product.**

The wedge: **stop scoring claims, start corroborating them.** Every line on a resume is a *claim*. Each claim gets a verdict — Verified / Partial / Unverified / **Contradicted** — and every verdict carries a clickable citation to the artifact that produced it. No citation, no verdict.

And the non-obvious part: **refusing to emit a score is not just good product taste — it is the regulatory unlock** that lets a company deploy this without a legal project first. See §3.

---

## 1. Product Vision

> Recruiters should never have to take a resume's word for it.

A hiring team drops in a job description and a stack of resumes. The system returns, per candidate, a **Verified Skill Matrix**: for each thing the job actually requires, what the candidate claims, what evidence exists, where that evidence lives, and — critically — **what could not be verified**.

The product does not decide. It **removes the guessing** and hands a human a decision that is now cheap to make and expensive to get wrong.

Three-year vision: the evidence layer that sits under any ATS. The ATS tracks candidates through stages; we tell you whether what's written on them is true.

---

## 2. Problem Statement

**For** engineering hiring managers and small talent teams at 20–200 person tech companies,
**who** receive hundreds of applications per role and cannot tell which claims are real,
**the problem is** that resumes are unverified self-reports and AI has made them both universally polished and universally untrustworthy — so screening has collapsed into pattern-matching on prose that a language model wrote.

The observable symptoms:

| Symptom | Evidence |
|---|---|
| Screening effort is enormous and yields nothing | 73% of orgs using AI recruiting tools report *minimal* improvement in candidate quality despite ~$340k/yr spend; time-to-hire is **up 23%** since 2024 |
| The resume itself is now fiction | ~3 in 4 resumes at top employers contain AI-generated content; 9 in 10 have logical inconsistencies (overlapping dates, impossible tenure) |
| The interview no longer discriminates | 38.5% of candidates flagged for AI-cheating across 19,368 live interviews; rate tripled 9%→45% in three months of late 2025 |
| Nobody can tell | Humans detect deepfakes at 55.5% accuracy — a coin flip |

The manual work that remains, everywhere, today: **a human opening GitHub in a second tab and squinting at it.** That is the thing to automate. Not the ranking — the *looking*.

---

## 3. Why companies would buy it — and the legal unlock

### 3.1 The honest ROI

An engineering manager screening 200 applicants at ~10 minutes each burns **33 hours** — and at the end still does not know who can actually code. They then run four 45-minute technical screens to find out, three of which are wasted.

This product returns the 33 hours *and* replaces two of those wasted screens with evidence. For a team hiring 10 engineers/year, that is roughly 300+ hours of senior engineering time. At loaded cost, the tool pays for itself on the first hire.

### 3.2 The unlock: stay outside the AEDT definition

This is the most important design decision in the document, and it is why your instinct to avoid scores was right for reasons beyond taste.

**NYC Local Law 144** (in force, enforced since July 2023) requires any **Automated Employment Decision Tool** to have an *annual independent bias audit*, a *publicly posted audit summary*, and *10 business days' candidate notice*. An AEDT is defined as a tool that produces a **"simplified output"** — a **score, tag, classification, or ranking** — that **"substantially assists or replaces discretionary decision making."** "Substantially assists" means: sole basis for the decision, **or** weighted more than any other criterion, **or** capable of overruling human conclusions.

Now read your original spec back:

> Overall Match … Recommendation: Proceed / Hold / Reject

That is a simplified output plus a recommendation. **That is an AEDT, textbook.** A customer in NYC could not switch it on without first commissioning a third-party audit. Your answer to *"can our company use this?"* becomes *"yes, after a six-week compliance project."* Which means: no.

The exclusion clause is the opening. LL144 explicitly excludes tools that do not substantially assist discretionary decision-making, naming *"a database, data set or **other compilation of data**."* **A cited evidence matrix with no score, no ranking, and no verdict is a compilation of data.** The human reads it and decides.

So:

| Cut | Replace with | Why |
|---|---|---|
| Overall Match % | **Evidence coverage**: "8 of 11 requirements have supporting evidence" | A count of artifacts is a fact about *documents*, not a score of a *person* |
| Auto Proceed/Hold/Reject | **Human picks, system records** who decided, when, and why | Produces the audit trail; satisfies EU AI Act Art. 14 human-oversight; generates your training data |
| Candidate ranking | Sort by evidence coverage, **explicitly labelled as a document count, not a quality order** | Ranking *is* a simplified output |

The same design pre-satisfies the **EU AI Act**, where hiring AI is Annex III **high-risk** (fines to €15M / 3% of global turnover). Obligations for high-risk employment systems were **postponed from 2 Aug 2026 to 2 Dec 2027** by the AI Digital Omnibus agreement — so there is room, but the human-oversight, transparency, and logging requirements are exactly what this architecture already produces as a byproduct.

**Caveat, stated plainly: I am not a lawyer and this is not legal advice.** The argument is strong and it is the right architecture regardless. But "we designed the output to sit outside the AEDT definition" is a *design intent*, not a legal opinion, and you should say it that way in an interview too — that phrasing is itself the senior signal.

### 3.3 Deployability as a feature

"Can our company use this tomorrow?" has a specific technical meaning:

- `docker compose up` — **two containers**, app + Postgres. Nothing else.
- **Bring your own LLM key.** You never hold their data or their bill.
- **Their Postgres, their disk.** No candidate PII leaves their infrastructure except the LLM call itself (and that endpoint is configurable — point it at Bedrock/Azure/vLLM and nothing leaves at all).
- No Pinecone account, no Redis, no vendor lock-in, no seat licence.

That is a real, checkable answer. Most portfolio projects cannot make it.

---

## 4. Target users

**Primary buyer & user (build for exactly this person):** the **engineering hiring manager or technical founder at a 20–200 person company** hiring 5–30 engineers/year, with no recruiting-ops function. They personally screen. They feel every one of the 33 hours. They already have an ATS they don't love and won't rip out. They can run Docker.

**Secondary:** the one-person talent team at the same company, who needs to hand the EM a shortlist that survives scrutiny.

**Explicitly NOT the target:**

- **Enterprise (1000+).** Requires SOC 2, DPA, procurement, security review, 9-month sales cycle. A solo developer cannot serve them, and building for them adds RBAC/SSO/audit-console work that buys you nothing on either goal.
- **Staffing agencies.** Volume-driven; they want throughput, not truth. Wrong incentive — they are paid to place, not to verify.
- **Non-technical roles.** The evidence sources (code, artifacts) don't exist. Stay in technical hiring where verification is possible. This is a *feature* of the scope, not a limitation.

---

## 5. Competitive read — what to learn, what to avoid

| Player | Does well | Where it fails / your opening |
|---|---|---|
| **Greenhouse / Lever / Workable** | Workflow, compliance, integrations. Greenhouse has 400+ integration marketplace. | Built 2012 — they are *systems of record*, not systems of truth. They track claims, never test them. They will never build this; it's off-thesis for them. **They are your distribution partner, not your competitor.** |
| **Ashby** | Best-in-class analytics, modern UX, loved by technical teams | Still measures *funnel*, not *truth*. Analytics on unverified inputs. |
| **Mercor** | Genuinely close to your idea: ingests resume + GitHub/LinkedIn, generates targeted questions, rewards specificity | It's a **marketplace** — they own the candidate relationship and sell you the person. A company cannot run it on *their own* pipeline. Also scores **delivery signals — "clarity, pacing"** — which is an accent/disability disparate-impact landmine (see §13.4). |
| **Micro1** ("Zara") | AI screening + certification | Marketplace again. You are not for sale — you are for deployment. |
| **HeyMilo / Apriora** ("Alex") | Conversational AI pre-screens, ATS write-back, 24/7 | **Generic questions from a configured bank.** Not grounded in the candidate's own artifacts → directly defeatable by a second window with ChatGPT. They verify nothing; they just automate the *asking*. |
| **LinkedIn Recruiter AI** | Distribution, graph | Sourcing, not verification. Different problem. |
| **Proctoring vendors (Sherlock etc.)** | Detect cheating | Adversarial arms race, creepy, high false-positive rate. **Do not compete here.** Sidestep it (§13.3). |

**The gap nobody occupies:** every one of them produces a *score*. Not one produces a **citation**. And not one will tell you *"we could not verify this — ask about it yourself."* Honesty is an unclaimed market position.

**Do not copy:** the marketplace model (you'd be selling people), live scheduling (zero AI value, enormous complexity), proctoring, sourcing, delivery/accent scoring.

---

## 6. Exact MVP scope

Your chain was right. Here it is with four changes that make it cohere:

```
YOURS:  Import → JD match → GitHub verify → AI interview → Skill matrix → Report

MINE:   JD first → Claim extraction → Free evidence pass → Targeted interview
                                          ↓                       ↓
                                   (GitHub + internal        (only the gaps
                                     consistency)             that matter)
                                          ↓
                              Verified Skill Matrix → Human decides (recorded)
```

**Change 1 — JD first, not import first.** The JD defines what is worth verifying. Verifying a skill the job doesn't need is pure cost. This alone cuts LLM spend several-fold and focuses every downstream stage.

**Change 2 — "resume parsing" → "claim extraction."** Not cosmetic. It changes the data model: every row is a *claim* with a source span pointing back into the PDF. The product is one noun, and the schema should say so.

**Change 3 — add an internal-consistency pass.** Free, universal, zero API cost, works for the 100% of candidates who don't have usable GitHub. Overlapping employment dates, impossible tenure vs. graduation, "5 years of Kubernetes" on a 3-year career, a skills section listing 40 technologies none of which appear in any job description. **9 in 10 resumes have these.** Nobody surfaces them. This is the cheapest evidence in the product and it fills the GitHub recall gap.

**Change 4 — the interview targets *unverified* claims only.** This is the keystone. GitHub already proved Docker? Don't spend a question on Docker. The evidence stage *writes the interview*. That's what makes the pipeline a pipeline instead of five features in a trenchcoat.

### The MVP, concretely

1. **Create a job.** Paste JD → extract structured requirements (skill, importance, years, must-have vs nice-to-have, what evidence would satisfy it).
2. **Bulk-upload resumes.** PDF + DOCX, drag a folder. Dedupe by content hash.
3. **Claim extraction.** Resume → structured claims, each with a source span.
4. **Free evidence pass** (no human, runs automatically):
   - GitHub, *if* a profile is found and *if* it has substance
   - Internal consistency check
5. **Interview invite.** One tokenised link per candidate. Async, text, ~8 questions, ~20 min. Questions grounded in *their* artifacts, targeting *their* unverified JD-critical claims.
6. **Verified Skill Matrix + report.** Every verdict cited. Contradictions surfaced. Unverifiable items named.
7. **Human decision, recorded.**

### Definition of done for the MVP

Not "it runs." It ships when:

- [ ] 30-resume labelled eval set exists; extraction precision/recall measured and in the README
- [ ] **Citation validation is automated: every evidence URL resolves and every source span actually contains the quoted text.** A hallucinated citation is a product-ending bug — see §11.4
- [ ] Cost and p50/p95 latency per candidate are measured and published
- [ ] `docker compose up` works on a clean machine from the README alone
- [ ] No score, no ranking, no auto-verdict anywhere in the output

---

## 7. Features to REMOVE

Including — especially — things you already built. This is the hardest section and the most valuable.

| Remove | Why |
|---|---|
| **The RAG / vector search pipeline** (`qa_chain.py`, `data_ingestion.py`, `pinecone_client.py`, `text_splitter.py`) | See §8.1. This is your current product's core and it is architecturally wrong for the new one. |
| **Pinecone** | An external dependency, a recurring bill, a data-residency objection in every security review — for a problem you no longer have. |
| **Single Resume Q&A chat** | Chat is *work*. Recruiters don't want to ask questions, they want the answers already on the page. An unbounded chatbox has no workflow, no completion state, and nothing to act on. It's the cool demo nobody opens twice. |
| **Overall match score** | §3.2. Legal trap and it's the thing every competitor already does badly. |
| **Auto Proceed/Hold/Reject** | §3.2. The moment you emit a verdict you own the discrimination claim, and you've handed away the audit trail. |
| **Google Forms import** | Zero buyer value. Nobody has ever chosen a hiring tool for this. |
| **Excel import** | "Save as CSV." No buyer cares. Don't own a parser you don't need. |
| **Voice/video interview** | See §13.4. Adds STT cost, latency, **accent and disability disparate-impact risk**, and improves technical signal by ~nothing. Text is cheaper, fairer, and auditable. This is a *deliberate* differentiator, not a shortcut. |
| **Live interview scheduling** | Calendar integration hell. Zero AI value. Async link is strictly better for both sides. |
| **Sourcing, HRMS, payroll, CRM, analytics dashboard** | Correctly excluded in your brief. Holding the line. |
| Streamlit session-state as storage | A refresh destroys the recruiter's work. Not a product. |

---

## 8. What happens to the existing repo

You asked me not to throw away working code. Here is the honest accounting — because the useful version of that instruction is *"don't rewrite for fashion,"* not *"keep code that's solving a different problem."*

**Verdict: 2 of 7 files carry forward. The RAG core does not. But the learning does, and the judgment call itself is resume-grade.**

| File | Fate | Reason |
|---|---|---|
| `utils/text_extraction.py` | **Keep & extend** | PyMuPDF extraction is solid. Add: DOCX, OCR fallback for scanned PDFs, and **character offsets** so claims can cite a source span. |
| `utils/llm_client.py` | **Keep the pattern, generalise** | The OpenAI-compatible-client-pointed-at-any-base-URL pattern is genuinely good and is exactly what "BYO key / point it at Bedrock" needs. Promote it to a provider-agnostic client with retries, timeouts, structured-output parsing, and token/cost accounting. |
| `app.py` | Retire | Streamlit cannot host a tokenised candidate-facing interview portal, has no auth, no roles, no background jobs, and stores state in RAM. |
| `utils/qa_chain.py` | Retire | §8.1 |
| `utils/data_ingestion.py` | Retire | Embedding/upsert for a pipeline that no longer exists |
| `utils/pinecone_client.py` | Retire | Dependency removed |
| `utils/text_splitter.py` | Retire | Nothing to chunk |
| `requirements.txt` | Rewrite | Drop pinecone, sentence-transformers, langchain, cross-encoder. The dependency tree collapses dramatically — that's the deployability win, visible in the diff. |

### 8.1 Why the RAG pipeline must die (the important argument)

Three independent reasons, any one of which is sufficient:

1. **RAG solves a problem you don't have.** Retrieval exists because the corpus doesn't fit in context. A resume is 2–4 pages — roughly 3k tokens. Modern context windows hold it **fifty times over**. You are paying an embedding model, a vector DB, a cross-encoder, and a lossy chunking step to solve a problem that does not exist. Feed the whole document and ask for structured output.

2. **Chunking destroys the exact structure you need.** An 800-character chunk with 80 of overlap will happily sever "Senior ML Engineer, 2021–2023" from the TensorFlow bullet three lines below it. But *"which role was TensorFlow used in, and for how long"* is the entire question. RAG shreds the document into pieces and then asks the LLM to guess how they fit back together. Structured extraction over the whole document preserves the relationships **because they were never broken.**

3. **The killer: cosine similarity is not evidence.** This product's entire promise is *"here is why, click the link."* A vector search cannot answer "why did this match?" — the honest answer is "0.83 cosine distance in a 384-dimensional space," which is not something you can show a recruiter, a candidate, or a court. Retrieval is fundamentally **unciteable**, and this product is **only** citations. Vector search is not merely suboptimal here; it is *anti-thetical to the thesis*.

Structured extraction into Postgres JSONB gives you exact filters (`requires Python AND 3+ years in a role after 2022`), full explainability ("matched: 'Python' in Experience §2, chars 1420–1426"), zero embedding cost, and one fewer container.

Vectors earn their place in exactly one future scenario: semantic search over a **talent pool of thousands** ("who from past applicants looks like this new JD?"). That is post-MVP, and when it arrives the answer is **pgvector in the Postgres you already run** — not a second vendor.

> **This is the strongest thing you will say in an interview.** "I deleted the RAG pipeline I'd built, because retrieval isn't evidence and my product is only evidence." Engineers who can delete their own work for a stated reason are rare, and every senior interviewer is listening for exactly that. It is worth more than the pipeline was.

---

## 9. Architecture

Deliberately boring. The novelty budget is spent entirely on the evidence pipeline.

```
┌─────────────────────────────────────────────────────────┐
│  Container 1: app  (FastAPI, Python 3.12)               │
│                                                          │
│  /recruiter/*   Jinja + HTMX + Tailwind (server-rendered)│
│  /interview/{token}  candidate portal (no login)         │
│  /api/*         JSON                                     │
│                                                          │
│  ┌────────────────────────────────────────────────┐     │
│  │ pipeline/                                       │     │
│  │   extract_jd.py       → requirements            │     │
│  │   extract_claims.py   → claims + source spans   │     │
│  │   evidence/github.py  → verdicts + citations    │     │
│  │   evidence/consistency.py → contradictions      │     │
│  │   interview/generate.py → grounded questions    │     │
│  │   interview/score.py    → per-claim evidence    │     │
│  │   report.py             → matrix assembly       │     │
│  └────────────────────────────────────────────────┘     │
│                                                          │
│  worker: same image, `SKIP LOCKED` poll loop on Postgres │
│  llm_client.py → any OpenAI-compatible base_url          │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│  Container 2: postgres 16                                │
│  relational + JSONB + job queue (FOR UPDATE SKIP LOCKED) │
└──────────────────────────────────────────────────────────┘

External (all optional / BYO): LLM endpoint, GitHub API token
```

**Decisions and their reasons:**

- **FastAPI, not Streamlit.** Not fashion — three hard blockers: (a) the candidate interview needs an unauthenticated tokenised URL, which Streamlit cannot serve; (b) GitHub + LLM work takes minutes and must survive a browser close; (c) recruiter work must persist across a refresh. Streamlit fails all three. This is the one rewrite with a strong technical reason, which is the bar you set.
- **HTMX + Jinja, not React/Next.** You are applying for **AI Engineer** roles. Nobody will ask about your state management. HTMX ships this UI in a third of the time, needs no node build step, and keeps it one container. Every hour spent on a SPA is an hour not spent on the evidence pipeline — which is the entire reason anyone would hire you or buy this. *(If you later want the SPA for its own sake, the `/api/*` layer is already there. Don't do it first.)*
- **Postgres as the job queue.** `SELECT … FOR UPDATE SKIP LOCKED` is a completely legitimate queue up to ~thousands of jobs/min. Celery + Redis would add two containers and one more thing that breaks in a customer's environment, to solve a problem you will never reach. **"Two containers" is a feature you are selling.**
- **No Pinecone, no LangChain.** Direct SDK calls. LangChain's abstractions cost you the control you need over structured output and cost accounting, and add a large dependency surface to every security review.
- **Model tiering.** `llama-3.1-8b-instant` is too weak for structured claim extraction and interview reasoning — it will hallucinate spans, and a hallucinated span is a product-ending bug (§11.4). Use a strong model (Claude Sonnet 4.5 class) for extraction / question generation / answer scoring; keep a cheap fast model for classification-shaped steps (is this a GitHub URL, is this repo a tutorial clone). Configure both by env var. **BYO key means model spend is the customer's, which is also why they'll let you use a good one.**

---

## 10. Database design

The schema encodes the philosophy: **there is nowhere to store a score.** That's deliberate — it makes the product thesis structurally enforced rather than culturally remembered.

```sql
organizations (id, name, created_at)
users         (id, org_id, email, role, ...)          -- role: admin | recruiter

jobs              (id, org_id, title, jd_raw, jd_text, created_by, created_at)
job_requirements  (id, job_id, skill, category, importance,   -- must_have | nice_to_have
                   min_years, evidence_criteria, source_span)
                  -- ^ extracted from the JD; defines what is worth verifying

candidates  (id, org_id, name, email, github_login, linkedin_url, created_at)
documents   (id, candidate_id, kind, filename, content_hash,   -- dedupe
             storage_path, extracted_text, page_offsets, created_at)

-- ═══ the heart ═══
claims (
  id, candidate_id, document_id,
  claim_type,        -- skill | employment | education | project | credential
  claim_text,        -- "3 years TensorFlow"
  normalized_skill,  -- "tensorflow"
  asserted_years, asserted_start, asserted_end, asserted_org,
  source_span_start, source_span_end,   -- MUST resolve into documents.extracted_text
  extractor_model, prompt_version, created_at
)

evidence (
  id, claim_id,
  source_type,   -- github | consistency | interview
  verdict,       -- verified | partial | unverified | contradicted
  confidence,    -- calibration only; never surfaced as a score
  summary,       -- one human sentence
  artifact_url,  -- MUST resolve (§11.4)
  artifact_snippet,
  model, prompt_version, raw_response_id,
  created_at     -- APPEND ONLY. never updated, never deleted.
)
-- CHECK (artifact_url IS NOT NULL OR source_type = 'consistency')
--   ^ no citation, no evidence. enforced in the database.

-- ═══ interview ═══
interviews (id, candidate_id, job_id, token UNIQUE, status,
            invited_at, started_at, submitted_at, expires_at)
interview_questions (id, interview_id, ordinal,
                     targets_claim_id,      -- ← every question earns its place
                     question_text, grounding_artifact_url,
                     rubric,                -- written BEFORE the answer exists
                     rationale)             -- shown to the recruiter
interview_answers (id, question_id, answer_text,
                   time_to_first_keystroke_ms, total_time_ms,
                   paste_event_count, revision_count,
                   specificity_notes, review_flags)  -- flags → human, never auto-reject

-- ═══ the human ═══
decisions (id, candidate_id, job_id, decided_by_user_id,
           verdict, rationale, created_at)   -- ← the ONLY verdict in the system
audit_log (id, org_id, actor_user_id, action, entity, entity_id, payload, created_at)
```

**Four load-bearing properties:**

1. **`evidence` is append-only.** You can reconstruct exactly what the system knew at any past moment. That is what makes it defensible if a rejected candidate ever asks why — and the EU AI Act will eventually require exactly this.
2. **`model` + `prompt_version` on every inferred row.** Any verdict is reproducible months later. This is the single most senior thing in the schema and it costs two columns.
3. **No `candidates.score` column exists.** By construction. §3.2.
4. **`decisions` is the only place a verdict lives, and it has a `user_id`.** A human made it. The system recorded it. That's the whole compliance posture in one table.

---

## 11. AI pipeline

Six stages. Each is a separate, independently testable, independently cacheable function. Nothing is a chain of prompts pretending to be reasoning.

### 11.1 JD → requirements
Whole JD in context → structured output. Extract skill, must-have vs nice-to-have, min years, and **`evidence_criteria`**: *what would actually satisfy this?* That last field is what makes the rest of the pipeline possible — it's the spec for the evidence hunt.
Human-in-the-loop: the recruiter **reviews and edits** the extracted requirements before anything runs. 30 seconds of their time, and it fixes the garbage-in problem permanently. Every failure downstream traces back to a bad JD read.

### 11.2 Resume → claims
Whole document in context (it fits — §8.1). Structured output. **Every claim must carry `source_span_start/end` that resolves into the extracted text.** Validated programmatically, not trusted (§11.4).

### 11.3 Evidence pass (parallel, per candidate)
- **`consistency`** — pure Python, zero LLM cost, runs for **everyone**: date overlaps, impossible tenure, years-claimed vs. career length, skills that appear in the skills list but in no role. Deterministic, explainable, free.
- **`github`** — §13. Runs only when a profile with substance exists.
Both write `evidence` rows keyed to specific claims.

### 11.4 Citation validation — the guardrail
> This is the single most important engineering artifact in the project, and the thing to lead with in an interview.

**A hallucinated citation is worse than no product.** If the report says "verified — see line 14" and line 14 says nothing of the sort, you have automated the manufacture of false confidence about a human being's career. That is a genuinely harmful failure, not a bug.

So, mechanically, before any evidence row is written:
- `artifact_url` must return HTTP 200
- `artifact_snippet` must be a **literal substring** of the fetched artifact
- `source_span` must be a **literal substring** of `documents.extracted_text`
- fail → the row is **discarded and the claim degrades to `unverified`**, never to a verdict

Measure and publish **hallucinated-citation rate**. Target: zero, structurally enforced. This is the difference between "I used an LLM" and "I engineered an LLM system," and it is exactly what an AI Engineer interview is probing for.

### 11.5 Question generation → §14
### 11.6 Answer scoring → §14

**Cross-cutting:**
- **Cache by `content_hash + prompt_version`.** Re-running a candidate costs nothing. Re-running your whole eval set after a prompt change costs one candidate's worth of tokens.
- **Cost/latency budget:** target < $0.15 and < 90s per candidate for stages 11.1–11.4. Measure it, publish it in the README. Nobody does this and it reads as production experience because it is.
- **Eval harness from day one.** 30 hand-labelled resumes, ground-truth claims. Track extraction P/R, citation-resolution rate, contradiction false-positive rate. **Prompts are code; they need tests.** When an interviewer asks "how do you know it works?" — this is the answer, and most candidates don't have one.

---

## 12. Candidate verification pipeline

The mental model to hold: **precision over recall, always, and absence is never guilt.**

Every claim lands in one of four states:

| Verdict | Meaning | Example |
|---|---|---|
| **Verified** | Independent artifact corroborates it | 47 commits authored by them across 8 months in a repo whose `requirements.txt` pins `tensorflow==2.15` |
| **Partial** | Some support, doesn't reach the claim | Claims 3 years Docker; a Dockerfile exists in one repo, 2 months of activity |
| **Unverified** | No evidence either way — **the default, and not a negative** | Claims Kubernetes; no public artifact. Most claims land here. |
| **Contradicted** | Evidence actively conflicts | Claims "led backend at X, 2021–2023"; X's public repos show no commits from them; resume elsewhere says they were at Y in 2022 |

**Two rules that define the product's ethics, and its legal exposure:**

1. **`unverified` is the honest default and must never be styled as failure.** Most engineers' best work is behind a corporate firewall — permanently unverifiable, and that says nothing about them. The UI must present unverified neutrally (grey, not red) and route it to *"ask about this yourself."*
2. **Absence of evidence never subtracts.** Nothing in the system may penalise a missing GitHub, a missing profile, a thin public footprint. This is not politeness — public-artifact volume correlates with free time, which correlates with caregiving, class, and health. **Penalising absence builds a disparate-impact engine that would fail exactly the bias audit you designed the product to avoid needing.** Enforce it in code: evidence rows can only ever *add*.

**`contradicted` is the money shot.** It is the one output no competitor produces, and the one a recruiter acts on within seconds. Given 9 in 10 resumes contain logical inconsistencies, it will fire often — which is exactly why it needs a punishing false-positive bar. **A false "contradicted" can cost someone a job.** Rules: deterministic checks only where possible; the specific conflicting spans always shown side by side; the word "contradicted" describes *the documents*, never the person — "these two statements conflict," never "the candidate lied." Any ambiguity degrades to `unverified`.

---

## 13. GitHub verification strategy

### 13.1 Reset the expectation first

**83% of GitHub users pushed no code in the last year. 88% have no followers.** Most engineers' real work is behind a firewall. Analysts who do this for a living are blunt: GitHub *"works, but only for a narrow slice of technical hiring — a signal layer, not a database."*

So GitHub **cannot be a pillar**, and Step 3 of your flow has to be demoted. It is a **high-precision, low-recall, opportunistic** source: when it fires it is gold; when it doesn't it must mean **exactly nothing**.

Which raises the real question your flow doesn't answer: *what verifies the majority?* Two answers, and they're the reason the plan re-orders your chain:
- the **consistency pass** (free, universal), and
- **the interview** — the only evidence source every candidate has. Which is why it's the load-bearing wall, not step 4 of 6.

### 13.2 The reframe that makes GitHub valuable anyway

> **GitHub's highest use is not verification. It is interview fuel.**

Verifying "they know Docker" from a Dockerfile is weak evidence — anyone can copy a Dockerfile. But *reading* their Dockerfile lets you ask:

> *"In `yourrepo/Dockerfile` you install dependencies before copying source, then copy the whole tree in one layer. Walk me through the caching behaviour you were going for, and what you'd change."*

That question is **unanswerable by ChatGPT in a second window** — the model has never seen that repo, and the answer requires knowing why *you* did it. It is unfakeable, un-Google-able, and takes ten seconds for a real author to answer. It is simultaneously the best signal in the product **and** the strongest anti-cheating measure — without a single second of creepy proctoring.

This is where GitHub + interview compose into something no competitor has: they generate questions from a *bank*; you generate them from the candidate's *own code*.

### 13.3 Signals — evidence, not vanity

**Ownership first** (your instinct, and it's where naive tools fail):
- Is it a **fork** with no meaningful commits from them? → **no evidence.** A starred fork proves taste, not skill.
- Commits *authored by them*, matched via login and the resume's email — not just repo membership.
- **Authorship share**: what % of the repo's substantive commits are theirs? "Contributed to a 40k-star project" is usually one typo fix in the README.

**Substance:**
- **Does the claimed tech actually appear?** Parse `requirements.txt` / `package.json` / `go.mod` / `pyproject.toml`. **A pinned dependency is far stronger proof of "uses TensorFlow" than the resume's skills section** — and it's a cheap, deterministic, citeable check.
- Sustained vs. dumped: commits across months, or one 400-file initial commit? (One-shot dumps often mean a tutorial followed, or code moved from elsewhere.)
- Engineering maturity: tests present, CI config, README that explains *why*, commit messages that are sentences.
- **Tutorial/clone detection** — is this the 400,000th "build a chat app with React" course project? Compare structure and filenames against known template/tutorial repos. **A tutorial clone is not evidence of anything**, and detecting it is a signal no competitor bothers with.

**Explicitly ignored — the anti-vanity list** (your instinct was right, this is the whole point):
> stars · followers · total repo count · contribution-graph streaks · profile README aesthetics · org memberships

These measure *popularity and free time*, not skill, and every one of them is a demographic proxy. Say this out loud in the product UI. It's a trust win and it's true.

### 13.4 Mechanics
- Discover: regex the resume for a GitHub URL; let the candidate add one at interview time. **Never guess from their name** — wrong-person attribution is a catastrophic, silent failure mode.
- API: REST/GraphQL with the org's PAT (5,000 req/hr vs. 60 unauthenticated).
- **Never clone.** Metadata + language bytes + manifest files + a handful of sampled source files. Keeps it seconds, not hours, and keeps the cost line honest.
- Cache by repo SHA. Re-analysis is free.
- Every verdict cites a **permalink pinned to a commit SHA** — not a branch URL, which rots.
- Post-MVP: GitLab, published papers, patents. Same contract: cite or don't claim.

---

## 14. Personalized interview strategy

The research floor: **structured interviews are the single most predictive selection method known** (r ≈ .51 Schmidt-Hunter; r ≈ .42 in Sackett's 2023 re-analysis — top of the table either way), and they beat unstructured by ~30%. Structure is what buys the validity. So: **rubric written before the answer exists.** Non-negotiable.

### 14.1 Shape
- **Async, tokenised link.** No scheduling. Candidate does it on their time.
- **Text, not voice.** Deliberate, and worth defending: voice adds STT cost, latency, and — critically — the temptation to score *delivery*. **Mercor scores "clarity, pacing, delivery."** Scoring how someone *sounds* is an accent, ESL, and disability disparate-impact claim wearing a lab coat. **Score content. Never delivery.** Text makes that a structural guarantee rather than a promise, and it's fairer, cheaper, and auditable. This is a feature.
- **~8 questions, ~20 minutes, hard cap.** Candidate time is not free, and respecting it is a real complaint in every survey.
- **Every question earns its place**: `targets_claim_id NOT NULL`. A question that doesn't test an unverified, JD-critical claim doesn't ship.

### 14.2 Generation
For each claim where `importance = must_have` **AND** verdict ∈ {`unverified`, `partial`} — ranked by JD importance, top ~8:
1. Ground it in their most specific available artifact — their repo file > their project description > their claim text.
2. Ask for a **decision and its tradeoff**, never a definition. *"Why did you choose X over Y in Z, and what broke?"* — never *"What is Docker?"* Definitions are what ChatGPT is for.
3. Write the **rubric first**: what would a real practitioner mention? What would a bluffer miss?
4. Store the **rationale** and show it to the recruiter. They must be able to see *why* this question was asked — otherwise it's a black box, and black boxes are what you're differentiating against.

### 14.3 Adaptive drill-down
Vague answer → one specificity probe. That's it — one, not an interrogation. Mercor's own finding matches the theory: **specific answers (numbers, team sizes, timeframes, named technologies, failure modes) separate cleanly from fluent ones.** LLM-generated answers are reliably fluent and reliably non-specific. Score **specificity**, and you're measuring the exact axis where generated text fails.

### 14.4 Anti-cheating — the honest position

> **This cannot be made cheat-proof, and you must never claim it is.** Any vendor claiming otherwise is lying, and saying so in an interview will earn you more credit than a fake solution.

38.5% of candidates get flagged; humans catch deepfakes at 55.5%; 62% of hiring pros concede candidates are winning. That arms race is unwinnable and you should not enter it. **Sidestep instead:**

1. **Artifact-grounded questions** (§13.2) — the primary defence, and it's structural. An LLM cannot explain a commit it has never seen. This does more than any proctoring stack.
2. **Specificity rubric** — measures the axis generated text fails on.
3. **Behavioural signals as flags only** — time to first keystroke, paste events, revision count. **These flag for human review. They never auto-reject and never appear as a score.** A false accusation of cheating is a serious harm to a real person, and an auto-rejecting false-positive machine is a lawsuit with a countdown timer.
4. **Frame it honestly in the product**: this is a *screening* tool that produces evidence and interview areas for a human. It is not a hire/no-hire oracle. That framing is the only one that survives contact with reality — and it's the same framing that keeps you outside the AEDT definition (§3.2). The ethics and the compliance and the product truth all point the same direction, which is usually a sign the design is right.

### 14.5 Candidate-side transparency
Disclose AI use up front, state what is evaluated (content, not delivery), offer a human-review path, allow the candidate to add a GitHub/artifact link. Costs a day. Required by the EU AI Act's transparency duty eventually. Buys trust now. **Candidate experience is a competitive axis nobody in AI hiring is contesting** — and it's free to win.

---

## 15. Final hiring report design

One screen. Skimmable in 60 seconds. Every claim clickable to its artifact.

```
┌──────────────────────────────────────────────────────────────┐
│ Priya Sharma  ·  Senior ML Engineer                          │
│                                                              │
│ EVIDENCE COVERAGE   8 of 11 requirements have evidence       │
│ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░                              │
│ ⓘ A count of supporting documents. Not a score, not a        │
│   ranking, and not a measure of this person.                 │
├──────────────────────────────────────────────────────────────┤
│ ⚠ CONFLICTS IN THE DOCUMENTS                        (1)      │
│                                                              │
│   Resume states "Led ML platform at Acme, 2021–2023"         │
│   Resume also states "MS, Stanford, 2022–2024 (full-time)"   │
│   → These two statements overlap. Worth asking about.        │
│     [resume p.1 ln 12] [resume p.2 ln 3]                     │
├──────────────────────────────────────────────────────────────┤
│ VERIFIED SKILL MATRIX                                        │
│                                                              │
│ Requirement    Claim      Verdict      Evidence              │
│ ───────────────────────────────────────────────────────────  │
│ TensorFlow ●   4 yrs      Verified     tf 2.15 pinned; 47    │
│   must-have                            commits/8mo, 91% by   │
│                                        them → repo@a3f9c2 ↗  │
│                                        Interview Q3: named   │
│                                        the retracing bug ↗   │
│                                                              │
│ Docker ●       3 yrs      Partial      Dockerfile in 1 repo, │
│   must-have                            2mo activity ↗        │
│                                        Interview Q5: correct │
│                                        on layers, vague on   │
│                                        multi-stage ↗         │
│                                                              │
│ Kubernetes ●   2 yrs      Unverified   No public artifact.   │
│   must-have                            Not asked — budget.   │
│                                        → Probe this live.    │
│                                                              │
│ RAG ○          "expert"   Verified     Interview Q1: chunk-  │
│   nice-to-have                         ing tradeoffs, named  │
│                                        a failure mode ↗      │
├──────────────────────────────────────────────────────────────┤
│ RECOMMENDED FOR YOUR INTERVIEW                               │
│   1. Kubernetes — claimed 2 yrs, zero evidence either way    │
│   2. Docker multi-stage — answer thinned out under probe     │
│   3. The 2021–2023 / 2022–2024 overlap                       │
├──────────────────────────────────────────────────────────────┤
│ ⚑ 1 item for review: Q5 answer began after a 4-min pause     │
│   followed by a single paste. Not a conclusion — look at it. │
├──────────────────────────────────────────────────────────────┤
│ YOUR DECISION            [ Advance ]  [ Hold ]  [ Decline ]  │
│ Rationale: ______________________________________________    │
│ ⓘ You decide. We record who, when, and why.                  │
└──────────────────────────────────────────────────────────────┘
```

**Design rules, each doing real work:**

- **No overall score. No ranking. No auto-verdict.** §3.2.
- **"Evidence coverage" is annotated as a document count** — in the UI, permanently, not in a tooltip. That sentence is a compliance artifact and a product truth simultaneously.
- **Conflicts sit at the top** — highest-value, most actionable, unique to you.
- **Unverified is grey, never red, and is stated as *our* limitation** ("no public artifact"), not the candidate's deficiency.
- **"Not asked — budget"** is shown. The system admits what it skipped. That honesty is the product.
- **Every ↗ resolves** or the row wouldn't exist (§11.4).
- **The decision box is empty.** A human fills it. That's the whole thesis in one UI element.

---

## 16. Roadmap

**V1 — MVP (target ~8–10 focused weeks solo).** §6. JD → claims → free evidence → targeted interview → matrix → recorded decision. Two containers. Eval harness. Published cost/latency.

**V1.5 — Distribution.** Greenhouse integration first (400+ marketplace = the widest door). **Build against Harvest v3 / OAuth 2.0 directly — v1 and v2 are dead after 31 Aug 2026**, so anything built on Basic Auth is born obsolete. Then Ashby (technical teams, your exact ICP). Write the matrix back as a candidate note. CSV pool import (`name, email, resume_url, github`) lands here too.

**V2 — More evidence, better evidence.** GitLab. Published papers / Scholar. Patents. Public writing. Then the big one: **an optional take-home work sample** — work samples sit at the very top of the validity table (composite .63 with GMA) and are the strongest evidence source that exists. Same contract as everything else: cite or don't claim.

**V3 — The real moat: calibration.** Feed hire outcomes back. Ask the question no vendor in this market can answer: **does "verified" actually predict 6-month performance?** Every competitor sells a score no one has ever validated. If you can show that evidence-backed verification correlates with outcomes — even on modest n — you have the only defensible claim in AI hiring, and the only one a serious buyer's head of talent will care about.

**V4 — Optional, only if a customer demands scoring.** If you ever emit a simplified output, you become an AEDT and you need bias-audit tooling: demographic selection rates, impact ratios, the LL144 artifact pack. **Design it so this stays optional forever.** The moment it's on by default, you've become everyone else.

### 16.1 The moat that shipped in V1: the Evidence Ledger

Calibration (V3) is the *earned* moat — it needs outcomes data and time. The **Evidence Ledger** is the moat you can ship on day one, and it compounds while you wait.

Every consequential action in a candidate's verification — resume fingerprinted, claims extracted, consistency checked, every interview question and answer, the human decision — is appended to a **per-candidate, SHA-256 hash-chained, append-only log**, committed in the same transaction as the action it records. Free text (answers, rationales) is attested by content hash. One endpoint replays the chain and re-verifies every attestation; any post-hoc edit, insertion, or deletion is pinpointed to the exact event.

Why this is a real moat and not a feature:

1. **It's regulatory gravity, monetized.** The EU AI Act puts hiring AI in the high-risk class — record-keeping and traceability are *obligations*, and LL144-style laws keep spreading. Every competitor sells a score they can't explain; you sell a record that survives a lawyer. "Show me how this decision was reached, eight months later, provably unaltered" is a question only this product answers.
2. **It cannot be retrofitted.** A competitor can copy the feature next quarter — but their customers' past decisions are unattested forever. Your customers accumulate tamper-evident decision history from day one; the value of switching away *grows with every candidate processed*. That's the same asymmetry that makes audit-log vendors sticky.
3. **It's honest by construction, which is the brand.** The ledger records what the system did *and* what it skipped, with the model + prompt version on every AI action. The pitch writes itself: *we can't be caught misrepresenting the process, because the process notarizes itself.*

Cost to build: one table, one service module, ~10 emission points, two endpoints. Cost to fake: infeasible after the fact. That ratio is what "smart but powerful" looks like.

**Never build:** sourcing · HRMS · payroll · CRM · analytics dashboards · a chatbot · proctoring · anything that scores how a person sounds.

---

## 17. Positioning this for the two goals

**Goal 2 — "Can our company actually use this?"**
> "Yes. Two containers, your Postgres, your LLM key — no candidate data leaves your infrastructure. And it deliberately emits no score and no automated verdict, so under NYC Local Law 144 it's designed to sit outside the AEDT definition and not trigger the annual bias-audit requirement. A human makes every decision; the system records who and why. You could run it against a live req this week."

That is a real answer. Almost nobody applying to these roles can give one.

**Goal 1 — the interview talking points, ranked by how senior they read:**

1. **"I deleted the RAG pipeline I'd already built."** Retrieval isn't evidence; cosine similarity can't be cited; a resume fits in context fifty times over. Deleting your own work for a stated reason is the rarest signal in engineering.
2. **"The report has no score — for legal reasons."** Walk through the AEDT definition and the "compilation of data" exclusion. Product judgment fused with regulatory literacy is a staff-level move and nobody expects it.
3. **"Missing GitHub can't count against you."** Explain why absence-as-penalty is a disparate-impact engine that correlates with caregiving and class. This is ML fairness understood concretely rather than recited.
4. **"Every citation is validated; hallucination rate is structurally zero."** Substrings must match or the row is discarded. This is the LLM-systems-engineering answer.
5. **"We can't stop cheating, so we made it pointless."** Ask about their commit, not about Docker. Sidestepping an unwinnable arms race with a design choice.
6. **"Here's the eval set, the P/R, the cost and the p95."** The answer to *"how do you know it works?"* — which most candidates cannot answer at all.

**Build the eval harness before the UI.** It's the artifact that separates "I used an LLM" from "I engineer LLM systems," and it's the thing you'll actually be interviewed on.

---

## Sources

- [HBR — AI Has Broken Hiring. Here's How to Fix It.](https://hbr.org/2026/06/ai-has-broken-hiring-heres-how-to-fix-it)
- [SupportFinity — Why Your AI Recruiting Tools Are Still Failing in 2026](https://blog.supportfinity.com/ai-recruiting-tools-failing-2026-talent-intelligence/)
- [HR Dive — What happens when candidates overuse AI](https://www.hrdive.com/news/what-happens-when-candidates-overuse-ai-what-recruiters-can-do/824157/)
- [HR Brew — Well, AI still hasn't solved bias in hiring](https://www.hr-brew.com/stories/2026/04/02/well-ai-still-hasn-t-solved-bias-in-hiring)
- [The Interview Guys — The State of Hiring Fraud 2026](https://blog.theinterviewguys.com/the-state-of-hiring-fraud-2026-when-38-5-of-candidates-are-cheating/)
- [Sherlock AI — Rise of AI Interview Fraud](https://www.withsherlock.ai/blog/rise-of-ai-interview-fraud)
- [NYC DCWP — Automated Employment Decision Tools](https://www.nyc.gov/site/dca/about/automated-employment-decision-tools.page)
- [Perkins Coie — NYC Adopts Final Rules for AEDT Law](https://perkinscoie.com/insights/update/new-york-city-adopts-final-rules-law-governing-automated-employment-decision-tools)
- [Deloitte — NYC Local Law 144-21 and Algorithmic Bias](https://www.deloitte.com/us/en/services/audit-assurance/articles/nyc-local-law-144-algorithmic-bias.html)
- [DLA Piper — Critical audit of NYC's AI hiring law signals increased risk](https://www.dlapiper.com/en-us/insights/publications/2026/01/critical-audit-of-nyc-ai-hiring-law-signals-increased-risk-for-employers)
- [Crowell & Moring — AI and HR in the EU: a 2026 Legal Overview](https://www.crowell.com/en/insights/client-alerts/artificial-intelligence-and-human-resources-in-the-eu-a-2026-legal-overview)
- [DLA Piper GENIE — EU Commission draft guidelines on high-risk AI in employment](https://knowledge.dlapiper.com/dlapiperknowledge/globalemploymentlatestdevelopments/2026/eu-commission-publishes-draft-guidelines-on-high-risk-ai-in-employment)
- [EU AI Act — What the Act Means for Staffing Businesses](https://artificialintelligenceact.eu/what-the-act-means-for-staffing-businesses/)
- [Ben Frederickson — Why GitHub Won't Help You With Hiring](https://www.benfrederickson.com/github-wont-help-with-hiring/)
- [Kula — How to Recruit Top Developers on GitHub in 2026](https://www.kula.ai/blog/github-beginners-guide-source-candidates)
- [Mercor — AI Interview docs](https://talent.docs.mercor.com/support/ai-interview)
- [AceRound — Mercor AI Interview Tips: What the Autonomous AI Actually Scores](https://www.aceround.app/blog/mercor-ai-interview-tips/)
- [HeyMilo — Best AI Recruitment Platforms in 2026](https://www.heymilo.ai/blog/best-ai-recruitment-platforms-in-2026-choosing-the-right-fit-for-your-hiring-team)
- [Truto — How to Integrate with the Greenhouse API](https://truto.one/blog/how-to-integrate-with-the-greenhouse-api-a-guide-for-b2b-saas/)
- [Index.dev — Greenhouse vs Lever vs Ashby (2026)](https://www.index.dev/blog/greenhouse-vs-lever-vs-ashby-ats-comparison)
- [Schmidt & Hunter (1998) — Validity and Utility of Selection Methods (summary)](https://firstpersonnel.org/wp-content/uploads/2013/10/Summary-Schmidt-Hunter-1998.pdf)
- [Pin — Structured Interviews: How to Run Them and Why They Work](https://www.pin.com/blog/structured-interviews-guide/)
