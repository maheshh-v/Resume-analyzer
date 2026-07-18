"""Fetching a resume PDF from a URL supplied in an imported sheet.

The URLs come from the recruiter's own sheet, but the fetch still runs server-side, so the
obvious SSRF doors are shut: http(s) only, no loopback/private literal hosts (re-checked on
every redirect hop), a 10MB cap, and the body must actually be a PDF. A hardened multi-tenant
deployment should additionally route these fetches through an egress proxy — DNS-rebinding
defenses are out of scope for an in-process guard.
"""

import ipaddress

import httpx

MAX_RESUME_BYTES = 10 * 1024 * 1024
_MAX_REDIRECTS = 3


class ResumeFetchError(Exception):
    """Raised with a user-facing message when a resume URL can't be turned into PDF bytes."""


def _host_is_private(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return not ipaddress.ip_address(host).is_global
    except ValueError:
        return False  # a domain name — resolution-level blocking needs an egress proxy


def check_resume_url(url: str) -> None:
    try:
        parsed = httpx.URL(url)
    except Exception as exc:
        raise ResumeFetchError("Resume URL is not a valid URL") from exc
    if parsed.scheme not in ("http", "https"):
        raise ResumeFetchError("Resume URL must be http(s)")
    if not parsed.host or _host_is_private(parsed.host):
        raise ResumeFetchError("Resume URL points at a private or invalid host")


async def fetch_resume_pdf(url: str, client: httpx.AsyncClient | None = None) -> bytes:
    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(timeout=20)
    try:
        response = None
        for _ in range(_MAX_REDIRECTS + 1):
            check_resume_url(url)
            try:
                response = await client.get(url, follow_redirects=False)
            except httpx.HTTPError as exc:
                raise ResumeFetchError(f"Couldn't fetch resume ({exc.__class__.__name__})") from exc
            location = response.headers.get("location")
            if response.status_code in (301, 302, 303, 307, 308) and location:
                url = str(httpx.URL(url).join(location))
                continue
            break
    finally:
        if owns_client:
            await client.aclose()

    if response is None or response.status_code in (301, 302, 303, 307, 308):
        raise ResumeFetchError("Resume URL redirected too many times")
    if response.status_code != 200:
        raise ResumeFetchError(f"Resume URL returned HTTP {response.status_code}")
    if len(response.content) > MAX_RESUME_BYTES:
        raise ResumeFetchError("Resume file too large (max 10MB)")
    if not response.content.startswith(b"%PDF"):
        raise ResumeFetchError("Resume URL did not return a PDF file")
    return response.content
