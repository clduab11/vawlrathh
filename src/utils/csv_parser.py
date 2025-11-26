"""CSV parser for MTG Arena deck exports."""

import logging
import re
from typing import List, TYPE_CHECKING
from io import StringIO
import pandas as pd

from ..models.deck import Card, Deck
from .mana_calculator import calculate_cmc, parse_mana_cost, extract_colors

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..services.scryfall_service import ScryfallService


# Custom header format: Id, Name, Set, Color, Rarity, Count
MULTIVERSE_ID_HEADERS = {'id', 'name', 'set', 'color', 'rarity', 'count'}


def _has_multiverse_id_format(columns: List[str]) -> bool:
    """Check if the CSV has the custom Multiverse ID header format."""
    normalized = {col.lower().strip() for col in columns}
    return normalized == MULTIVERSE_ID_HEADERS


def parse_deck_string(deck_string: str) -> Deck:
    """
    Parse MTG Arena deck format string.
    
    Format examples:
        4 Lightning Bolt (M11) 146
        2 Counterspell (MH2) 267
        20 Island (ZNR) 381
    """
    lines = deck_string.strip().split('\n')
    mainboard = []
    sideboard = []
    current_section = mainboard
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check for sideboard marker
        if line.lower() in ['sideboard', 'sideboard:']:
            current_section = sideboard
            continue
        
        # Parse card line: "4 Card Name (SET) 123"
        # Split by parentheses to avoid ReDoS vulnerability
        paren_match = re.search(r'\(([A-Z0-9]+)\)\s+(\d+)$', line)
        if paren_match:
            # Extract quantity and name from beginning
            prefix = line[:paren_match.start()].strip()
            # Use simple split to avoid ReDoS
            parts = prefix.split(None, 1)  # Split on first whitespace
            if len(parts) == 2 and parts[0].isdigit():
                quantity = int(parts[0])
                card_name = parts[1].strip()
                set_code = paren_match.group(1)
                
                # Determine card type and mana cost (simplified - would need card database)
                card_type = determine_card_type(card_name)
                # WARNING: Text format parsing limitation - mana cost is not available
                # This will result in CMC=0 and no colors for all non-land cards,
                # which significantly affects deck analysis accuracy.
                # Use CSV format for accurate mana curve and color analysis.
                mana_cost = ""  # Would need card database lookup
                
                card = Card(
                    name=card_name,
                    quantity=quantity,
                    card_type=card_type,
                    mana_cost=mana_cost,
                    cmc=calculate_cmc(mana_cost),
                    colors=extract_colors(mana_cost),
                    set_code=set_code
                )
                current_section.append(card)
    
    return Deck(
        name="Imported Deck",
        mainboard=mainboard,
        sideboard=sideboard
    )


def parse_arena_csv(csv_content: str) -> Deck:
    """
    Parse CSV export from Steam MTG Arena or custom Multiverse ID format.
    
    Supported CSV formats:
        1. Standard format: Quantity,Name,Set,Collector Number,Type,Mana Cost,CMC,Colors,Rarity
        2. Multiverse ID format: Id,Name,Set,Color,Rarity,Count
    
    For Multiverse ID format, use parse_multiverse_id_csv_sync for synchronous parsing
    or parse_multiverse_id_csv for async parsing with Scryfall API lookup.
    """
    # Read CSV
    df = pd.read_csv(StringIO(csv_content))
    
    # Check if this is the Multiverse ID format
    if _has_multiverse_id_format(df.columns.tolist()):
        return parse_multiverse_id_csv_sync(csv_content)
    
    # Normalize column names for standard format
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
    
    mainboard = []
    sideboard = []
    
    for _, row in df.iterrows():
        # Handle 'quantity' column (standard format)
        # Default to 1 for standard format since missing quantity typically means 1 copy
        if 'quantity' in row and pd.notna(row.get('quantity')):
            quantity = int(row['quantity'])
        else:
            quantity = 1
        
        name = str(row.get('name', ''))
        set_code = str(row.get('set', '')) if 'set' in row else None
        card_type = str(row.get('type', 'Unknown'))
        mana_cost = str(row.get('mana_cost', ''))
        
        # Calculate CMC if not provided
        if 'cmc' in row:
            cmc = float(row['cmc'])
        else:
            cmc = calculate_cmc(mana_cost)
        
        # Extract colors if not provided
        if 'colors' in row and pd.notna(row['colors']):
            colors = [c.strip() for c in str(row['colors']).split(',')]
        else:
            colors = extract_colors(mana_cost)
        
        rarity = str(row.get('rarity', '')) if 'rarity' in row else None
        is_sideboard = row.get('sideboard', False) if 'sideboard' in row else False
        
        card = Card(
            name=name,
            quantity=quantity,
            card_type=card_type,
            mana_cost=mana_cost,
            cmc=cmc,
            colors=colors,
            rarity=rarity,
            set_code=set_code
        )
        
        if is_sideboard:
            sideboard.append(card)
        else:
            mainboard.append(card)
    
    return Deck(
        name="CSV Import",
        mainboard=mainboard,
        sideboard=sideboard
    )


def determine_card_type(card_name: str) -> str:
    """Determine card type based on name (simplified heuristic)."""
    # This is a simplified version - in production would use card database
    name_lower = card_name.lower()
    
    if any(land in name_lower for land in ['island', 'mountain', 'forest', 'plains', 'swamp']):
        return "Land"
    
    # Default to Unknown - should be looked up from card database
    return "Unknown"


