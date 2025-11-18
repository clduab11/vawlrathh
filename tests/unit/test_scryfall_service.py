"""Unit tests for ScryfallService with async connection pooling.

Tests the refactored ScryfallService that uses shared AsyncClient
with connection pooling for efficient HTTP requests.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

from src.services.scryfall_service import ScryfallService


@pytest.mark.asyncio
class TestScryfallServiceLifecycle:
    """Tests for async context manager and lifecycle management."""

    async def test_context_manager_creates_client(self):
        """Test that entering context creates HTTP client."""
        async with ScryfallService() as service:
            assert service._client is not None

    async def test_context_manager_closes_client(self):
        """Test that exiting context closes HTTP client."""
        service = ScryfallService()
        await service.__aenter__()
        client = service._client
        await service.__aexit__(None, None, None)
        assert service._client is None

    async def test_ensure_client_creates_once(self):
        """Test that _ensure_client reuses existing client."""
        service = ScryfallService()
        await service._ensure_client()
        client1 = service._client
        await service._ensure_client()
        client2 = service._client
        assert client1 is client2
        await service.close()

    async def test_close_is_idempotent(self):
        """Test that close() can be called multiple times safely."""
        service = ScryfallService()
        await service._ensure_client()
        await service.close()
        await service.close()  # Should not raise
        assert service._client is None


@pytest.mark.asyncio
class TestScryfallServiceCaching:
    """Tests for response caching."""

    async def test_cache_hit_returns_cached_data(self):
        """Test that cached data is returned without API call."""
        service = ScryfallService()

        # Manually set cached data
        cache_key = "card:Lightning Bolt:latest"
        cached_data = {"name": "Lightning Bolt", "cached": True}
        service._set_cached(cache_key, cached_data)

        result = service._get_cached(cache_key)
        assert result == cached_data
        await service.close()

    async def test_cache_miss_returns_none(self):
        """Test that cache miss returns None."""
        service = ScryfallService()
        result = service._get_cached("nonexistent")
        assert result is None
        await service.close()

    async def test_cache_expiry(self):
        """Test that expired cache entries are removed."""
        service = ScryfallService()

        # Set cache with old timestamp
        cache_key = "card:Old Card:latest"
        old_time = datetime.now() - timedelta(hours=25)
        service._cache[cache_key] = (old_time, {"name": "Old Card"})

        result = service._get_cached(cache_key)
        assert result is None
        assert cache_key not in service._cache
        await service.close()


@pytest.mark.asyncio
class TestScryfallServiceRateLimiting:
    """Tests for rate limiting functionality."""

    async def test_rate_limit_enforces_delay(self):
        """Test that rate limiting adds delay between requests."""
        service = ScryfallService()

        # First call
        start = datetime.now()
        await service._rate_limit()

        # Second call should delay
        await service._rate_limit()
        elapsed = (datetime.now() - start).total_seconds()

        # Should have waited at least the rate limit delay
        assert elapsed >= service.RATE_LIMIT_DELAY * 0.9  # 90% tolerance
        await service.close()


@pytest.mark.asyncio
class TestScryfallServiceAPI:
    """Tests for API methods with mocked HTTP responses."""

    async def test_get_card_by_name_success(self, scryfall_service):
        """Test successful card fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "Lightning Bolt",
            "id": "12345",
            "games": ["paper", "arena"]
        }

        with patch.object(
            scryfall_service._client, 'get',
            new_callable=AsyncMock,
            return_value=mock_response
        ):
            result = await scryfall_service.get_card_by_name("Lightning Bolt")
            assert result["name"] == "Lightning Bolt"

    async def test_get_card_by_name_not_found(self, scryfall_service):
        """Test handling of 404 response."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch.object(
            scryfall_service._client, 'get',
            new_callable=AsyncMock,
            return_value=mock_response
        ):
            result = await scryfall_service.get_card_by_name("Nonexistent Card")
            assert result is None

    async def test_get_card_by_name_uses_cache(self, scryfall_service):
        """Test that second call uses cache."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"name": "Bolt", "id": "123"}

        with patch.object(
            scryfall_service._client, 'get',
            new_callable=AsyncMock,
            return_value=mock_response
        ) as mock_get:
            # First call hits API
            await scryfall_service.get_card_by_name("Bolt")
            # Second call should use cache
            await scryfall_service.get_card_by_name("Bolt")

            # API should only be called once
            assert mock_get.call_count == 1

    async def test_is_arena_only_paper_card(self, scryfall_service):
        """Test detection of paper-available cards."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "Lightning Bolt",
            "games": ["paper", "arena"]
        }

        with patch.object(
            scryfall_service._client, 'get',
            new_callable=AsyncMock,
            return_value=mock_response
        ):
            result = await scryfall_service.is_arena_only("Lightning Bolt")
            assert result is False

    async def test_is_arena_only_digital_card(self, scryfall_service):
        """Test detection of Arena-only cards."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "Digital Card",
            "games": ["arena"]
        }

        with patch.object(
            scryfall_service._client, 'get',
            new_callable=AsyncMock,
            return_value=mock_response
        ):
            result = await scryfall_service.is_arena_only("Digital Card")
            assert result is True

    async def test_search_cards_success(self, scryfall_service):
        """Test successful card search."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"name": "Bolt 1"},
                {"name": "Bolt 2"}
            ]
        }

        with patch.object(
            scryfall_service._client, 'get',
            new_callable=AsyncMock,
            return_value=mock_response
        ):
            result = await scryfall_service.search_cards("bolt")
            assert len(result) == 2

    async def test_get_card_prices(self, scryfall_service):
        """Test price extraction from card data."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "Expensive Card",
            "prices": {
                "usd": "10.00",
                "usd_foil": "25.00",
                "eur": "8.50",
                "tix": "5.00"
            }
        }

        with patch.object(
            scryfall_service._client, 'get',
            new_callable=AsyncMock,
            return_value=mock_response
        ):
            result = await scryfall_service.get_card_prices("Expensive Card")
            assert result["usd"] == 10.0
            assert result["usd_foil"] == 25.0


@pytest.mark.asyncio
class TestScryfallServiceErrorHandling:
    """Tests for error handling scenarios."""

    async def test_timeout_returns_none(self, scryfall_service):
        """Test that timeout errors return None."""
        import httpx

        with patch.object(
            scryfall_service._client, 'get',
            new_callable=AsyncMock,
            side_effect=httpx.TimeoutException("Timeout")
        ):
            result = await scryfall_service.get_card_by_name("Slow Card")
            assert result is None

    async def test_connection_error_returns_none(self, scryfall_service):
        """Test that connection errors return None."""
        with patch.object(
            scryfall_service._client, 'get',
            new_callable=AsyncMock,
            side_effect=Exception("Connection failed")
        ):
            result = await scryfall_service.get_card_by_name("Error Card")
            assert result is None
