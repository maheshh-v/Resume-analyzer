# Architecture & Implementation Blueprint

> Technical companion to [`PRODUCT_PLAN.md`](./PRODUCT_PLAN.md).
> `PRODUCT_PLAN.md` is the *product thesis* (evidence-first hiring verification, no score, human decides).
> This document is the *technical blueprint* for building it as a live SaaS.
>
> Status: approved plan, pre-build. Stack decisions locked below.

---

## 0. What we are building (one paragraph)

An AI hiring platform whose job is not to *parse* resumes but to *verify* them. A recruiter
creates a job, uploads candidate resumes, and the system extracts every technical **claim**,
matches it against the job's requirements, gathers free supporting evidence (internal
consistency + optional GitHub), then runs an **adaptive AI interview** that grounds each
question in the candidate's own claims and artifacts — questions a second ChatGPT window
cannot answer. It ends with a cited hiring summary. **It never emits a hire/reject decision
or a match score.** A human decides; the system records who, when, and why.

---

## 1. Locked stack decisions

| Layer | Choice | Notes |
|---|---|---|
| Frontend | **Next.js 15** (App Router), TypeScript, TailwindCSS, shadcn/ui, Framer Motion, TanStack Query | Deployed to **Vercel**. Thin by design — ~5 core screens. The moat is the pipeline, not the UI. |
| Backend | **FastAPI**, Python 3.12, Pydantic v2, SQLAlchemy 2.0 (async), Alembic | Deployed to **Railway**. |
| Database + Auth + Storage | **Supabase** (single Postgres) | Auth + Storage + all app tables in one Postgres. Neon dropped. |
| Auth model | **Single recruiter per account** | Every owned row carries `owner_user_id`. No org/team machinery in the MVP. |
| LLM | Provider-agnostic client; **Gemini default, OpenAI fallback** | One env var switches providers. Strong model for extraction/interview reasoning. |
| Observability | **Langfuse** | Traces every LLM call; stores prompt versions tied to `prompt_version` DB columns. |
| Background work | **FastAPI background tasks + a `status` column** | No Celery/Redis. Upgrade path is a Postgres `FOR UPDATE SKIP LOCKED` worker *if ever needed*. |

**Explicitly NOT in the stack:** Pinecone / any vector DB, LangChain, embeddings, a
reranker, Redis, Streamlit. See `PRODUCT_PLAN.md` §8.1 for why RAG is deleted (a resume fits
in context ~50× over; cosine similarity cannot be cited; the product is *only* citations).

---

## 2. Security model (the one nuance that matters)

- The browser talks to **Supabase only for authentication** (supabase-js: sign in, session,
  JWT). It never queries app tables or Storage directly.
- The browser sends the Supabase JWT to **FastAPI**. FastAPI verifies it (Supabase JWKS),
  extracts `sub` → the user id.
- FastAPI is the **only** thing that touches app data and Storage, over a direct
  SQLAlchemy/asyncpg connection using service credentials. **This connection bypasses RLS.**
- Therefore **authorization lives in the API layer**: every query is scoped to
  `owner_user_id == <verified user>`. There is a single dependency that does this; routers
  cannot forget it.
- **RLS policies still exist** as deny-by-default defense-in-depth (owner-only), so any future
  direct-from-browser access is safe by construction. RLS is the backstop, not the gate.

---

## 3. Repository layout (monorepo)

```
/apps
  /web                 Next.js 15 frontend            → Vercel
  /api                 FastAPI backend                → Railway
/packages
  /shared-types        (optional) OpenAPI-generated TS types shared with web
/docs
  PRODUCT_PLAN.md      product thesis
  ARCHITECTURE.md      this file
/eval                  labeled resumes + prompt eval harness (lives with the API)
docker-compose.yml     local Postgres only (Supabase for real; local PG for offline dev)
```

### Backend (`apps/api`)

