import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import get_settings
from app.db.session import engine
from app.llm.errors import LLMUnavailableError
from app.models import Base
from app.routers import candidates, health, interviews, jobs, ledger, reports

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.is_sqlite:
        # Local/dev/test convenience only — production (Postgres) schema is managed by Alembic.
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield


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

    # Order matters: the LAST-added middleware is OUTERMOST, so add LLM error handling
    # first and CORS second — CORS must wrap every response, including our 503s.
    app.add_middleware(LLMErrorMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(jobs.router)
    app.include_router(candidates.router)
    app.include_router(interviews.router)
    app.include_router(reports.router)
    app.include_router(ledger.router)

    return app


app = create_app()
