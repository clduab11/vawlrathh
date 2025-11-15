"""Pytest configuration and fixtures."""

import asyncio
import os

import httpx
import pytest
import pytest_asyncio

from src.services.smart_sql import SmartSQLService


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def sql_service():
    """Create a test database."""
    service = SmartSQLService("sqlite+aiosqlite:///:memory:")
    await service.init_db()
    yield service
    # Cleanup
    await service.engine.dispose()


@pytest.fixture(scope="function")
async def initialized_app():
    """Initialize FastAPI app with test database."""
    from src.main import app
    from src.api.routes import sql_service
    
    # Initialize test database
    await sql_service.init_db()
    
    yield app
    
    # Cleanup
    await sql_service.engine.dispose()


@pytest.fixture(scope="session")
def api_base_url() -> str:
    """Base URL for integration tests (overridable via env)."""
    return (
        os.getenv("FASTAPI_BASE_URL")
        or os.getenv("API_BASE_URL")
        or "http://localhost:7860"
    )


@pytest_asyncio.fixture()
async def api_client(api_base_url: str):
    """Shared HTTP client that ensures the API is reachable."""
    async with httpx.AsyncClient(
        base_url=api_base_url,
        timeout=30.0
    ) as client:
        try:
            health_response = await client.get("/health", timeout=5.0)
            health_response.raise_for_status()
        except (
            httpx.HTTPError,
            httpx.ConnectError,
            httpx.TimeoutException,
        ) as exc:
            pytest.skip(f"FastAPI server unavailable at {api_base_url}: {exc}")

        yield client
