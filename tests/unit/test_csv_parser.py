"""Tests for CSV parser."""

import pytest
from src.utils.csv_parser import (
    parse_deck_string, 
    parse_arena_csv,
    parse_multiverse_id_csv_sync,
    parse_multiverse_id_csv,
    _has_multiverse_id_format
)


def test_parse_deck_string_basic():
    """Test basic deck string parsing."""
    deck_string = """4 Lightning Bolt (M11) 146
2 Counterspell (MH2) 267
20 Island (ZNR) 381"""
    
    deck = parse_deck_string(deck_string)
    
    assert deck.name == "Imported Deck"
    assert len(deck.mainboard) == 3
    assert deck.mainboard[0].name == "Lightning Bolt"
    assert deck.mainboard[0].quantity == 4


def test_parse_deck_string_with_sideboard():
    """Test deck string parsing with sideboard."""
    deck_string = """4 Lightning Bolt (M11) 146
    
Sideboard:
2 Spell Pierce (XLN) 81"""
    
    deck = parse_deck_string(deck_string)
    
    assert len(deck.mainboard) == 1
    assert len(deck.sideboard) == 1
    assert deck.sideboard[0].name == "Spell Pierce"


def test_parse_arena_csv():
    """Test CSV parsing."""
    csv_content = """Quantity,Name,Set,Type,Mana Cost,CMC,Colors,Rarity
4,Lightning Bolt,M11,Instant,R,1,R,Uncommon
20,Island,ZNR,Land,,0,,Common"""
    
    deck = parse_arena_csv(csv_content)
    
    assert deck.name == "CSV Import"
    assert len(deck.mainboard) == 2
    assert deck.mainboard[0].name == "Lightning Bolt"
    assert deck.mainboard[0].quantity == 4
    assert deck.mainboard[0].colors == ["R"]


def test_has_multiverse_id_format():
    """Test detection of Multiverse ID format headers."""
    # Should match
    assert _has_multiverse_id_format(['Id', 'Name', 'Set', 'Color', 'Rarity', 'Count'])
    assert _has_multiverse_id_format(['id', 'name', 'set', 'color', 'rarity', 'count'])
    assert _has_multiverse_id_format([' Id ', ' Name ', ' Set ', ' Color ', ' Rarity ', ' Count '])
    
    # Should not match
    assert not _has_multiverse_id_format(['Quantity', 'Name', 'Set', 'Type', 'Mana Cost'])
    assert not _has_multiverse_id_format(['Id', 'Name', 'Set'])  # Missing columns


def test_parse_multiverse_id_csv_sync_basic():
    """Test synchronous parsing of Multiverse ID format CSV."""
    csv_content = """Id,Name,Set,Color,Rarity,Count
6873,Crash of Rhinos,AA4,Green,Common,2
7649,Necromancy,AA3,Black,Uncommon,1
9135,Mind Stone,HA1,Colorless,Common,4"""
    
    deck = parse_multiverse_id_csv_sync(csv_content)
    
    assert deck.name == "CSV Import"
    assert len(deck.mainboard) == 3
    
    # Check first card
    card1 = deck.mainboard[0]
    assert card1.name == "Crash of Rhinos"
    assert card1.quantity == 2
    assert card1.set_code == "AA4"  # Uses CSV value in sync mode
    assert card1.rarity == "Common"
    assert card1.colors == ["G"]  # Green -> G
    
    # Check second card
    card2 = deck.mainboard[1]
    assert card2.name == "Necromancy"
    assert card2.quantity == 1
    assert card2.colors == ["B"]  # Black -> B
    
    # Check third card (colorless)
    card3 = deck.mainboard[2]
    assert card3.name == "Mind Stone"
    assert card3.quantity == 4
    assert card3.colors == []  # Colorless -> empty list


def test_parse_multiverse_id_csv_sync_zero_count():
    """Test that Count: 0 rows are handled without errors."""
    csv_content = """Id,Name,Set,Color,Rarity,Count
6873,Crash of Rhinos,AA4,Green,Common,0
7649,Necromancy,AA3,Black,Uncommon,3"""
    
    deck = parse_multiverse_id_csv_sync(csv_content)
    
    assert len(deck.mainboard) == 2
    assert deck.mainboard[0].quantity == 0  # Count 0 is allowed
    assert deck.mainboard[1].quantity == 3


