"""Concurrent AI chat agent system with consensus checking."""

import asyncio
import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import anthropic
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class AgentModel(Enum):
    """Available AI models for chat agents."""
    GPT4_TURBO = "gpt-4-turbo-preview"
    GPT4 = "gpt-4"
    HAIKU_4_5 = "claude-3-5-haiku-20241022"
    SONNET_4_5 = "claude-sonnet-4-5-20250929"


@dataclass
class ChatMessage:
    """Chat message with metadata."""
    role: str  # 'user', 'assistant', 'system'
    content: str
    agent: Optional[str] = None
    timestamp: datetime = None
    consensus_checked: bool = False
    consensus_passed: bool = True

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class ConsensusResult:
    """Result of consensus checking."""
    passed: bool
    primary_response: str
    consensus_response: str
    disagreement_reason: Optional[str] = None
    severity: str = "info"  # 'info', 'warning', 'critical'


class VawlrathhAgent:
    """
    Vawlrathh, The Small'n - A dry-witted, brusque MTG strategy assistant.

    Primary chat agent using GPT-4.1 or Claude Haiku 4.5.
    """

    SYSTEM_PROMPT = """You are Vawlrathh, The Small'n - a diminutive but formidable version of Volrath, The Fallen.

Despite your small stature, you possess vast knowledge of Magic: The Gathering strategy. You are:
- Dry-witted and brusque in your responses
- Direct and to-the-point (no flowery language)
- Almost goblin-like in your pragmatic approach
- Knowledgeable about MTG Arena meta, deck building, and competitive play
- True to your Volrath roots: cunning, strategic, and slightly menacing

You assist players with deck analysis, meta insights, and competitive strategy for MTG Arena on Steam.
Keep responses concise. Get to the point. No nonsense.

Example tone:
"Your mana curve's a disaster. Fix it."
"That's... not terrible. Could be worse."
"You call that a sideboard? I've seen better from goblins."
"""

    def __init__(
        self,
        model: AgentModel = AgentModel.GPT4_TURBO,
        openai_api_key: Optional[str] = None,
        anthropic_api_key: Optional[str] = None
    ):
        """
        Initialize Vawlrathh agent.

        Args:
            model: AI model to use
            openai_api_key: OpenAI API key (for GPT models)
            anthropic_api_key: Anthropic API key (for Claude models)
        """
        self.model = model
        self.conversation_history: List[ChatMessage] = []

        if model in [AgentModel.GPT4, AgentModel.GPT4_TURBO]:
            self.client = AsyncOpenAI(api_key=openai_api_key)
            self.provider = "openai"
        else:
            self.client = anthropic.AsyncAnthropic(api_key=anthropic_api_key)
            self.provider = "anthropic"

    async def chat(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ChatMessage:
        """
        Send a message to Vawlrathh and get a response.

        Args:
            user_message: User's message
            context: Optional context (deck data, meta info, etc.)

        Returns:
            ChatMessage with Vawlrathh's response
        """
        # Add user message to history
        user_msg = ChatMessage(role="user", content=user_message, agent="user")
        self.conversation_history.append(user_msg)

        # Build messages for API
        messages = self._build_message_list(context)

        # Get response based on provider
        if self.provider == "openai":
            response_content = await self._chat_openai(messages)
        else:
            response_content = await self._chat_anthropic(messages)

        # Create response message
        response_msg = ChatMessage(
            role="assistant",
            content=response_content,
            agent="vawlrathh"
        )
        self.conversation_history.append(response_msg)

        return response_msg

    def _build_message_list(self, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
        """Build message list for API."""
        messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]

        # Add context if provided
        if context:
            context_str = self._format_context(context)
            messages.append({"role": "system", "content": f"Current context:\n{context_str}"})

        # Add conversation history
        for msg in self.conversation_history[-10:]:  # Last 10 messages
            if msg.role in ["user", "assistant"]:
                messages.append({"role": msg.role, "content": msg.content})

        return messages

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context data for system message."""
        parts = []

        if "deck" in context:
            parts.append(f"Current deck: {context['deck'].get('name', 'Unknown')}")

        if "meta" in context:
            parts.append(f"Meta format: {context['meta'].get('format', 'Unknown')}")

        if "analysis" in context:
            parts.append(f"Deck score: {context['analysis'].get('overall_score', 'N/A')}/100")

        return "\n".join(parts)

    async def _chat_openai(self, messages: List[Dict[str, str]]) -> str:
        """Get response from OpenAI."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model.value,
                messages=messages,
                temperature=0.8,
                max_tokens=500
            )
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"OpenAI chat error: {e}")
            return "Bah. Something broke. Try again."

    async def _chat_anthropic(self, messages: List[Dict[str, str]]) -> str:
        """Get response from Anthropic."""
        try:
            # Separate system message
            system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
            conversation = [m for m in messages if m["role"] != "system"]

            response = await self.client.messages.create(
                model=self.model.value,
                system=system_msg,
                messages=conversation,
                temperature=0.8,
                max_tokens=500
            )
            return response.content[0].text

        except Exception as e:
            logger.error(f"Anthropic chat error: {e}")
            return "Bah. Something broke. Try again."

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []


