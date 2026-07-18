"""API key generation + hashing. The raw key is shown once and never stored — only its SHA-256."""

import hashlib
import secrets

_KEY_ENTROPY_BYTES = 32
_PREFIX = "rx_live_"


def generate_api_key() -> tuple[str, str, str]:
    """Return (raw_key, key_hash, key_prefix). The raw key is the only time the plaintext exists."""
    raw = _PREFIX + secrets.token_urlsafe(_KEY_ENTROPY_BYTES)
    return raw, hash_api_key(raw), raw[:16]


def hash_api_key(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
