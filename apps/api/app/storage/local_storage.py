"""Local-disk fallback storage, used when Supabase Storage isn't configured (local dev,
tests). Same interface as supabase_storage.upload_resume so orchestrate.py can swap between
them transparently based on settings — never a hard dependency on Supabase just to try the
app locally.
"""

from pathlib import Path

_LOCAL_STORAGE_ROOT = Path(__file__).resolve().parent.parent.parent / "data" / "resumes"


async def upload_resume(*, candidate_id: str, filename: str, content: bytes) -> str:
    candidate_dir = _LOCAL_STORAGE_ROOT / candidate_id
    candidate_dir.mkdir(parents=True, exist_ok=True)
    file_path = candidate_dir / filename
    file_path.write_bytes(content)
    return str(file_path.relative_to(_LOCAL_STORAGE_ROOT.parent.parent))
