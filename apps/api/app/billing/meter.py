"""Stripe metered-usage emission — scaffold only.

A single successful /verify emits one usage event, but ONLY when the key has a
`stripe_customer_id` AND `STRIPE_API_KEY` is configured. Absent either, this is a no-op that
returns False — so local dev, tests, and un-onboarded orgs never touch Stripe. Best-effort:
a billing failure is logged, never raised into the request.

`stripe` is imported lazily so the app runs without the package or any Stripe config.
"""

from __future__ import annotations

import logging

from app.config import get_settings
from app.models.api_key import ApiKey

logger = logging.getLogger(__name__)


async def record_verification_usage(api_key: ApiKey, quantity: int = 1) -> bool:
    """Emit one Stripe meter event for a metered key. Returns True if an event was sent."""
    settings = get_settings()
    if not api_key.stripe_customer_id or not settings.stripe_api_key:
        return False  # not onboarded / not configured -> silently skip

    try:
        import stripe  # lazy: app must run without the package/config

        stripe.api_key = settings.stripe_api_key
        stripe.billing.MeterEvent.create(
            event_name=settings.stripe_meter_event_name,
            payload={"stripe_customer_id": api_key.stripe_customer_id, "value": str(quantity)},
        )
        return True
    except Exception:  # billing must never break a verification
        logger.warning("stripe meter event failed for org %s", api_key.org_name, exc_info=True)
        return False