async def parse_multiverse_id_csv(
    csv_content: str,
    scryfall_service: "ScryfallService"
) -> Deck:
    """
    Parse CSV with Multiverse ID format using Scryfall API for card lookup.
    
    Expected CSV format:
        Id,Name,Set,Color,Rarity,Count
    
    Where:
        - Id: Multiverse ID (used for Scryfall API lookup)
        - Name: Card name
        - Set: Non-standard set codes (ignored, fetched from API)
        - Color: Card color (ignored, fetched from API)
        - Rarity: Card rarity
        - Count: Quantity (0 is allowed)
    
    Args:
        csv_content: The CSV file content as a string
        scryfall_service: ScryfallService instance for API lookups
    
    Returns:
        Deck object with parsed cards
    """
    # Read CSV
    df = pd.read_csv(StringIO(csv_content))
    
    # Normalize column names
    df.columns = df.columns.str.strip().str.lower()
    
    mainboard = []
    
    for _, row in df.iterrows():
        # Map Count column to quantity (allow 0)
        quantity = int(row.get('count', 0))
        name = str(row.get('name', ''))
        multiverse_id = row.get('id')
        rarity = str(row.get('rarity', '')) if pd.notna(row.get('rarity')) else None
        
        # Default card data
        card_type = "Unknown"
        mana_cost = ""
        cmc = 0.0
        colors = []
        set_code = None
        
        # Try to fetch card data from Scryfall API using Multiverse ID
        if multiverse_id and pd.notna(multiverse_id):
            try:
                # Safely convert multiverse_id to int
                # Convert via float to handle pandas nullable int types that may be stored as float64
                mid_int = int(float(multiverse_id))
                card_data = await scryfall_service.get_card_by_multiverse_id(mid_int)
                if card_data:
                    # Extract data from Scryfall response
                    set_code = card_data.get('set', '').upper()
                    card_type = card_data.get('type_line', 'Unknown')
                    mana_cost = card_data.get('mana_cost', '')
                    cmc = float(card_data.get('cmc', 0))
                    colors = card_data.get('colors', [])
                    # Use Scryfall name if available (more accurate)
                    if card_data.get('name'):
                        name = card_data['name']
            except Exception as e:
                # If API lookup fails, fall back to CSV data
                logger.debug(
                    f'Failed to fetch card by Multiverse ID {mid_int}: {e}',
                    exc_info=True
                )
        
        # Fallback: try name lookup if Multiverse ID lookup failed
        if set_code is None and name:
            try:
                card_data = await scryfall_service.get_card_by_name(name)
                if card_data:
                    set_code = card_data.get('set', '').upper()
                    card_type = card_data.get('type_line', 'Unknown')
                    mana_cost = card_data.get('mana_cost', '')
                    cmc = float(card_data.get('cmc', 0))
                    colors = card_data.get('colors', [])
            except Exception as e:
                logger.debug(
                    f'Failed to fetch card by name {name}: {e}',
                    exc_info=True
                )
        
        card = Card(
            name=name,
            quantity=quantity,
            card_type=card_type,
            mana_cost=mana_cost,
            cmc=cmc,
            colors=colors,
            rarity=rarity,
            set_code=set_code
        )
        
        mainboard.append(card)
    
    return Deck(
        name="CSV Import",
        mainboard=mainboard,
        sideboard=[]
    )


def parse_multiverse_id_csv_sync(csv_content: str) -> Deck:
    """
    Parse CSV with Multiverse ID format synchronously (without API lookup).
    
    This is a fallback parser that uses only the data available in the CSV.
    The set codes from the CSV are used as-is (even if non-standard).
    
    Expected CSV format:
        Id,Name,Set,Color,Rarity,Count
    
    Args:
        csv_content: The CSV file content as a string
    
    Returns:
        Deck object with parsed cards
    """
    # Read CSV
    df = pd.read_csv(StringIO(csv_content))
    
    # Normalize column names
    df.columns = df.columns.str.strip().str.lower()
    
    mainboard = []
    
    for _, row in df.iterrows():
        # Map Count column to quantity (allow 0)
        quantity = int(row.get('count', 0))
        name = str(row.get('name', ''))
        set_code = str(row.get('set', '')) if pd.notna(row.get('set')) else None
        rarity = str(row.get('rarity', '')) if pd.notna(row.get('rarity')) else None
        
        # Map Color column to colors list
        color_value = row.get('color', '')
        if pd.notna(color_value) and str(color_value).strip():
            # Map color names to color codes
            color_map = {
                'white': 'W', 'blue': 'U', 'black': 'B', 
                'red': 'R', 'green': 'G', 'colorless': ''
            }
            color_str = str(color_value).strip().lower()
            if color_str in color_map:
                colors = [color_map[color_str]] if color_map[color_str] else []
            else:
                # Assume it's already in short form (W, U, B, R, G)
                colors = [c.strip().upper() for c in str(color_value).split(',') if c.strip()]
        else:
            colors = []
        
        # Determine card type from name (simplified)
        card_type = determine_card_type(name)
        
        card = Card(
            name=name,
            quantity=quantity,
            card_type=card_type,
            mana_cost="",  # Not available in this format
            cmc=0.0,  # Would need API lookup for accurate value
            colors=colors,
            rarity=rarity,
            set_code=set_code
        )
        
        mainboard.append(card)
    
    return Deck(
        name="CSV Import",
        mainboard=mainboard,
        sideboard=[]
    )
