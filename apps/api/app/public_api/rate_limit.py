"""Per-key in-memory rate limiter (fixed 60s sliding window).

Kept dependency-free (no slowapi) — a deque of hit timestamps per key id is enough for the MVP.
Single-process only; a multi-instance deployment should move this to Redis. Enforced as a
FastAPI dependency layered on top of require_api_key.
"""

import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, status

from app.config import get_settings
from app.models.api_key import ApiKey
from app.public_api.auth import require_api_key

_WINDOW_SECONDS = 60.0
_hits: dict[str, deque] = defaultdict(deque)


def _allow(key_id: str, limit: int) -> bool:
    now = time.monotonic()
    dq = _hits[key_id]
    while dq and now - dq[0] > _WINDOW_SECONDS:
        dq.popleft()
    if len(dq) >= limit:
        return False
    dq.append(now)
    return True


def reset_rate_limits() -> None:
    """Test/ops seam — clear the in-memory window state."""
    _hits.clear()


async def rate_limited_api_key(key: ApiKey = Depends(require_api_key)) -> ApiKey:
    limit = get_settings().public_api_rate_limit_per_min
    if limit > 0 and not _allow(key.id, limit):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Rate limit exceeded (max {limit} requests/min for this key)",
        )
    return key
