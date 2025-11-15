"""Tests for card market service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.card_market_service import CardMarketService, VendorPrice, CardMarketInfo
from src.services.scryfall_service import ScryfallService


@pytest.fixture
def mock_scryfall():
    """Create mock Scryfall service."""
    scryfall = AsyncMock(spec=ScryfallService)
    return scryfall


@pytest.fixture
def card_market_service(mock_scryfall):
    """Create CardMarketService with mocked Scryfall."""
    return CardMarketService(mock_scryfall)


@pytest.mark.asyncio
async def test_get_card_market_info_arena_only(card_market_service, mock_scryfall):
    """Test getting market info for Arena-only card."""
    # Setup
    mock_scryfall.is_arena_only.return_value = True

    # Execute
    result = await card_market_service.get_card_market_info(
        "Test Card",
        exclude_arena_only=True
    )

    # Assert
    assert result is None
    mock_scryfall.is_arena_only.assert_called_once_with("Test Card", None)


@pytest.mark.asyncio
async def test_get_card_market_info_purchasable(card_market_service, mock_scryfall):
    """Test getting market info for purchasable card."""
    # Setup
    mock_scryfall.is_arena_only.return_value = False
    mock_scryfall.get_card_by_name.return_value = {
        "id": "test-id",
        "name": "Lightning Bolt",
        "set": "M11"
    }
    mock_scryfall.get_card_prices.return_value = {
        "usd": 1.50,
        "usd_foil": 3.00,
        "eur": 1.20,
        "tix": 0.50
    }
    mock_scryfall.get_purchase_uris.return_value = {
        "tcgplayer": "https://tcgplayer.com/test",
        "cardmarket": "https://cardmarket.com/test",
        "cardhoarder": "https://cardhoarder.com/test"
    }
    mock_scryfall.get_card_image_uri.return_value = "https://image.url/test.png"

    # Execute
    result = await card_market_service.get_card_market_info("Lightning Bolt")

    # Assert
    assert result is not None
    assert result.card_name == "Lightning Bolt"
    assert result.is_arena_only is False
    assert result.available_in_paper is True
    assert result.best_price_usd == 1.50
    assert result.best_vendor == "TCGPlayer"
    assert len(result.vendors) == 3


@pytest.mark.asyncio
async def test_get_deck_market_info(card_market_service, mock_scryfall):
    """Test getting market info for entire deck."""
    # Setup
    mock_scryfall.is_arena_only.side_effect = [False, False, True]
    mock_scryfall.get_card_by_name.return_value = {"id": "test", "name": "Test"}
    mock_scryfall.get_card_prices.return_value = {
        "usd": 2.00, "usd_foil": None, "eur": None, "tix": None
    }
    mock_scryfall.get_purchase_uris.return_value = {
        "tcgplayer": "https://test.com"
    }
    mock_scryfall.get_card_image_uri.return_value = "https://image.url"

    cards = [
        ("Card A", 4, "SET1"),
        ("Card B", 2, "SET2"),
        ("Arena Only Card", 4, "SET3")
    ]

    # Execute
    result = await card_market_service.get_deck_market_info(cards)

    # Assert
    assert result['total_cards'] == 3
    assert result['purchasable_cards'] == 2
    assert result['arena_only_cards'] == 1
    assert result['total_price_usd'] == 12.00  # (4 * 2.00) + (2 * 2.00)


def test_vendor_price_dataclass():
    """Test VendorPrice dataclass."""
    vendor = VendorPrice(
        vendor_name="TCGPlayer",
        price_usd=1.50,
        price_eur=None,
        currency="USD",
        purchase_url="https://test.com"
    )

    assert vendor.vendor_name == "TCGPlayer"
    assert vendor.price_usd == 1.50
    assert vendor.in_stock is True
    assert vendor.last_updated is not None


def test_card_market_info_to_dict():
    """Test CardMarketInfo serialization."""
    vendor = VendorPrice(
        vendor_name="TCGPlayer",
        price_usd=1.50,
        price_eur=None,
        currency="USD",
        purchase_url="https://test.com"
    )

    info = CardMarketInfo(
        card_name="Lightning Bolt",
        set_code="M11",
        is_arena_only=False,
        available_in_paper=True,
        vendors=[vendor],
        best_price_usd=1.50,
        best_vendor="TCGPlayer"
    )

    result = info.to_dict()

    assert result['card_name'] == "Lightning Bolt"
    assert result['available_in_paper'] is True
    assert len(result['vendors']) == 1
    assert result['vendors'][0]['vendor_name'] == "TCGPlayer"
