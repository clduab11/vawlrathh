"""Unit tests for CardMarketService with async context management.

Tests the refactored CardMarketService that uses ScryfallService
with connection pooling and proper lifecycle management.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from src.services.card_market_service import (
    CardMarketService,
    CardMarketInfo,
    VendorPrice
)
from src.services.scryfall_service import ScryfallService


@pytest.mark.asyncio
class TestCardMarketServiceLifecycle:
    """Tests for async context manager and lifecycle management."""

    async def test_context_manager_creates_scryfall(self):
        """Test that entering context creates ScryfallService."""
        async with CardMarketService() as service:
            assert service.scryfall is not None
            assert service._owns_scryfall is True

    async def test_context_manager_with_injected_scryfall(self):
        """Test context manager with pre-existing ScryfallService."""
        async with ScryfallService() as scryfall:
            service = CardMarketService(scryfall)
            await service.__aenter__()
            assert service.scryfall is scryfall
            assert service._owns_scryfall is False
            await service.__aexit__(None, None, None)
            # Scryfall should still be open since we don't own it
            assert scryfall._client is not None

    async def test_close_cleans_up_owned_scryfall(self):
        """Test that close() cleans up owned ScryfallService."""
        service = CardMarketService()
        await service.__aenter__()
        await service.close()
        assert service.scryfall is None

    async def test_close_preserves_injected_scryfall(self):
        """Test that close() preserves injected ScryfallService."""
        async with ScryfallService() as scryfall:
            service = CardMarketService(scryfall)
            await service.__aenter__()
            await service.close()
            # Injected scryfall should not be closed
            assert scryfall._client is not None


@pytest.mark.asyncio
class TestCardMarketInfo:
    """Tests for CardMarketInfo operations."""

    async def test_get_card_market_info_success(self, card_market_service):
        """Test successful card market info retrieval."""
        # Mock all the Scryfall methods
        with patch.multiple(
            card_market_service.scryfall,
            is_arena_only=AsyncMock(return_value=False),
            get_card_by_name=AsyncMock(return_value={
                "name": "Lightning Bolt",
                "id": "12345"
            }),
            get_card_prices=AsyncMock(return_value={
                "usd": 1.50,
                "usd_foil": 5.00,
                "eur": 1.20,
                "tix": 0.50
            }),
            get_purchase_uris=AsyncMock(return_value={
                "tcgplayer": "https://tcgplayer.com/bolt",
                "cardmarket": "https://cardmarket.com/bolt",
                "cardhoarder": None
            }),
            get_card_image_uri=AsyncMock(return_value="https://img.scryfall.com/bolt.jpg")
        ):
            result = await card_market_service.get_card_market_info("Lightning Bolt")

            assert result is not None
            assert result.card_name == "Lightning Bolt"
            assert result.is_arena_only is False
            assert result.available_in_paper is True
            assert len(result.vendors) == 2  # TCGPlayer and CardMarket
            assert result.best_price_usd == 1.50

    async def test_get_card_market_info_arena_only_excluded(self, card_market_service):
        """Test that Arena-only cards are excluded when requested."""
        with patch.object(
            card_market_service.scryfall, 'is_arena_only',
            new_callable=AsyncMock,
            return_value=True
        ):
            result = await card_market_service.get_card_market_info(
                "Digital Only Card",
                exclude_arena_only=True
            )
            assert result is None

    async def test_get_card_market_info_arena_only_included(self, card_market_service):
        """Test that Arena-only cards are included when not excluded."""
        with patch.multiple(
            card_market_service.scryfall,
            is_arena_only=AsyncMock(return_value=True),
            get_card_by_name=AsyncMock(return_value={"name": "Digital Card", "id": "99"}),
            get_card_prices=AsyncMock(return_value={"usd": None, "usd_foil": None, "eur": None, "tix": None}),
            get_purchase_uris=AsyncMock(return_value={}),
            get_card_image_uri=AsyncMock(return_value=None)
        ):
            result = await card_market_service.get_card_market_info(
                "Digital Card",
                exclude_arena_only=False
            )
            assert result is not None
            assert result.is_arena_only is True

    async def test_card_market_info_to_dict(self):
        """Test CardMarketInfo serialization."""
        vendor = VendorPrice(
            vendor_name="TCGPlayer",
            price_usd=1.50,
            price_eur=None,
            currency="USD",
            purchase_url="https://tcgplayer.com",
            in_stock=True
        )

        info = CardMarketInfo(
            card_name="Bolt",
            set_code="M11",
            is_arena_only=False,
            available_in_paper=True,
            vendors=[vendor],
            best_price_usd=1.50,
            best_vendor="TCGPlayer"
        )

        result = info.to_dict()
        assert result["card_name"] == "Bolt"
        assert result["best_price_usd"] == 1.50
        assert len(result["vendors"]) == 1


@pytest.mark.asyncio
class TestDeckMarketInfo:
    """Tests for deck-wide market information."""

    async def test_get_deck_market_info(self, card_market_service):
        """Test market info for entire deck."""
        # Mock get_card_market_info to return controlled data
        async def mock_market_info(card_name, set_code, exclude_arena_only):
            if "Digital" in card_name:
                return CardMarketInfo(
                    card_name=card_name,
                    set_code=set_code,
                    is_arena_only=True,
                    available_in_paper=False,
                    vendors=[],
                    best_price_usd=None,
                    best_vendor=None
                )
            return CardMarketInfo(
                card_name=card_name,
                set_code=set_code,
                is_arena_only=False,
                available_in_paper=True,
                vendors=[
                    VendorPrice(
                        vendor_name="TCGPlayer",
                        price_usd=1.00,
                        price_eur=None,
                        currency="USD",
                        purchase_url="https://tcg.com",
                        in_stock=True
                    )
                ],
                best_price_usd=1.00,
                best_vendor="TCGPlayer"
            )

        with patch.object(
            card_market_service, 'get_card_market_info',
            side_effect=mock_market_info
        ):
            cards = [
                ("Lightning Bolt", 4, "M11"),
                ("Digital Card", 2, None)
            ]

            result = await card_market_service.get_deck_market_info(cards)

            assert result["total_cards"] == 2
            assert result["purchasable_cards"] == 1
            assert result["arena_only_cards"] == 1
            assert result["total_price_usd"] == 4.0  # 4 copies * $1


@pytest.mark.asyncio
class TestFindAlternatives:
    """Tests for finding alternative card printings."""

    async def test_find_card_alternatives(self, card_market_service):
        """Test finding alternative printings."""
        with patch.object(
            card_market_service.scryfall, 'search_cards',
            new_callable=AsyncMock,
            return_value=[
                {"name": "Bolt", "set": "M11"},
                {"name": "Bolt", "set": "4ED"}
            ]
        ):
            with patch.object(
                card_market_service, 'get_card_market_info',
                new_callable=AsyncMock,
                side_effect=[
                    CardMarketInfo(
                        card_name="Bolt", set_code="M11",
                        is_arena_only=False, available_in_paper=True,
                        vendors=[], best_price_usd=1.00, best_vendor="TCG"
                    ),
                    CardMarketInfo(
                        card_name="Bolt", set_code="4ED",
                        is_arena_only=False, available_in_paper=True,
                        vendors=[], best_price_usd=0.50, best_vendor="TCG"
                    )
                ]
            ):
                result = await card_market_service.find_card_alternatives("Bolt")

                assert len(result) == 2
                # Should be sorted by price
                assert result[0].best_price_usd == 0.50


@pytest.mark.asyncio
class TestVendorBreakdown:
    """Tests for vendor breakdown calculations."""

    def test_vendor_breakdown_calculation(self):
        """Test vendor total calculation."""
        service = CardMarketService()

        purchasable_cards = [
            {
                "card_name": "Bolt",
                "quantity": 4,
                "vendors": [
                    {"vendor_name": "TCG", "price_usd": 1.00, "in_stock": True},
                    {"vendor_name": "MKM", "price_usd": 0.80, "in_stock": True}
                ]
            }
        ]

        result = service._get_vendor_breakdown(purchasable_cards)

        assert result["MKM"] == 3.20  # 4 * 0.80
        assert result["TCG"] == 4.00  # 4 * 1.00


@pytest.mark.asyncio
class TestEnsureScryfall:
    """Tests for lazy initialization of ScryfallService."""

    async def test_ensure_scryfall_creates_service(self):
        """Test that _ensure_scryfall creates service when None."""
        service = CardMarketService()
        assert service.scryfall is None

        await service._ensure_scryfall()
        assert service.scryfall is not None
        assert service._owns_scryfall is True

        await service.close()

    async def test_ensure_scryfall_reuses_existing(self):
        """Test that _ensure_scryfall reuses existing service."""
        async with ScryfallService() as scryfall:
            service = CardMarketService(scryfall)
            await service._ensure_scryfall()
            assert service.scryfall is scryfall
