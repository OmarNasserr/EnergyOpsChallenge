from typing import AsyncGenerator

import pytest_asyncio
from _pytest.monkeypatch import MonkeyPatch
from httpx import AsyncClient, ASGITransport
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.main import app
from app.db.models import Base, Contract, Event

# Use a separate test database
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_eo_tech_challenge_async.db"
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_database():
    """Create database schema once at the start of test session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Cleanup after all tests complete
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def get_test_session() -> AsyncSession:
    """Override the database session to use test database."""
    from sqlalchemy.ext.asyncio import async_sessionmaker
    TestSessionLocal = async_sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def async_client():
    """Provide an async HTTP client with clean database before each test."""
    # Delete all data before each test (fast - keeps tables, deletes data only)
    async with test_engine.begin() as conn:
        await conn.execute(delete(Event))
        await conn.execute(delete(Contract))

    # Override the database dependency to use test database
    from app.db.session import get_async_session
    app.dependency_overrides[get_async_session] = get_test_session

    # Create test client
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    # Clean up dependency override
    app.dependency_overrides.clear()