def test_parse_arena_csv_detects_multiverse_format():
    """Test that parse_arena_csv auto-detects Multiverse ID format."""
    csv_content = """Id,Name,Set,Color,Rarity,Count
6873,Crash of Rhinos,AA4,Green,Common,2"""
    
    deck = parse_arena_csv(csv_content)
    
    assert deck.name == "CSV Import"
    assert len(deck.mainboard) == 1
    assert deck.mainboard[0].name == "Crash of Rhinos"
    assert deck.mainboard[0].quantity == 2
    assert deck.mainboard[0].colors == ["G"]


def test_parse_multiverse_id_csv_sync_color_mapping():
    """Test color name to code mapping."""
    csv_content = """Id,Name,Set,Color,Rarity,Count
1,White Card,TEST,White,Common,1
2,Blue Card,TEST,Blue,Common,1
3,Black Card,TEST,Black,Common,1
4,Red Card,TEST,Red,Common,1
5,Green Card,TEST,Green,Common,1
6,Colorless Card,TEST,Colorless,Common,1"""
    
    deck = parse_multiverse_id_csv_sync(csv_content)
    
    assert deck.mainboard[0].colors == ["W"]
    assert deck.mainboard[1].colors == ["U"]
    assert deck.mainboard[2].colors == ["B"]
    assert deck.mainboard[3].colors == ["R"]
    assert deck.mainboard[4].colors == ["G"]
    assert deck.mainboard[5].colors == []  # Colorless


@pytest.mark.asyncio
async def test_parse_multiverse_id_csv_async_with_mock():
    """Test async parsing with mocked Scryfall service."""
    from unittest.mock import AsyncMock, MagicMock
    
    csv_content = """Id,Name,Set,Color,Rarity,Count
6873,Crash of Rhinos,AA4,Green,Common,2"""
    
    # Create mock Scryfall service
    mock_scryfall = MagicMock()
    mock_scryfall.get_card_by_multiverse_id = AsyncMock(return_value={
        'name': 'Crash of Rhinos',
        'set': 'mir',
        'type_line': 'Creature — Rhino',
        'mana_cost': '{3}{G}{G}',
        'cmc': 5.0,
        'colors': ['G']
    })
    
    deck = await parse_multiverse_id_csv(csv_content, mock_scryfall)
    
    assert deck.name == "CSV Import"
    assert len(deck.mainboard) == 1
    
    card = deck.mainboard[0]
    assert card.name == "Crash of Rhinos"
    assert card.quantity == 2
    assert card.set_code == "MIR"  # Fetched from API (uppercased)
    assert card.card_type == "Creature — Rhino"
    assert card.mana_cost == "{3}{G}{G}"
    assert card.cmc == 5.0
    assert card.colors == ["G"]


@pytest.mark.asyncio
async def test_parse_multiverse_id_csv_async_fallback_to_name():
    """Test async parsing falls back to name lookup if Multiverse ID fails."""
    from unittest.mock import AsyncMock, MagicMock
    
    csv_content = """Id,Name,Set,Color,Rarity,Count
,Unknown Card,TEST,Blue,Rare,1"""
    
    # Create mock Scryfall service
    mock_scryfall = MagicMock()
    mock_scryfall.get_card_by_multiverse_id = AsyncMock(return_value=None)
    mock_scryfall.get_card_by_name = AsyncMock(return_value={
        'name': 'Unknown Card',
        'set': 'test',
        'type_line': 'Instant',
        'mana_cost': '{U}',
        'cmc': 1.0,
        'colors': ['U']
    })
    
    deck = await parse_multiverse_id_csv(csv_content, mock_scryfall)
    
    assert len(deck.mainboard) == 1
    card = deck.mainboard[0]
    assert card.set_code == "TEST"  # Fetched from name lookup
