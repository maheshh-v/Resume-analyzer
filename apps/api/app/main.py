import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse

from app.config import get_settings
from app.db.session import engine
from app.llm.errors import LLMUnavailableError
from app.models import Base
from app.routers import (
    benchmarks,
    candidates,
    health,
    intake,
    interviews,
    jobs,
    ledger,
    observability,
    public,
    reports,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.is_sqlite:
        # Local/dev/test convenience only — production (Postgres) schema is managed by Alembic.
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield


# Top-level segments of the pre-versioning recruiter API. Kept for backward compatibility via a
# 308 redirect to their /api/v1 equivalents (see LegacyPathRedirectMiddleware). `/health` and `/`
# are intentionally NOT here — infra health checks must keep hitting the bare paths.
_LEGACY_PREFIXES = ("/jobs", "/candidates", "/interview")
_API_V1 = "/api/v1"


class LegacyPathRedirectMiddleware(BaseHTTPMiddleware):
    """Redirect old unprefixed recruiter routes to their /api/v1 equivalents with a 308 (which
    preserves method + body, unlike a 302). Temporary: logs a warning each time so we can see who
    still hits legacy paths and remove this once callers migrate."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if any(path == p or path.startswith(p + "/") for p in _LEGACY_PREFIXES):
            target = request.url.replace(path=_API_V1 + path)
            logger.warning(
                "Legacy API path hit: %s %s -> 308 %s (client should migrate to /api/v1)",
                request.method,
                path,
                target.path,
            )
            return RedirectResponse(str(target), status_code=308)
        return await call_next(request)


class LLMErrorMiddleware(BaseHTTPMiddleware):
    """Turns exhausted-LLM-retries into a clean 503 with a user-facing detail message.

    This must be a middleware INSIDE the CORS middleware, not an unhandled exception: an
    unhandled exception becomes a bare 500 with no CORS headers, which the browser reports
    as an opaque "Failed to fetch" instead of our message.
    """

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except LLMUnavailableError as exc:
            logger.warning("LLM unavailable on %s %s: %s", request.method, request.url.path, exc)
            return JSONResponse({"detail": str(exc)}, status_code=503)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Recruit — Evidence-First Hiring Verification", lifespan=lifespan)

    # Order matters: the LAST-added middleware is OUTERMOST, so add LLM error handling first,
    # the legacy redirect second, and CORS last — CORS must wrap every response (including 503s
    # and the 308 redirects, so browsers can follow them cross-origin).
    app.add_middleware(LLMErrorMiddleware)
    app.add_middleware(LegacyPathRedirectMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Infra endpoints stay unprefixed. Everything the product exposes lives under /api/v1: the
    # recruiter routers get the prefix here; benchmarks/observability/public already bake it in.
    app.include_router(health.router)
    app.include_router(benchmarks.router)
    app.include_router(jobs.router, prefix=_API_V1)
    app.include_router(candidates.router, prefix=_API_V1)
    app.include_router(intake.router, prefix=_API_V1)
    app.include_router(interviews.router, prefix=_API_V1)
    app.include_router(reports.router, prefix=_API_V1)
    app.include_router(ledger.router, prefix=_API_V1)
    app.include_router(observability.router)
    app.include_router(public.router)

    return app


app = create_app()