class ConsensusChecker:
    """
    Consensus checking agent using Claude Sonnet 4.5.

    Validates responses from the primary agent for accuracy and safety.
    """

    SYSTEM_PROMPT = """You are a consensus validation agent for MTG Arena strategy advice.

Your role is to review responses from the primary agent (Vawlrathh) and determine if they contain:
1. Factually incorrect MTG rules or card interactions
2. Dangerous or misleading strategic advice
3. Meta information that contradicts current tournament data
4. Toxic or harmful content

Respond with:
- PASS: if the response is acceptable
- FAIL: if there are significant issues

If FAIL, provide a brief reason (1-2 sentences).
"""

    def __init__(self, anthropic_api_key: Optional[str] = None):
        """Initialize consensus checker."""
        self.client = anthropic.AsyncAnthropic(api_key=anthropic_api_key)

    async def check_consensus(
        self,
        user_message: str,
        agent_response: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ConsensusResult:
        """
        Check if agent response passes consensus validation.

        Args:
            user_message: Original user message
            agent_response: Agent's response to validate
            context: Optional context

        Returns:
            ConsensusResult with validation outcome
        """
        prompt = f"""User asked: "{user_message}"

Agent responded: "{agent_response}"

Validate this response. Is it accurate and safe?
Respond with either:
- PASS (if acceptable)
- FAIL: [reason] (if there are issues)
"""

        if context:
            prompt += f"\nContext: {context}"

        try:
            response = await self.client.messages.create(
                model=AgentModel.SONNET_4_5.value,
                system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200
            )

            consensus_text = response.content[0].text.strip()

            # Parse response
            if consensus_text.startswith("PASS"):
                return ConsensusResult(
                    passed=True,
                    primary_response=agent_response,
                    consensus_response=consensus_text
                )
            elif consensus_text.startswith("FAIL"):
                reason = consensus_text.replace("FAIL:", "").strip()
                severity = self._determine_severity(reason)

                return ConsensusResult(
                    passed=False,
                    primary_response=agent_response,
                    consensus_response=consensus_text,
                    disagreement_reason=reason,
                    severity=severity
                )
            else:
                # Ambiguous response, default to warning
                return ConsensusResult(
                    passed=True,
                    primary_response=agent_response,
                    consensus_response=consensus_text,
                    severity="warning"
                )

        except Exception as e:
            logger.error(f"Consensus check error: {e}")
            # On error, default to passing with warning
            return ConsensusResult(
                passed=True,
                primary_response=agent_response,
                consensus_response="Error checking consensus",
                severity="warning"
            )

    def _determine_severity(self, reason: str) -> str:
        """Determine severity of disagreement."""
        critical_keywords = ["incorrect", "wrong", "dangerous", "harmful", "toxic"]
        warning_keywords = ["misleading", "outdated", "unclear", "questionable"]

        reason_lower = reason.lower()

        if any(kw in reason_lower for kw in critical_keywords):
            return "critical"
        elif any(kw in reason_lower for kw in warning_keywords):
            return "warning"
        else:
            return "info"


class ConcurrentChatService:
    """
    Service managing concurrent chat with Vawlrathh and consensus checking.
    """

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
        enable_consensus: bool = True
    ):
        """
        Initialize concurrent chat service.

        Args:
            openai_api_key: OpenAI API key
            anthropic_api_key: Anthropic API key
            enable_consensus: Enable consensus checking
        """
        self.vawlrathh = VawlrathhAgent(
            model=AgentModel.GPT4_TURBO,
            openai_api_key=openai_api_key,
            anthropic_api_key=anthropic_api_key
        )
        self.consensus_checker = ConsensusChecker(anthropic_api_key=anthropic_api_key)
        self.enable_consensus = enable_consensus

    async def chat(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send message and get response with optional consensus check.

        Args:
            user_message: User's message
            context: Optional context

        Returns:
            Dict with response and consensus info
        """
        # Get response from Vawlrathh
        response_msg = await self.vawlrathh.chat(user_message, context)

        result = {
            "response": response_msg.content,
            "agent": "vawlrathh",
            "timestamp": response_msg.timestamp.isoformat(),
            "consensus_checked": False,
            "consensus_passed": True
        }

        # Run consensus check if enabled
        if self.enable_consensus:
            consensus_result = await self.consensus_checker.check_consensus(
                user_message,
                response_msg.content,
                context
            )

            result["consensus_checked"] = True
            result["consensus_passed"] = consensus_result.passed

            if not consensus_result.passed:
                result["consensus_breaker"] = {
                    "reason": consensus_result.disagreement_reason,
                    "severity": consensus_result.severity,
                    "warning": f"⚠️ ConsensusBreaker: {consensus_result.disagreement_reason}"
                }

        return result

    def clear_history(self):
        """Clear conversation history."""
        self.vawlrathh.clear_history()
