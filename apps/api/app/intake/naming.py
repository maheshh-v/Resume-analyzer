"""Deriving a candidate display name from a resume filename for bulk upload.

"Jane_Doe_Resume_2024.pdf" → "Jane Doe". Filler tokens (resume/cv/final/...), version markers,
and bare numbers are dropped; all-lower/all-upper tokens are title-cased, mixed-case tokens
(McDonald, O'Brien) are kept as typed. The result is only a label — the resume itself is the
source of truth and the recruiter sees it on the candidate page.
"""

import re

_FILLER_TOKENS = {
    "resume",
    "cv",
    "curriculum",
    "vitae",
    "final",
    "updated",
    "new",
    "copy",
    "latest",
    "draft",
    "profile",
    "application",
    "portfolio",
}
_TOKEN_SPLIT = re.compile(r"[\s_\-.,()\[\]{}+]+")
_VERSION_OR_NUMBER = re.compile(r"^v?\d+$", re.IGNORECASE)


def _fix_case(token: str) -> str:
    return token.capitalize() if token.islower() or token.isupper() else token


def candidate_name_from_filename(filename: str) -> str:
    stem = filename.rsplit(".", 1)[0] if "." in filename else filename
    tokens = [t for t in _TOKEN_SPLIT.split(stem) if t]
    kept = [t for t in tokens if t.lower() not in _FILLER_TOKENS and not _VERSION_OR_NUMBER.match(t)]
    if not kept:
        return "Unnamed candidate"
    return " ".join(_fix_case(t) for t in kept)
