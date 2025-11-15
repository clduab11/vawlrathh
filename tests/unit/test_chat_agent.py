"""Tests for chat agent service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.chat_agent import (
    VawlrathhAgent,
    ConsensusChecker,
    ConcurrentChatService,
    ChatMessage,
    ConsensusResult,
    AgentModel
)


@pytest.fixture
def mock_openai_client():
    """Create mock OpenAI client."""
    client = AsyncMock()
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = "Your deck's terrible. Fix it."
    client.chat.completions.create.return_value = response
    return client


@pytest.fixture
def mock_anthropic_client():
    """Create mock Anthropic client."""
    client = AsyncMock()
    response = MagicMock()
    response.content = [MagicMock()]
    response.content[0].text = "PASS"
    client.messages.create.return_value = response
    return client


@pytest.mark.asyncio
async def test_vawlrathh_agent_chat(mock_openai_client):
    """Test Vawlrathh agent chat."""
    agent = VawlrathhAgent(model=AgentModel.GPT4_TURBO, openai_api_key="test")
    agent.client = mock_openai_client

    # Chat
    result = await agent.chat("What do you think of my deck?")

    # Assert
    assert isinstance(result, ChatMessage)
    assert result.role == "assistant"
    assert result.agent == "vawlrathh"
    assert "terrible" in result.content.lower()
    assert len(agent.conversation_history) == 2  # User + assistant message


@pytest.mark.asyncio
async def test_vawlrathh_agent_with_context(mock_openai_client):
    """Test Vawlrathh agent with deck context."""
    agent = VawlrathhAgent(model=AgentModel.GPT4_TURBO, openai_api_key="test")
    agent.client = mock_openai_client

    context = {
        "deck": {"name": "Mono-Red Aggro", "format": "Standard"},
        "analysis": {"overall_score": 75}
    }

    # Chat with context
    result = await agent.chat("Rate my deck", context=context)

    # Assert
    assert result is not None
    mock_openai_client.chat.completions.create.assert_called_once()


def test_vawlrathh_system_prompt():
    """Test Vawlrathh has correct system prompt."""
    agent = VawlrathhAgent()

    assert "Vawlrathh" in agent.SYSTEM_PROMPT
    assert "The Small'n" in agent.SYSTEM_PROMPT
    assert "brusque" in agent.SYSTEM_PROMPT or "direct" in agent.SYSTEM_PROMPT.lower()


@pytest.mark.asyncio
async def test_consensus_checker_pass(mock_anthropic_client):
    """Test consensus checker passing validation."""
    checker = ConsensusChecker(anthropic_api_key="test")
    checker.client = mock_anthropic_client

    result = await checker.check_consensus(
        user_message="What's the best removal spell?",
        agent_response="Lightning Bolt is solid removal."
    )

    # Assert
    assert isinstance(result, ConsensusResult)
    assert result.passed is True
    assert result.primary_response == "Lightning Bolt is solid removal."


@pytest.mark.asyncio
async def test_consensus_checker_fail(mock_anthropic_client):
    """Test consensus checker failing validation."""
    # Setup mock to return FAIL
    response = MagicMock()
    response.content = [MagicMock()]
    response.content[0].text = "FAIL: This advice is incorrect about card legality."
    mock_anthropic_client.messages.create.return_value = response

    checker = ConsensusChecker(anthropic_api_key="test")
    checker.client = mock_anthropic_client

    result = await checker.check_consensus(
        user_message="Is Black Lotus legal in Standard?",
        agent_response="Yes, Black Lotus is legal in Standard."
    )

    # Assert
    assert result.passed is False
    assert result.disagreement_reason is not None
    assert "incorrect" in result.disagreement_reason.lower()
    assert result.severity in ["info", "warning", "critical"]


def test_consensus_severity_determination():
    """Test severity determination logic."""
    checker = ConsensusChecker()

    # Critical keywords
    assert checker._determine_severity("This is incorrect and dangerous") == "critical"

    # Warning keywords
    assert checker._determine_severity("This seems misleading") == "warning"

    # Info
    assert checker._determine_severity("Minor issue here") == "info"


@pytest.mark.asyncio
async def test_concurrent_chat_service(mock_openai_client, mock_anthropic_client):
    """Test concurrent chat service integration."""
    service = ConcurrentChatService(
        openai_api_key="test",
        anthropic_api_key="test",
        enable_consensus=True
    )

    # Mock both clients
    service.vawlrathh.client = mock_openai_client
    service.consensus_checker.client = mock_anthropic_client

    # Chat
    result = await service.chat("Test message")

    # Assert
    assert 'response' in result
    assert 'consensus_checked' in result
    assert result['consensus_checked'] is True
    assert result['consensus_passed'] is True


@pytest.mark.asyncio
async def test_concurrent_chat_service_consensus_breaker(mock_openai_client, mock_anthropic_client):
    """Test concurrent chat service with consensus breaker."""
    # Setup mock to fail consensus
    response = MagicMock()
    response.content = [MagicMock()]
    response.content[0].text = "FAIL: Incorrect advice"
    mock_anthropic_client.messages.create.return_value = response

    service = ConcurrentChatService(
        openai_api_key="test",
        anthropic_api_key="test",
        enable_consensus=True
    )

    service.vawlrathh.client = mock_openai_client
    service.consensus_checker.client = mock_anthropic_client

    # Chat
    result = await service.chat("Test message")

    # Assert
    assert result['consensus_passed'] is False
    assert 'consensus_breaker' in result
    assert 'reason' in result['consensus_breaker']
    assert 'severity' in result['consensus_breaker']


def test_chat_message_dataclass():
    """Test ChatMessage dataclass."""
    msg = ChatMessage(
        role="user",
        content="Test message",
        agent="test_agent"
    )

    assert msg.role == "user"
    assert msg.content == "Test message"
    assert msg.timestamp is not None
    assert msg.consensus_checked is False


def test_clear_history():
    """Test clearing conversation history."""
    agent = VawlrathhAgent()
    agent.conversation_history = [
        ChatMessage(role="user", content="Test 1"),
        ChatMessage(role="assistant", content="Response 1")
    ]

    agent.clear_history()

    assert len(agent.conversation_history) == 0
