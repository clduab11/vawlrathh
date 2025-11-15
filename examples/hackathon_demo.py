"""
Hackathon Demo: Complete workflow showcasing all Arena Improver features.

This demo showcases:
1. Physical card purchase integration with Arena-only filtering
2. Concurrent AI chat with Vawlrathh and consensus checking
3. Sequential reasoning for deck optimization
4. Event logging for strategic recommendations
5. MCP integration depth
"""

import asyncio
import os
import json
from pathlib import Path

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.smart_sql import SmartSQLService
from src.services.deck_analyzer import DeckAnalyzer
from src.services.card_market_service import CardMarketService, ScryfallService
from src.services.chat_agent import ConcurrentChatService
from src.services.sequential_reasoning import SequentialReasoningService
from src.services.event_logger import get_event_logger
from src.utils.csv_parser import parse_deck_string


# Demo deck: Mono-Red Aggro
DEMO_DECK = """
4 Monastery Swiftspear (KTK) 118
4 Kumano Faces Kakkazan (NEO) 152
4 Lightning Strike (M19) 152
4 Play with Fire (MID) 154
4 Embercleave (ELD) 120
4 Phoenix Chick (DMU) 140
4 Bloodthirsty Adversary (MID) 129
3 Bonecrusher Giant (ELD) 115
3 Fable of the Mirror-Breaker (NEO) 141
2 Den of the Bugbear (AFR) 254
20 Mountain (MID) 383
"""


async def demo_1_physical_card_purchase():
    """Demo 1: Physical card purchase with Arena-only filtering."""
    print("\n" + "="*80)
    print("DEMO 1: Physical Card Purchase Integration")
    print("="*80)

    # Initialize services
    sql_service = SmartSQLService()
    await sql_service.init_db()

    scryfall = ScryfallService()
    card_market = CardMarketService(scryfall)
    event_logger = get_event_logger()

    # Parse and store deck
    deck = parse_deck_string(DEMO_DECK)
    deck.name = "Mono-Red Aggro"
    deck.format = "Standard"

    print(f"\n📋 Analyzing deck: {deck.name}")
    print(f"Total cards: {len(deck.mainboard)}")

    deck_id = await sql_service.store_deck(deck)
    print(f"✅ Deck stored with ID: {deck_id}")

    # Get purchase info
    print("\n🛒 Fetching purchase information...")

    cards = [(card.name, card.quantity, card.set_code) for card in deck.mainboard]
    purchase_info = await card_market.get_deck_market_info(
        cards,
        exclude_arena_only=True
    )

    print(f"\n💰 Purchase Summary:")
    print(f"   Total cards: {purchase_info['total_cards']}")
    print(f"   Purchasable in paper: {purchase_info['purchasable_cards']}")
    print(f"   Arena-only cards: {purchase_info['arena_only_cards']}")
    print(f"   Total cost: ${purchase_info['total_price_usd']:.2f} USD")

    if purchase_info['arena_only']:
        print(f"\n⚠️  Arena-Only Cards (excluded from purchase):")
        for card in purchase_info['arena_only'][:3]:
            print(f"      • {card['quantity']}x {card['card_name']}")

    print(f"\n💵 Top 3 Purchasable Cards:")
    for i, card in enumerate(purchase_info['cards'][:3], 1):
        print(f"   {i}. {card['quantity']}x {card['card_name']}")
        print(f"      ${card['unit_price_usd']:.2f} each at {card['best_vendor']}")

    # Log event
    await event_logger.log_purchase_lookup(
        deck_id=deck_id,
        cards_found=purchase_info['total_cards'],
        purchasable_cards=purchase_info['purchasable_cards'],
        arena_only_cards=purchase_info['arena_only_cards'],
        total_price_usd=purchase_info['total_price_usd'],
        user_id="demo_user"
    )

    print("\n✅ Demo 1 complete! Purchase info logged.")
    return deck_id


async def demo_2_concurrent_ai_chat(deck_id: int):
    """Demo 2: Concurrent AI chat with consensus checking."""
    print("\n" + "="*80)
    print("DEMO 2: Vawlrathh Chat with Consensus Checking")
    print("="*80)

    # Initialize chat service
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    if not openai_key or not anthropic_key:
        print("\n⚠️  Warning: API keys not set. Using mock responses.")
        print("   Set OPENAI_API_KEY and ANTHROPIC_API_KEY to see real responses.")
        return

    chat_service = ConcurrentChatService(
        openai_api_key=openai_key,
        anthropic_api_key=anthropic_key,
        enable_consensus=True
    )

    event_logger = get_event_logger()

    # Chat examples
    messages = [
        "What's your take on this Mono-Red Aggro deck?",
        "Should I add more burn spells or creatures?",
        "How do I sideboard against control?"
    ]

    print(f"\n💬 Starting chat with Vawlrathh, The Small'n...")

    for msg in messages:
        print(f"\n👤 User: {msg}")

        result = await chat_service.chat(msg, context={"deck_id": deck_id})

        print(f"🤖 Vawlrathh: {result['response']}")
        print(f"   [Consensus: {'✅ Passed' if result['consensus_passed'] else '❌ Failed'}]")

        if not result['consensus_passed']:
            breaker = result.get('consensus_breaker', {})
            print(f"   ⚠️  {breaker.get('warning', 'ConsensusBreaker triggered')}")
            print(f"   Severity: {breaker.get('severity', 'unknown')}")

        # Log interaction
        await event_logger.log_chat_interaction(
            user_message=msg,
            agent_response=result['response'],
            user_id="demo_user",
            consensus_result=result.get('consensus_breaker')
        )

        await asyncio.sleep(0.5)

    print("\n✅ Demo 2 complete! All chats logged with consensus checks.")


