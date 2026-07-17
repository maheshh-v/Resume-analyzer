import os
import tempfile

# Must happen before any `app.*` import: config/db modules read env at import time.
_TEST_DB_FD, _TEST_DB_PATH = tempfile.mkstemp(suffix=".db")
os.close(_TEST_DB_FD)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TEST_DB_PATH}"
os.environ["LLM_PROVIDER"] = "fake"
os.environ["SUPABASE_JWKS_URL"] = ""
os.environ["SUPABASE_URL"] = ""
# Tracing is a no-op by default in tests (the intended unconfigured path) so the suite never
# fires real Langfuse telemetry. Tests that need tracing on build an explicit Settings + a fake
# Langfuse client (see test_observability.py).
os.environ["LANGFUSE_PUBLIC_KEY"] = ""
os.environ["LANGFUSE_SECRET_KEY"] = ""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import get_current_user
from app.db.session import SessionLocal, engine
from app.llm.client import LLMClient, set_default_client
from app.llm.provider import FakeProvider
from app.main import app
from app.models import Base
from app.models.user import User


@pytest_asyncio.fixture(autouse=True)
async def _reset_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    set_default_client(None)
    yield


@pytest_asyncio.fixture
async def db_session():
    async with SessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def test_user(db_session) -> User:
    user = User(auth_id="test-auth-id", email="recruiter@example.com")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def fake_provider() -> FakeProvider:
    provider = FakeProvider()
    set_default_client(LLMClient(provider=provider))
    return provider


@pytest_asyncio.fixture
async def client(test_user):
    async def _override_current_user():
        return test_user

    app.dependency_overrides[get_current_user] = _override_current_user
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
