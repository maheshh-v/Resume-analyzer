from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    cors_origins: str = "http://localhost:3000"

    database_url: str = "sqlite+aiosqlite:///./dev.db"

    supabase_url: str = ""
    supabase_jwks_url: str = ""
    supabase_service_role_key: str = ""
    supabase_storage_bucket: str = "resumes"

    llm_provider: str = "gemini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"
    # Tried (2 attempts) when the primary model is overloaded after retries. Set to "" to
    # disable. Uses the same API key. The "-latest" alias always resolves to a model this
    # key can access, unlike pinned versions which 404 for newer keys.
    gemini_fallback_model: str = "gemini-flash-lite-latest"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    github_token: str = ""

    # Optional evidence connectors, opt-in per source. Off by default so a fresh deploy never
    # makes surprise outbound calls; each still routes through the URL+substring guardrail.
    enable_semantic_scholar: bool = False
    enable_google_patents: bool = False
    enable_package_ownership: bool = False

    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    interview_token_ttl_hours: int = 72

    # --- White-label public API + billing (Phase 4) ---
    # Per-key requests/minute for /api/v1/public. In-memory limiter; see public_api/rate_limit.py.
    public_api_rate_limit_per_min: int = 10
    # Stripe metered billing. Scaffold only: no event is sent unless BOTH a key's stripe_customer_id
    # and this secret are set. Never collect card details here — Stripe onboarding is manual.
    stripe_api_key: str = ""
    stripe_meter_event_name: str = "recruitx_verification"

    # Where the eval harness writes its results (latest.json / latest.md). Empty -> the router
    # computes the default repo-root `evals/results` path. Set in tests to point at a fixture dir.
    benchmarks_results_dir: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