```
app/
  main.py                     app factory, CORS, router registration, Langfuse init
  config.py                   pydantic-settings (env: SUPABASE_*, GEMINI_*, OPENAI_*, LANGFUSE_*)
  auth/
    dependencies.py           verify Supabase JWT → current_user; scope-to-owner helper
  db/
    session.py                async engine + session
    base.py
  models/                     SQLAlchemy models (see §5)
  schemas/                    Pydantic request/response models
  routers/
    jobs.py                   Job CRUD + JD requirement extraction/edit
    candidates.py             candidate CRUD
    documents.py              resume upload → Storage → extract → claims
    interviews.py             recruiter: invite/generate; PUBLIC: /interview/{token}
    reports.py                hiring summary assembly
  llm/
    client.py                 provider-agnostic: Gemini|OpenAI, structured output, retries,
                              cost accounting, Langfuse spans, prompt_version tagging
    prompts/                  versioned prompt templates (prompts are code)
  pipeline/
    extract_jd.py             JD text  → structured requirements (+ evidence_criteria)
    extract_claims.py         resume text → claims, each with a source span
    match.py                  claims × requirements → strengths / gaps / matches
    evidence/
      consistency.py          free, deterministic: date overlaps, impossible tenure, etc.
      github.py               optional, authorship-aware, cites commit permalinks
    interview/
      generate.py             grounded questions for unverified must-have claims
      evaluate.py             rubric-first answer scoring + adaptive follow-up decision
    report.py                 assemble the cited hiring summary
  workers/
    tasks.py                  background task entrypoints (parse, evidence, generate)
```

### Frontend (`apps/web`) — core screens only

1. **Auth** (Supabase) — sign in / sign up.
2. **Jobs list + Job detail** — create job, paste JD, review/edit extracted requirements.
3. **Candidates** — upload resumes, see claim extraction + JD match (strengths/gaps).
4. **Interview** — recruiter generates/sends invite; **public tokenized portal** for the
   candidate (no login).
5. **Hiring summary** — the cited report; the human records a decision.

TanStack Query for all server state. Framer Motion for the interview flow and matrix reveal.
No global state library needed.

---

## 4. The AI pipeline (six independent, testable stages)

1. **JD → requirements.** Whole JD in context → structured output: `skill`, `must_have` vs
   `nice_to_have`, `min_years`, and `evidence_criteria` (what would actually satisfy this).
   Recruiter **reviews and edits** before anything runs — 30 seconds that fixes garbage-in.
2. **Resume → claims.** Whole document in context (it fits). Each claim carries a
   `source_span` that **must resolve to a literal substring** of the extracted text.
3. **Match.** Claims × requirements → strengths, missing skills, matching claims.
4. **Free evidence pass.** `consistency` (pure Python, runs for everyone) + `github`
   (optional, only when a real profile exists). Both write append-only `evidence` rows.
5. **Question generation.** For each must-have claim that is unverified/partial, ranked by JD
   importance, top ~8: ground in the candidate's most specific artifact, ask for a *decision
   and its tradeoff* (never a definition), and **write the rubric before the answer exists**.
6. **Answer scoring + report.** Score *specificity* (numbers, named tech, failure modes) —
   the axis on which generated text fails. Assemble the cited summary.

**Citation validation guardrail (non-negotiable):** before any evidence row is written, its
`source_span` must be a literal substring of the document text and any `artifact_url` must
resolve. Fail → the row is discarded and the claim stays `unverified`, never a false verdict.
A hallucinated citation is a product-ending bug; we measure the rate and drive it to zero.

### Adaptive interview state machine

```
for each must-have claim where verdict ∈ {unverified, partial}, ranked by JD importance (top ~8):
    ask grounded base question   (depth = 0)
    loop:
        evaluate answer against the pre-written rubric
        if answer is specific/strong          → record, advance to next claim
        elif depth < 3                         → ask ONE deeper probe, depth += 1
        else                                   → record, advance to next claim
```

Conversation state lives in Postgres (survives refresh/close). Max depth = 3. One probe per
weak answer, not an interrogation.

---

## 5. Data model (lean; two senior touches)