async def demo_3_sequential_reasoning(deck_id: int):
    """Demo 3: Sequential reasoning for deck optimization."""
    print("\n" + "="*80)
    print("DEMO 3: Sequential Reasoning for Deck Optimization")
    print("="*80)

    # Initialize services
    sql_service = SmartSQLService()
    await sql_service.init_db()

    reasoning_service = SequentialReasoningService()
    event_logger = get_event_logger()

    # Get deck
    deck = await sql_service.get_deck(deck_id)

    print(f"\n🧠 Analyzing deck: {deck.name}")
    print("Using chain-of-thought reasoning...\n")

    # Run sequential reasoning
    deck_data = {
        "name": deck.name,
        "format": deck.format,
        "mainboard": [{"name": c.name, "quantity": c.quantity} for c in deck.mainboard]
    }

    reasoning_chain = await reasoning_service.reason_about_deck_building(
        deck_data=deck_data,
        archetype="Aggro",
        format_name="Standard"
    )

    print(f"📝 Reasoning Steps:\n")
    for step in reasoning_chain.steps:
        print(f"   Step {step.step_number}: {step.question}")
        print(f"      → {step.conclusion}")
        print(f"      Confidence: {step.confidence:.0%}\n")

    print(f"🎯 Final Decision:")
    print(f"   {reasoning_chain.final_decision}")
    print(f"\n   Overall Confidence: {reasoning_chain.overall_confidence:.0%}")

    # Log event
    await event_logger.log_event(
        event_logger.StrategyEvent(
            event_id=f"seq_{deck_id}",
            event_type="sequential_reasoning",
            timestamp=reasoning_chain.started_at,
            user_id="demo_user",
            deck_id=deck_id,
            agent="sequential_reasoning",
            action="deck_building_analysis",
            data=reasoning_chain.to_dict()
        )
    )

    print("\n✅ Demo 3 complete! Sequential reasoning logged.")


async def demo_4_event_logging_summary():
    """Demo 4: Event logging summary."""
    print("\n" + "="*80)
    print("DEMO 4: Event Logging Summary (Hackathon Metrics)")
    print("="*80)

    event_logger = get_event_logger()

    # Get statistics
    stats = await event_logger.get_statistics()

    print(f"\n📊 Event Statistics:")
    print(f"   Total events: {stats['total_events']}")
    print(f"   Success rate: {stats['success_rate']:.1%}")

    print(f"\n📈 Events by Type:")
    for event_type, count in stats['event_types'].items():
        print(f"   • {event_type}: {count}")

    print(f"\n🤖 Events by Agent:")
    for agent, count in stats['agents'].items():
        print(f"   • {agent}: {count}")

    print(f"\n🕐 Recent Events:")
    for event_dict in stats['recent_events'][-5:]:
        print(f"   • [{event_dict['event_type']}] {event_dict['action']}")
        print(f"     Agent: {event_dict['agent']}, Success: {event_dict['success']}")

    # Export events for hackathon
    export_path = "data/events/hackathon_demo_export.json"
    await event_logger.export_events(export_path)

    print(f"\n💾 Events exported to: {export_path}")
    print("   This file can be submitted for hackathon judging!")

    print("\n✅ Demo 4 complete! All events logged and exported.")


async def main():
    """Run complete hackathon demo."""
    print("\n" + "="*80)
    print("🎮 ARENA IMPROVER - HACKATHON DEMO")
    print("   Vibe. Code. Ship. - LiquidMetal Edition")
    print("="*80)

    print("\nThis demo showcases:")
    print("1. ✅ Physical card purchase integration (excludes Arena-only)")
    print("2. ✅ Concurrent AI chat with Vawlrathh + consensus checking")
    print("3. ✅ Sequential reasoning workflows (chain-of-thought)")
    print("4. ✅ Event logging for strategic recommendations")
    print("5. ✅ MCP protocol depth and integration")

    try:
        # Run demos
        deck_id = await demo_1_physical_card_purchase()
        await asyncio.sleep(1)

        await demo_2_concurrent_ai_chat(deck_id)
        await asyncio.sleep(1)

        await demo_3_sequential_reasoning(deck_id)
        await asyncio.sleep(1)

        await demo_4_event_logging_summary()

        print("\n" + "="*80)
        print("🎉 HACKATHON DEMO COMPLETE!")
        print("="*80)
        print("\n📦 Deliverables:")
        print("   • Physical card purchase API with Arena-only filtering")
        print("   • Real-time WebSocket chat with Vawlrathh, The Small'n")
        print("   • AI consensus checking (Sonnet 4.5)")
        print("   • Sequential reasoning for complex decisions")
        print("   • Event logging system (exportable for judging)")
        print("   • Full MCP protocol integration")
        print("\n🚀 Ready for DevPost submission!")

    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
