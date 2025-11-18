"""Pytest configuration and fixtures.

This module provides fixtures for testing async services with proper
lifecycle management and cleanup.

Fixture Dependencies:
    scryfall_service: Standalone, uses async context manager
    card_market_service: Depends on scryfall_service
    sql_service: Standalone database fixture
    api_client: Requires running FastAPI server
"""

import os

import httpx
import pytest
import pytest_asyncio

from src.services.smart_sql import SmartSQLService
from src.services.scryfall_service import ScryfallService
from src.services.card_market_service import CardMarketService


@pytest_asyncio.fixture(scope="function")
async def scryfall_service():
    """Create a ScryfallService with proper async context management.

    The service uses connection pooling and is automatically cleaned up
    after the test completes.

    Yields:
        ScryfallService: Initialized service with HTTP client ready.
    """
    service = ScryfallService()
    await service.__aenter__()
    yield service
    await service.__aexit__(None, None, None)


@pytest_asyncio.fixture(scope="function")
async def card_market_service(scryfall_service):
    """Create a CardMarketService with injected ScryfallService.

    Uses the scryfall_service fixture to share the connection pool
    and ensure proper cleanup order.

    Args:
        scryfall_service: The ScryfallService fixture.

    Yields:
        CardMarketService: Initialized service ready for use.
    """
    service = CardMarketService(scryfall_service)
    await service.__aenter__()
    yield service
    await service.__aexit__(None, None, None)


@pytest_asyncio.fixture(scope="function")
async def sql_service():
    """Create a test database with in-memory SQLite.

    Yields:
        SmartSQLService: Initialized service with database ready.
    """
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
def api_base_url_setting() -> str:
    """Base URL for integration tests (overridable via env)."""
    return (
        os.getenv("FASTAPI_BASE_URL")
        or os.getenv("API_BASE_URL")
        or "http://localhost:7860"
    )


@pytest_asyncio.fixture()
async def api_client(api_base_url_setting: str):
    """Shared HTTP client that ensures the API is reachable."""
    async with httpx.AsyncClient(
        base_url=api_base_url_setting,
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
            pytest.skip(
                f"FastAPI server unavailable at {api_base_url_setting}: {exc}"
            )

        yield client
