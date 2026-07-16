# Recruit — Evidence-First Hiring Verification

Recruiters don't struggle with parsing resumes anymore — they struggle with verifying whether
candidates can actually defend what they claim. This isn't another resume scorer. It extracts
every technical claim from a resume, matches it against a job's actual requirements, gathers
free supporting evidence (internal consistency checks + optional GitHub), and runs an
**adaptive AI interview** that grounds every question in the candidate's own claims — the kind
of question a second ChatGPT window can't answer. It ends in a cited hiring summary.
**It never emits a score or an auto hire/reject decision.** A human decides; the system
records who, when, and why.

See [`docs/PRODUCT_PLAN.md`](docs/PRODUCT_PLAN.md) for the product thesis and
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the technical blueprint.

## Stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 15, TypeScript, TailwindCSS, shadcn/ui, Framer Motion, TanStack Query |
| Backend | FastAPI, Python 3.12+, Pydantic v2, SQLAlchemy (async) |
| Database + Auth + Storage | Supabase (single Postgres) |
| LLM | Gemini (default) or OpenAI, behind one abstraction — switch via env var |
| Observability | Langfuse (optional) |

## Repository layout

```
apps/api/     FastAPI backend — pipeline, routers, models, tests
apps/web/     Next.js frontend
docs/         Product plan + architecture blueprint
```

## Running it locally

### Backend

```bash
cd apps/api
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash; use .venv/bin/activate on macOS/Linux
pip install -r requirements-dev.txt
cp .env.example .env             # fill in real values — see "What needs your credentials" below
uvicorn app.main:app --reload --port 8000
```

Without a `DATABASE_URL` set, it defaults to a local SQLite file (`dev.db`) and auto-creates
tables on startup — enough to click through the app with no external services at all. Point
`DATABASE_URL` at your Supabase Postgres connection string for anything beyond local dev;
schema changes there are managed by Alembic (`alembic upgrade head`), not the SQLite
auto-create path.

Run the test suite (76 tests, all offline — SQLite + a fake LLM provider, no network calls):

```bash
python -m pytest tests/ -v
ruff check app/ tests/
```

### Frontend

```bash
cd apps/web
npm install
cp .env.local.example .env.local   # fill in real values
npm run dev
```

Visit `http://localhost:3000`.

## What needs your own credentials before it's fully live

This was built and tested entirely offline — SQLite instead of Supabase Postgres, a fake LLM
provider instead of Gemini/OpenAI, no real GitHub token, no Langfuse project. That's
deliberate: none of those accounts could be created on your behalf. Before this is a live
product you can actually demo end-to-end, you need to:

1. **Create a Supabase project** (free tier is fine) → Project Settings → API. Copy the URL,
   anon key, and service role key into both `.env` files. This gives you real Postgres,
   Auth, and Storage — Supabase is the only backing service the app needs.
2. **Get a Gemini API key** (default provider — [aistudio.google.com](https://aistudio.google.com)) or an
   OpenAI key, and set `GEMINI_API_KEY`/`OPENAI_API_KEY` + `LLM_PROVIDER` in `apps/api/.env`.
3. **Run the Alembic migration** against your Supabase Postgres: `alembic upgrade head`
   (from `apps/api`, with `DATABASE_URL` pointed at Supabase).
4. **Create a Supabase Storage bucket** named `resumes` (or update `SUPABASE_STORAGE_BUCKET`).
5. *(Optional)* a GitHub personal access token for the opportunistic GitHub evidence pass, and
   Langfuse keys for LLM tracing.

Everything else — the claim-extraction pipeline, the adaptive interview state machine, the
citation-validation guardrail, JD/resume matching, the hiring summary — is fully implemented
and covered by the automated test suite, not stubbed.

### Known gaps to verify once you add real keys

- The Gemini/OpenAI/Langfuse SDK calls (`apps/api/app/llm/provider.py`, `app/llm/client.py`)
  are written against each SDK's documented API but were never exercised against a live
  endpoint in this session — there was no key to test with. Sanity-check a real call once you
  add keys; the FakeProvider-backed tests only prove the *pipeline logic* around those calls
  is correct, not the SDK integration itself.
- Cost/latency budgets (target < $0.15, < 90s per candidate per `docs/ARCHITECTURE.md`) are
  designed for but not yet measured against a live model — there's nothing to measure without
  a key.
