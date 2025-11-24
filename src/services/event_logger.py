"""Event logging system for strategic recommendations and agent actions."""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import aiofiles

logger = logging.getLogger(__name__)


@dataclass
class StrategyEvent:
    """Strategic recommendation or action event."""
    event_id: str
    event_type: str  # 'recommendation', 'analysis', 'optimization', 'consensus_check', 'chat'
    timestamp: datetime
    user_id: Optional[str]
    deck_id: Optional[int]
    agent: str  # 'vawlrathh', 'sonnet_consensus', 'deck_analyzer', 'smart_inference'
    action: str
    data: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    duration_ms: Optional[float] = None
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        event_dict = asdict(self)
        event_dict['timestamp'] = self.timestamp.isoformat()
        return event_dict


class EventLogger:
    """
    Event logger for tracking strategic recommendations and agent actions.

    Stores events in JSON format for hackathon demo and analysis.
    """

    def __init__(self, log_dir: str = "data/events"):
        """
        Initialize event logger.

        Args:
            log_dir: Directory to store event logs
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.events: List[StrategyEvent] = []
        self._lock = asyncio.Lock()

    async def log_event(self, event: StrategyEvent):
        """
        Log a strategy event.

        Args:
            event: StrategyEvent to log
        """
        async with self._lock:
            self.events.append(event)

            # Write to daily log file
            log_file = self.log_dir / f"events_{datetime.now().strftime('%Y-%m-%d')}.jsonl"

            try:
                async with aiofiles.open(log_file, 'a') as f:
                    await f.write(json.dumps(event.to_dict()) + '\n')
            except Exception as e:
                logger.error(f"Error writing event log: {e}")

    async def log_recommendation(
        self,
        deck_id: int,
        recommendations: List[str],
        agent: str = "smart_inference",
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log a deck recommendation event.

        Args:
            deck_id: Deck ID
            recommendations: List of recommendations
            agent: Agent that generated recommendations
            user_id: Optional user ID
            metadata: Additional metadata

        Returns:
            Event ID
        """
        event_id = f"rec_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        event = StrategyEvent(
            event_id=event_id,
            event_type="recommendation",
            timestamp=datetime.now(),
            user_id=user_id,
            deck_id=deck_id,
            agent=agent,
            action="generate_recommendations",
            data={
                "recommendations": recommendations,
                "count": len(recommendations),
                "metadata": metadata or {}
            }
        )

        await self.log_event(event)
        return event_id

    async def log_analysis(
        self,
        deck_id: int,
        analysis_result: Dict[str, Any],
        agent: str = "deck_analyzer",
        user_id: Optional[str] = None
    ) -> str:
        """
        Log a deck analysis event.

        Args:
            deck_id: Deck ID
            analysis_result: Analysis results
            agent: Agent that performed analysis
            user_id: Optional user ID

        Returns:
            Event ID
        """
        event_id = f"ana_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        event = StrategyEvent(
            event_id=event_id,
            event_type="analysis",
            timestamp=datetime.now(),
            user_id=user_id,
            deck_id=deck_id,
            agent=agent,
            action="analyze_deck",
            data=analysis_result
        )

        await self.log_event(event)
        return event_id

    async def log_consensus_check(
        self,
        primary_response: str,
        consensus_result: Dict[str, Any],
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log a consensus check event.

        Args:
            primary_response: Primary agent response
            consensus_result: Consensus check result
            user_id: Optional user ID
            context: Optional context

        Returns:
            Event ID
        """
        event_id = f"con_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        event = StrategyEvent(
            event_id=event_id,
            event_type="consensus_check",
            timestamp=datetime.now(),
            user_id=user_id,
            deck_id=context.get('deck_id') if context else None,
            agent="sonnet_consensus",
            action="check_consensus",
            data={
                "primary_response": primary_response,
                "consensus_passed": consensus_result.get('passed', True),
                "disagreement_reason": consensus_result.get('disagreement_reason'),
                "severity": consensus_result.get('severity'),
                "context": context or {}
            },
            success=consensus_result.get('passed', True)
        )

        await self.log_event(event)
        return event_id

    async def log_chat_interaction(
        self,
        user_message: str,
        agent_response: str,
        agent: str = "vawlrathh",
        user_id: Optional[str] = None,
        consensus_result: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log a chat interaction event.

        Args:
            user_message: User's message
            agent_response: Agent's response
            agent: Agent name
            user_id: Optional user ID
            consensus_result: Optional consensus check result

        Returns:
            Event ID
        """
        event_id = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        event = StrategyEvent(
            event_id=event_id,
            event_type="chat",
            timestamp=datetime.now(),
            user_id=user_id,
            deck_id=None,
            agent=agent,
            action="chat_interaction",
            data={
                "user_message": user_message,
                "agent_response": agent_response,
                "consensus_checked": consensus_result is not None,
                "consensus_result": consensus_result
            }
        )

        await self.log_event(event)
        return event_id

    async def log_purchase_lookup(
        self,
        deck_id: int,
        cards_found: int,
        purchasable_cards: int,
        arena_only_cards: int,
        total_price_usd: float,
        user_id: Optional[str] = None
    ) -> str:
        """
        Log a card purchase lookup event.

        Args:
            deck_id: Deck ID
            cards_found: Total cards found
            purchasable_cards: Number of purchasable cards
            arena_only_cards: Number of Arena-only cards
            total_price_usd: Total price in USD
            user_id: Optional user ID

        Returns:
            Event ID
        """
        event_id = f"pur_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        event = StrategyEvent(
            event_id=event_id,
            event_type="purchase_lookup",
            timestamp=datetime.now(),
            user_id=user_id,
            deck_id=deck_id,
            agent="card_market_service",
            action="lookup_purchase_info",
            data={
                "cards_found": cards_found,
                "purchasable_cards": purchasable_cards,
                "arena_only_cards": arena_only_cards,
                "total_price_usd": total_price_usd
            }
        )

        await self.log_event(event)
        return event_id

    async def get_events_by_type(
        self,
        event_type: str,
        limit: int = 100
    ) -> List[StrategyEvent]:
        """
        Get events by type.

        Args:
            event_type: Event type to filter
            limit: Maximum number of events

        Returns:
            List of events
        """
        async with self._lock:
            filtered = [e for e in self.events if e.event_type == event_type]
            return filtered[-limit:]

    async def get_events_by_deck(
        self,
        deck_id: int,
        limit: int = 100
    ) -> List[StrategyEvent]:
        """
        Get events for a specific deck.

        Args:
            deck_id: Deck ID
            limit: Maximum number of events

        Returns:
            List of events
        """
        async with self._lock:
            filtered = [e for e in self.events if e.deck_id == deck_id]
            return filtered[-limit:]

    async def get_events_by_agent(
        self,
        agent: str,
        limit: int = 100
    ) -> List[StrategyEvent]:
        """
        Get events by agent.

        Args:
            agent: Agent name
            limit: Maximum number of events

        Returns:
            List of events
        """
        async with self._lock:
            filtered = [e for e in self.events if e.agent == agent]
            return filtered[-limit:]

    async def get_recent_events(
        self,
        limit: int = 100
    ) -> List[StrategyEvent]:
        """
        Get recent events.

        Args:
            limit: Maximum number of events

        Returns:
            List of events
        """
        async with self._lock:
            return self.events[-limit:]

    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get event statistics.

        Returns:
            Dict with statistics
        """
        async with self._lock:
            total_events = len(self.events)

            event_types = {}
            agents = {}
            success_count = 0

            for event in self.events:
                # Count by event type
                event_types[event.event_type] = event_types.get(event.event_type, 0) + 1

                # Count by agent
                agents[event.agent] = agents.get(event.agent, 0) + 1

                # Count successes
                if event.success:
                    success_count += 1

            return {
                "total_events": total_events,
                "event_types": event_types,
                "agents": agents,
                "success_rate": success_count / total_events if total_events > 0 else 0.0,
                "recent_events": [e.to_dict() for e in self.events[-10:]]
            }

    async def export_events(
        self,
        output_file: str,
        event_type: Optional[str] = None
    ):
        """
        Export events to JSON file.

        Args:
            output_file: Output file path
            event_type: Optional event type filter
        """
        async with self._lock:
            events_to_export = self.events

            if event_type:
                events_to_export = [e for e in events_to_export if e.event_type == event_type]

            export_data = {
                "exported_at": datetime.now().isoformat(),
                "total_events": len(events_to_export),
                "events": [e.to_dict() for e in events_to_export]
            }

            async with aiofiles.open(output_file, 'w') as f:
                await f.write(json.dumps(export_data, indent=2))

            logger.info(f"Exported {len(events_to_export)} events to {output_file}")


# Global event logger instance
_event_logger: Optional[EventLogger] = None


def get_event_logger() -> EventLogger:
    """Get global event logger instance."""
    global _event_logger
    if _event_logger is None:
        _event_logger = EventLogger()
    return _event_logger
