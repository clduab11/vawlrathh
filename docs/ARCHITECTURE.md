# Arena Improver - System Architecture

This document describes the system architecture, async patterns, and service design for Arena Improver.

> **📖 Related Documentation:**
> - **[../DEPLOYMENT.md](../DEPLOYMENT.md)** - Deployment guide
> - **[HF_DEPLOYMENT.md](HF_DEPLOYMENT.md)** - HuggingFace Spaces deployment
> - **[../CLAUDE.md](../CLAUDE.md)** - Claude AI integration

## 🎯 Overview

Arena Improver is an async Python application using FastAPI for the backend API and Gradio for the web UI. The architecture emphasizes:

- **Connection pooling** for efficient HTTP requests
- **Async context managers** for proper resource lifecycle
- **Modular service design** with clear dependencies
- **Dual-port architecture** for API and UI separation

## 🏗️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User Interface                        │
├─────────────────────────────────────────────────────────┤
│   Gradio UI (Port 7861)          FastAPI Docs            │
│   ├─ Deck Uploads                /proxy/7860/docs        │
│   ├─ Chat Interface                                      │
│   └─ Meta Dashboards                                     │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              FastAPI Server (Port 7860)                  │
├─────────────────────────────────────────────────────────┤
│   /api/v1/upload/*     │   /api/v1/analyze/*            │
│   /api/v1/optimize/*   │   /api/v1/ws/chat/*            │
│   /health              │   /metrics                      │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                   Service Layer                          │
├─────────────────────────────────────────────────────────┤
│   ScryfallService      │   CardMarketService             │
│   (Connection Pool)    │   (Uses ScryfallService)        │
│                        │                                 │
│   SmartSQLService      │   ChatAgent                     │
│   (Async SQLAlchemy)   │   (WebSocket Handler)           │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                  External APIs                           │
├─────────────────────────────────────────────────────────┤
│   Scryfall API    │   OpenAI API    │   Anthropic API   │
│   (Card Data)     │   (Inference)   │   (Consensus)     │
└─────────────────────────────────────────────────────────┘
```

## 🔌 HTTP Client Strategy

### Shared AsyncClient with Connection Pooling

Services use a shared `httpx.AsyncClient` to reuse TCP connections, reducing overhead especially for rate-limited APIs like Scryfall (100ms between requests).

#### Configuration

```python
# src/services/scryfall_service.py
self._client = httpx.AsyncClient(
    timeout=10.0,
    limits=httpx.Limits(
        max_keepalive_connections=5,
        max_connections=10
    )
)
```

#### Benefits

1. **Connection Reuse**: Avoids TCP handshake overhead per request
2. **Rate Limit Efficiency**: Maintains warm connections during rate limit delays
3. **Resource Management**: Centralized cleanup prevents connection leaks

### Async Context Manager Pattern

Services implement the async context manager protocol for proper lifecycle management:

```python
async with ScryfallService() as scryfall:
    card = await scryfall.get_card_by_name("Lightning Bolt")
# Client automatically closed on exit
```

Or manual management:

```python
service = ScryfallService()
await service._ensure_client()
try:
    card = await service.get_card_by_name("Lightning Bolt")
finally:
    await service.close()
```

## 🔧 Service Architecture

### ScryfallService

**Location**: `src/services/scryfall_service.py`

Handles all Scryfall API interactions with caching and rate limiting.

**Key Features**:
- 24-hour response caching
- 100ms rate limit enforcement
- Connection pooling via shared AsyncClient

**Public Methods**:
- `get_card_by_name()` - Fetch card by name/set
- `search_cards()` - Search with Scryfall syntax
- `is_arena_only()` - Check if card is digital-only
- `get_card_prices()` - Fetch pricing data
- `batch_check_arena_availability()` - Bulk availability check

### CardMarketService

**Location**: `src/services/card_market_service.py`

Provides card pricing and vendor information using ScryfallService.

**Dependency**: Depends on `ScryfallService` for card data.

**Lifecycle Management**:
```python
async with CardMarketService() as market:
    info = await market.get_card_market_info("Lightning Bolt")
# Both CardMarketService and its ScryfallService are cleaned up
```

**Public Methods**:
- `get_card_market_info()` - Complete market info for a card
- `get_deck_market_info()` - Market info for entire deck
- `find_card_alternatives()` - Alternative printings
- `get_budget_replacements()` - Budget-friendly options

### Service Dependencies

```
CardMarketService
    └── ScryfallService
            └── httpx.AsyncClient (pooled)

ChatAgent
    ├── OpenAI API
    └── Anthropic API (consensus)

SmartSQLService
    └── SQLAlchemy AsyncSession
```

## 🌐 Gradio + FastAPI Integration

### Dual-Port Architecture

The HF Space runs two servers simultaneously:

| Port | Service | Purpose |
|------|---------|---------|
| 7860 | FastAPI | API endpoints, WebSocket, health checks |
| 7861 | Gradio | Web UI with tabs for uploads, chat, meta |

### App Entry Point

**Location**: `app.py`

**Startup Sequence**:
1. Kill existing uvicorn processes
2. Start FastAPI server on port 7860
3. Wait for health check (max 60s)
4. Create and launch Gradio interface on 7861

### Shared Client in Gradio Handlers

Gradio handlers use a module-level shared client for UI → API requests:

```python
# app.py
_shared_client: Optional[httpx.AsyncClient] = None

async def get_shared_client() -> httpx.AsyncClient:
    global _shared_client
    if _shared_client is None:
        _shared_client = httpx.AsyncClient(
            timeout=60.0,
            limits=httpx.Limits(max_keepalive_connections=10)
        )
    return _shared_client
```

### Modular Tab Builders

Tabs are registered via the `@builder_registry` decorator:

```python
@builder_registry(
    name="deck_uploader",
    description="Deck CSV and text imports",
    endpoints=["/api/v1/upload/csv", "/api/v1/upload/text"],
)
def build_deck_uploader_tab():
    # ... Gradio components
```

## 💬 WebSocket Chat

### Architecture

```
Client (Browser)
    │
    ▼ WebSocket
┌─────────────────┐
│  FastAPI WS     │
│  /api/v1/ws/    │
│  chat/{user_id} │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   ChatAgent     │
│   ├─ GPT-4      │
│   └─ Consensus  │
└─────────────────┘
```

### Message Format

**Request**:
```json
{
  "type": "chat",
  "message": "How do I beat control?",
  "context": {"deck_id": 1}
}
```

**Response**:
```json
{
  "type": "response",
  "response": "Pack hand disruption...",
  "consensus_checked": true,
  "consensus_passed": true
}
```

## 🧠 MCP Integration

Arena Improver integrates with MCP (Model Context Protocol) for enhanced capabilities:

### MCP Tools

| Tool | Purpose |
|------|---------|
| `parse_deck_csv` | Import from Steam Arena CSV |
| `parse_deck_text` | Import from Arena text format |
| `analyze_deck` | Full deck analysis |
| `optimize_deck` | AI-powered suggestions |
| `find_card_market_links` | Get purchase info |

### External MCP Servers

Configured in `mcp_config.json`:

- **Memory**: Persistent conversation context
- **Sequential Thinking**: Multi-step reasoning
- **cld-omnisearch**: Real-time meta data (Tavily/Exa)

## 🗄️ Database Layer

### SmartSQLService

**Location**: `src/services/smart_sql.py`

Uses SQLAlchemy with async support for database operations.

**Features**:
- Async session management
- In-memory testing support
- Deck and match history storage

## ⚡ Performance Considerations

### Connection Pooling Benefits

| Metric | Per-Request Client | Pooled Client |
|--------|-------------------|---------------|
| TCP Handshakes | N | 1 |
| Memory Overhead | High | Low |
| Rate Limit Efficiency | Poor | Good |

### Best Practices

1. **Use Context Managers**: Ensures cleanup
   ```python
   async with ScryfallService() as service:
       # operations
   ```

2. **Batch Operations**: Group API calls when possible
   ```python
   results = await service.batch_check_arena_availability(card_names)
   ```

3. **Cache Utilization**: Services cache for 24 hours
   ```python
   # Second call hits cache
   card1 = await service.get_card_by_name("Bolt")
   card2 = await service.get_card_by_name("Bolt")  # cached
   ```

## 🔍 Troubleshooting

### Connection Leaks

**Symptom**: "Too many open connections" or memory growth

**Causes**:
- Not closing services properly
- Exception during operation without cleanup

**Solution**: Always use async context managers or explicit `close()`:
```python
service = ScryfallService()
try:
    await service._ensure_client()
    # operations
finally:
    await service.close()
```

### Async Deadlocks

**Symptom**: Requests hang indefinitely

**Causes**:
- Mixing sync and async code incorrectly
- Forgetting `await` on coroutines

**Solution**: Ensure all async functions are awaited:
```python
# Wrong
result = service.get_card_by_name("Bolt")  # Returns coroutine, not result

# Correct
result = await service.get_card_by_name("Bolt")
```

### Rate Limit Errors

**Symptom**: 429 responses from Scryfall

**Cause**: Rate limit bypass or pooling misconfiguration

**Solution**: Check that `_rate_limit()` is called before requests:
```python
await self._rate_limit()  # Enforces 100ms delay
response = await self._client.get(...)
```

## 📁 Key Files Reference

| File | Purpose |
|------|---------|
| `app.py` | Gradio UI + FastAPI startup |
| `src/main.py` | FastAPI application |
| `src/services/scryfall_service.py` | Scryfall API with pooling |
| `src/services/card_market_service.py` | Market pricing service |
| `src/services/smart_sql.py` | Database operations |
| `tests/conftest.py` | Test fixtures for async services |

---

*"Architecture is the first thing you get wrong, and the last thing you get right."*
— **Vawlrathh, The Small'n**
