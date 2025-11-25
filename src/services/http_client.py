"""Shared HTTP client manager."""
import httpx
from typing import Optional

class HTTPClientManager:
    _client: Optional[httpx.AsyncClient] = None

    @classmethod
    def get_client(cls) -> httpx.AsyncClient:
        """Get the shared async client. Initialize if not exists."""
        if cls._client is None:
            # Fallback if not initialized in lifespan (e.g. tests)
            cls._client = httpx.AsyncClient(
                timeout=60.0,
                limits=httpx.Limits(max_keepalive_connections=10)
            )
        return cls._client

    @classmethod
    async def start(cls):
        """Initialize the client."""
        if cls._client is None:
            cls._client = httpx.AsyncClient(
                timeout=60.0,
                limits=httpx.Limits(max_keepalive_connections=10)
            )

    @classmethod
    async def stop(cls):
        """Close the client."""
        if cls._client:
            await cls._client.aclose()
            cls._client = None
