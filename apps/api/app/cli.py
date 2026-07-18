"""Admin CLI. Run from apps/api with the target DATABASE_URL configured.

    python -m app.cli create_api_key --org "Acme Staffing" --quota 500

Prints the raw API key exactly once — it is never recoverable afterward (only its hash is stored).
Run `alembic upgrade head` first so the api_keys table exists.
"""

import argparse
import asyncio

from app.db.session import SessionLocal
from app.models.api_key import ApiKey
from app.public_api.keys import generate_api_key


async def _create_api_key(
    *, org: str, quota: int, stripe_customer_id: str | None = None, logo_url: str | None = None
) -> tuple[str, str]:
    raw, key_hash, prefix = generate_api_key()
    async with SessionLocal() as db:
        key = ApiKey(
            org_name=org,
            key_hash=key_hash,
            key_prefix=prefix,
            monthly_quota=quota,
            stripe_customer_id=stripe_customer_id,
            logo_url=logo_url,
        )
        db.add(key)
        await db.commit()
        await db.refresh(key)
        return key.id, raw


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create_api_key", help="Mint a new white-label API key")
    create.add_argument("--org", required=True, help="Organisation name")
    create.add_argument("--quota", type=int, default=0, help="Monthly request quota (0 = unlimited)")
    create.add_argument("--stripe-customer-id", default=None, help="Opt this key into metered billing")
    create.add_argument("--logo-url", default=None, help="Logo URL for the branded PDF")

    args = parser.parse_args(argv)

    if args.command == "create_api_key":
        key_id, raw = asyncio.run(
            _create_api_key(
                org=args.org,
                quota=args.quota,
                stripe_customer_id=args.stripe_customer_id,
                logo_url=args.logo_url,
            )
        )
        print("\nAPI key created. Copy it now — it will NOT be shown again:\n")
        print(f"  org:     {args.org}")
        print(f"  quota:   {args.quota if args.quota else 'unlimited'}")
        print(f"  key_id:  {key_id}")
        print(f"  API KEY: {raw}\n")


if __name__ == "__main__":
    main()
