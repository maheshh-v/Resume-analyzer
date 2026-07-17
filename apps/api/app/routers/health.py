from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/", include_in_schema=False)
async def root() -> dict:
    return {"service": "recruit-api", "status": "ok", "health": "/health", "docs": "/docs"}


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}
