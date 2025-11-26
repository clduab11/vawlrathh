# Upload Tabs Architecture Specification

> **Document Version:** 1.0  
> **Created:** 2025-11-26  
> **Purpose:** Architecture for Deck Uploads and Collection Upload tabs

## Overview

This document specifies the architecture for:
1. **Deck Uploads Tab** - Standard deck CSV imports (enhancement of existing)
2. **Collection Upload Tab** - Large-scale CSV handling (up to 70,000 rows)

## Key Design Decisions

- Chunk size: 5,000 rows per chunk
- Memory-efficient: Generator-based processing
- Progress tracking: gr.Progress integration
- Timeout prevention: Progress updates reset HTTP timeout

## Files Modified

- `src/models/deck.py` - Added Collection, CollectionProcessingResult
- `src/utils/csv_parser.py` - Added chunked parser functions
- `app.py` - UI components and handlers (Phase 2)

See code for implementation details.