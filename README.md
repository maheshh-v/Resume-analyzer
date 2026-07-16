# Recruit — Evidence-First Hiring Verification

Recruiters don't struggle with parsing resumes anymore — they struggle with verifying whether
candidates can actually defend what they claim. This isn't another resume scorer. It extracts
every technical claim from a resume, matches it against a job's actual requirements, gathers
free supporting evidence (internal consistency checks + optional GitHub), and runs an
**adaptive AI interview** that grounds every question in the candidate's own claims — the kind
of question a second ChatGPT window can't answer. It ends in a cited hiring summary.
**It never emits a score or an auto hire/reject decision.** A human decides; the system
records who, when, and why.

Every step of that process — ingestion, extraction, each evidence pass, every interview
exchange, the final human decision — is sealed into a per-candidate, SHA-256 hash-chained
**Evidence Ledger**. One click replays the chain and proves the record hasn't been altered
since the moment it was written (see §16.1 of the product plan for why this is the moat).

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

## Environment setup (fresh clone)

The `.env` files are gitignored, so a fresh clone needs:

1. **A Supabase project** (free tier is fine) → Project Settings → API. Copy the URL,
   anon key, and service role key into both `.env` files. This gives you Postgres, Auth,
   and Storage — Supabase is the only backing service the app needs.
2. **A Gemini API key** (default provider — [aistudio.google.com](https://aistudio.google.com)) or an
   OpenAI key: set `GEMINI_API_KEY`/`OPENAI_API_KEY` + `LLM_PROVIDER` in `apps/api/.env`.
   ⚠ Gemini **2.x models return 404 for API keys created after ~2026** ("no longer available
   to new users") even though they still appear in the models list — use `gemini-3.5-flash`
   (the default).
3. **The Alembic migrations** against your Supabase Postgres: `alembic upgrade head`
   (from `apps/api`, with `DATABASE_URL` pointed at Supabase — use the `postgresql+asyncpg://`
   prefix and URL-encode special characters in the password, e.g. `@` → `%40`).
4. **A Supabase Storage bucket** named `resumes` (or update `SUPABASE_STORAGE_BUCKET`).
5. *(Optional)* a GitHub personal access token for the opportunistic GitHub evidence pass, and
   Langfuse keys for LLM tracing.

The live Gemini integration has been verified end-to-end through the real pipeline (JD
extraction with citation spans resolving verbatim). Cost/latency budgets (target < $0.15,
< 90s per candidate per `docs/ARCHITECTURE.md`) are designed for but not yet formally
measured — run a few candidates and check the Langfuse traces once keys are in.
