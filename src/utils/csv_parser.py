"""CSV parser for MTG Arena deck exports."""

import gc
import re
import logging
from typing import List, Tuple, Generator
from io import StringIO
import pandas as pd

from ..models.deck import Card, Deck
from .mana_calculator import calculate_cmc, parse_mana_cost, extract_colors

logger = logging.getLogger(__name__)


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
    Parse CSV export from Steam MTG Arena.
    
    Expected CSV format:
        Quantity,Name,Set,Collector Number,Type,Mana Cost,CMC,Colors,Rarity
    """
    # Read CSV
    df = pd.read_csv(StringIO(csv_content))
    
    # Normalize column names
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
    
    mainboard = []
    sideboard = []
    
    for _, row in df.iterrows():
        quantity = int(row.get('quantity', 1))
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


def count_csv_rows(filepath: str) -> int:
    """
    Efficiently count rows in CSV without loading into memory.
    
    Args:
        filepath: Path to the CSV file
        
    Returns:
        Number of data rows (excluding header)
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        # Count lines, subtract 1 for header
        return sum(1 for _ in f) - 1


def _parse_card_row(row: pd.Series) -> Card:
    """
    Parse a single CSV row into a Card object.
    
    Args:
        row: pandas Series with normalized column names
        
    Returns:
        Card object
        
    Raises:
        ValueError: If required fields are missing or invalid
    """
    # Handle quantity - default to 1 if missing
    quantity = int(row.get('quantity', 1) or 1)
    
    # Get name - required field
    name = str(row.get('name', '')).strip()
    if not name:
        raise ValueError("Card name is required")
    
    # Parse CMC - handle various formats
    cmc_val = row.get('cmc', 0)
    try:
        cmc = int(float(cmc_val)) if pd.notna(cmc_val) else 0
    except (ValueError, TypeError):
        cmc = 0
    
    # Parse colors - handle string or list
    colors_raw = row.get('colors', '')
    if pd.isna(colors_raw):
        colors = []
    elif isinstance(colors_raw, str):
        colors = [c.strip() for c in colors_raw.split(',') if c.strip()]
    else:
        colors = list(colors_raw) if colors_raw else []
    
    return Card(
        name=name,
        quantity=quantity,
        card_type=str(row.get('type', '')).strip() or None,
        mana_cost=str(row.get('mana_cost', '')).strip() or None,
        cmc=cmc,
        colors=colors,
        rarity=str(row.get('rarity', '')).strip() or None,
        set_code=str(row.get('set', '')).strip() or None
    )


def parse_arena_csv_chunked(
    filepath: str,
    chunk_size: int = 5000
) -> Generator[Tuple[int, List[Card], List[int]], None, None]:
    """
    Parse large CSV file in chunks using pandas chunked reader.
    
    This is memory-efficient for large collection CSVs (up to 70K+ rows).
    
    Args:
        filepath: Path to the CSV file
        chunk_size: Number of rows per chunk (default 5000)
        
    Yields:
        Tuple of (chunk_index, cards_list, failed_row_indices)
        
    Example:
        for chunk_idx, cards, failed in parse_arena_csv_chunked("collection.csv"):
            all_cards.extend(cards)
            all_failed.extend(failed)
    """
    chunk_iter = pd.read_csv(
        filepath,
        chunksize=chunk_size,
        dtype={
            'Quantity': 'Int64',  # Nullable integer
            'Name': 'string',
            'CMC': 'Float64',     # Nullable float
        },
        on_bad_lines='warn',
        encoding='utf-8'
    )
    
    for chunk_idx, chunk_df in enumerate(chunk_iter):
        # Normalize column names (lowercase, underscores)
        chunk_df.columns = (
            chunk_df.columns.str.strip()
            .str.lower()
            .str.replace(' ', '_')
            .str.replace('-', '_')
        )
        
        cards: List[Card] = []
        failed_rows: List[int] = []
        
        for row_idx, row in chunk_df.iterrows():
            global_row_idx = chunk_idx * chunk_size + row_idx
            try:
                card = _parse_card_row(row)
                cards.append(card)
            except Exception as e:
                failed_rows.append(global_row_idx)
                logger.warning(f"Failed to parse row {global_row_idx}: {e}")
        
        yield chunk_idx, cards, failed_rows
        
        # Explicit memory cleanup after each chunk
        del chunk_df
        gc.collect()
