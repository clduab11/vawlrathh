"""WebSocket routes for real-time chat with Vawlrathh."""

import json
import logging
from typing import Dict, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

from ..services.chat_agent import ConcurrentChatService
from ..services.smart_sql import SmartSQLService

logger = logging.getLogger(__name__)

router = APIRouter()

# Active WebSocket connections
active_connections: Dict[str, WebSocket] = {}

# Chat service instances per connection
chat_services: Dict[str, ConcurrentChatService] = {}


class ConnectionManager:
    """Manages WebSocket connections for chat."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.chat_services: Dict[str, ConcurrentChatService] = {}

    async def connect(
        self,
        websocket: WebSocket,
        client_id: str,
        openai_key: Optional[str] = None,
        anthropic_key: Optional[str] = None
    ):
        """Accept new WebSocket connection."""
        await websocket.accept()
        self.active_connections[client_id] = websocket

        # Initialize chat service for this connection
        self.chat_services[client_id] = ConcurrentChatService(
            openai_api_key=openai_key,
            anthropic_api_key=anthropic_key,
            enable_consensus=True
        )

        logger.info(f"Client {client_id} connected")

    def disconnect(self, client_id: str):
        """Remove connection."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]

        if client_id in self.chat_services:
            self.chat_services[client_id].clear_history()
            del self.chat_services[client_id]

        logger.info(f"Client {client_id} disconnected")

    async def send_message(self, client_id: str, message: dict):
        """Send message to specific client."""
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json(message)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        for client_id, websocket in self.active_connections.items():
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json(message)


manager = ConnectionManager()


@router.websocket("/ws/chat/{client_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    client_id: str,
    openai_key: Optional[str] = None,
    anthropic_key: Optional[str] = None
):
    """
    WebSocket endpoint for real-time chat with Vawlrathh.

    Message format (client -> server):
    {
        "type": "chat",
        "message": "Your message here",
        "context": {  // Optional
            "deck_id": 1,
            "include_analysis": true
        }
    }

    Response format (server -> client):
    {
        "type": "response",
        "response": "Vawlrathh's response",
        "agent": "vawlrathh",
        "timestamp": "2025-01-01T00:00:00",
        "consensus_checked": true,
        "consensus_passed": true,
        "consensus_breaker": {  // Only if consensus failed
            "reason": "...",
            "severity": "warning",
            "warning": "⚠️ ConsensusBreaker: ..."
        }
    }
    """
    await manager.connect(websocket, client_id, openai_key, anthropic_key)

    try:
        # Send welcome message
        await manager.send_message(client_id, {
            "type": "system",
            "message": "Connected to Vawlrathh, The Small'n. What do you want?",
            "agent": "system"
        })

        # Message loop
        while True:
            # Receive message
            data = await websocket.receive_text()

            try:
                message_data = json.loads(data)
            except json.JSONDecodeError:
                await manager.send_message(client_id, {
                    "type": "error",
                    "error": "Invalid JSON format"
                })
                continue

            message_type = message_data.get("type")

            if message_type == "chat":
                await handle_chat_message(client_id, message_data)
            elif message_type == "clear":
                await handle_clear_history(client_id)
            elif message_type == "ping":
                await manager.send_message(client_id, {"type": "pong"})
            else:
                await manager.send_message(client_id, {
                    "type": "error",
                    "error": f"Unknown message type: {message_type}"
                })

    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
        manager.disconnect(client_id)


async def handle_chat_message(client_id: str, message_data: dict):
    """Handle incoming chat message."""
    user_message = message_data.get("message", "")

    if not user_message:
        await manager.send_message(client_id, {
            "type": "error",
            "error": "Empty message"
        })
        return

    # Get context if provided
    context = None
    if "context" in message_data:
        context = await build_context(message_data["context"])

    # Send typing indicator
    await manager.send_message(client_id, {
        "type": "typing",
        "agent": "vawlrathh"
    })

    # Get chat service for this client
    chat_service = manager.chat_services.get(client_id)

    if not chat_service:
        await manager.send_message(client_id, {
            "type": "error",
            "error": "Chat service not initialized"
        })
        return

    try:
        # Get response from Vawlrathh with consensus check
        result = await chat_service.chat(user_message, context)

        # Send response
        response_msg = {
            "type": "response",
            **result
        }

        # Add consensus breaker notification if failed
        if not result.get("consensus_passed", True):
            response_msg["type"] = "consensus_breaker"

        await manager.send_message(client_id, response_msg)

    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        await manager.send_message(client_id, {
            "type": "error",
            "error": f"Error processing message: {str(e)}"
        })


async def handle_clear_history(client_id: str):
    """Clear chat history for client."""
    chat_service = manager.chat_services.get(client_id)

    if chat_service:
        chat_service.clear_history()

    await manager.send_message(client_id, {
        "type": "system",
        "message": "History cleared. Start fresh."
    })


async def build_context(context_data: dict) -> dict:
    """Build context from client request."""
    context = {}

    # Add deck context if requested
    if "deck_id" in context_data:
        deck_id = context_data["deck_id"]
        sql_service = SmartSQLService()

        try:
            await sql_service.init_db()
            deck = await sql_service.get_deck(deck_id)

            if deck:
                context["deck"] = {
                    "name": deck.name,
                    "format": deck.format,
                    "card_count": len(deck.mainboard)
                }

                # Add analysis if requested
                if context_data.get("include_analysis"):
                    from ..services.deck_analyzer import DeckAnalyzer
                    analyzer = DeckAnalyzer()
                    analysis = await analyzer.analyze_deck(deck)

                    context["analysis"] = {
                        "overall_score": analysis.overall_score,
                        "strengths": analysis.strengths,
                        "weaknesses": analysis.weaknesses
                    }

        except Exception as e:
            logger.error(f"Error building deck context: {e}")

    return context


@router.get("/chat/health")
async def chat_health_check():
    """Health check for chat service."""
    return {
        "status": "healthy",
        "service": "Vawlrathh Chat Service",
        "active_connections": len(manager.active_connections)
    }