Tables: `users(auth_id)` · `jobs` · `job_requirements` · `candidates` ·
`documents(content_hash, extracted_text, page_offsets)` ·
`claims(claim_text, normalized_skill, source_span_start/end, extractor_model, prompt_version)` ·
`evidence(claim_id, source_type, verdict, summary, artifact_url, model, prompt_version)` ·
`interviews(token, status)` · `interview_questions(targets_claim_id, rubric, rationale)` ·
`interview_answers(answer_text, behavioral_flags)` · `decisions(decided_by_user_id, verdict, rationale)` ·
`ledger_events(candidate_id, seq, event_type, actor_type, payload, prev_hash, event_hash)`.

Every owned table carries `owner_user_id`.

**Two touches that cost two columns and read as production experience:**
1. `model` + `prompt_version` on every AI-generated row → any verdict is reproducible months later.
2. `evidence` is **append-only** → reconstruct exactly what the system knew at any past moment.

**The Evidence Ledger (`ledger_events`)** hardens touch 2 from a convention into a guarantee:
a per-candidate SHA-256 hash chain (each event's hash covers its content *and* the previous
event's hash, from a genesis sentinel). Every consequential action — ingestion, extraction,
each evidence pass, every interview question and answer, the human decision — is appended on
the **same transaction** as the write it describes, so the ledger can never assert something
the database doesn't show. Free text stored elsewhere (answers, rationales) is referenced by
content hash, so editing those rows later is equally detectable. `GET
/candidates/{id}/ledger/verify` replays the chain and re-attests content on demand. Alter,
insert, or delete anything after the fact and verification pinpoints the exact event. See
`app/ledger.py`; the emission points are in `pipeline/orchestrate.py` and the routers.

**There is no `score` column, anywhere, by construction.** The only verdict in the system
lives in `decisions`, and it has a `user_id`.

---

## 6. Implementation phases

### Phase 0 — Scaffold + rails (before feature work)
- Monorepo (`apps/web`, `apps/api`), env config, health checks.
- `llm/client.py`: Gemini default + OpenAI fallback, structured output, retries, cost, Langfuse.
- Alembic baseline migration.
- **Eval harness stub**: 3–5 hand-labeled resumes; a runner that measures extraction P/R.
  Prompts get tests from day one.

### Phase 1 — Foundation
- Supabase Auth (Next.js middleware + FastAPI JWT verification).
- Schema + migrations. Job CRUD.
- Resume upload → Supabase Storage → PDF text extraction **with character/page offsets**.

### Phase 2 — Understanding
- JD → requirements (with recruiter review/edit).
- Resume → claims (+ citation validation).
- Claims × JD matching (strengths / gaps / matches).
- Free consistency pass. Optional GitHub evidence.

### Phase 3 — The USP (spend the novelty budget here)
- Grounded question generation.
- Rubric-first answer evaluation.
- Adaptive depth-≤3 follow-ups.
- Tokenized async candidate portal + persisted conversation state.

### Phase 4 — Payoff
- Hiring summary: JD alignment, verified skills, needs-manual-verification, technical
  strengths, weak areas, suggested follow-ups, full transcript. **No score, no auto-verdict.**
- Recruiter dashboard + polish.

### Definition of done (not "it runs")
- [ ] Eval set exists; extraction precision/recall measured and in the README.
- [ ] Citation validation automated; hallucinated-span rate driven to zero.
- [ ] Cost + p50/p95 latency per candidate measured and published.
- [ ] No score, no ranking, no auto-verdict anywhere in the output.

---

## 7. What we deleted from the old repo, and why

| Old file | Fate |
|---|---|
| `utils/text_extraction.py` | **Kept, extended** with source offsets for citations. |
| `utils/llm_client.py` | **Pattern kept, rewritten** as the provider-agnostic client. |
| `app.py` (Streamlit) | Deleted — no auth, no tokenized portal, RAM-only state. |
| `utils/qa_chain.py`, `data_ingestion.py`, `pinecone_client.py`, `text_splitter.py` | Deleted — the entire RAG/Pinecone/embeddings/reranker stack. |
| `requirements.txt` | Rewritten — dependency tree collapses (a good story). |

> The strongest interview line in this whole project: *"I deleted the RAG pipeline I'd already
> built, because retrieval isn't evidence and my product is only evidence."*
