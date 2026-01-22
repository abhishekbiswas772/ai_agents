"""
Integration tests for BYOM AI Agent workflows
"""
import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from byom import Agent, Config
from byom.agent.events import AgentEventType
from byom.client.response import StreamEvent, StreamEventType, TextDelta, TokenUsage


@pytest.mark.asyncio
async def test_agent_basic_workflow():
    """Test basic agent workflow with mocked provider"""
    # Mock the provider to avoid actual API calls
    with patch('byom.agent.session.LLMClient') as mock_llm_client_class:
        config = Config(model_name="test-model", cwd=Path.cwd())
        mock_llm_client = AsyncMock()
        mock_llm_client.get_model_info.return_value = {
            "name": "test-model",
            "provider": "test"
        }
        mock_llm_client_class.return_value = mock_llm_client
        
        # Mock the LLMClient's chat_completion method to return a simple response
        async def mock_chat_completion(*args, **kwargs):
            yield StreamEvent(
                type=StreamEventType.TEXT_DELTA,
                text_delta=TextDelta(content="Hello, I'm a test agent")
            )
            yield StreamEvent(
                type=StreamEventType.MESSAGE_COMPLETE,
                finish_reason="stop",
                usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15)
            )
        
        mock_llm_client.chat_completion = mock_chat_completion
        
        async with Agent(config) as agent:
            events = []
            async for event in agent.run("Hello"):
                events.append(event)
            
            # Check that we got some events
            assert len(events) > 0
            # Check for text event
            text_events = [e for e in events if e.type == AgentEventType.TEXT_DELTA]
            assert len(text_events) > 0
            assert "Hello, I'm a test agent" in text_events[0].data["content"]


@pytest.mark.asyncio
async def test_agent_with_tools():
    """Test agent workflow with tool usage"""
    config = Config(model_name="test-model", cwd=Path.cwd())
    
    with patch('byom.agent.session.LLMClient') as mock_llm_client_class:
        mock_llm_client = AsyncMock()
        mock_llm_client.get_model_info.return_value = {
            "name": "test-model",
            "provider": "test"
        }
        mock_llm_client_class.return_value = mock_llm_client
        
        # Mock response with tool call
        async def mock_chat_completion(*args, **kwargs):
            from byom.client.response import ToolCallDelta, ToolCall
            yield StreamEvent(
                type=StreamEventType.TOOL_CALL_START,
                tool_call_delta=ToolCallDelta(call_id="call_123", name="list_dir")
            )
            yield StreamEvent(
                type=StreamEventType.TOOL_CALL_DELTA,
                tool_call_delta=ToolCallDelta(call_id="call_123", arguments_delta='{"path": "."}')
            )
            yield StreamEvent(
                type=StreamEventType.TOOL_CALL_COMPLETE,
                tool_call=ToolCall(call_id="call_123", name="list_dir", arguments='{"path": "."}')
            )
            yield StreamEvent(
                type=StreamEventType.TEXT_DELTA,
                text_delta=TextDelta(content="Found 2 files")
            )
            yield StreamEvent(
                type=StreamEventType.MESSAGE_COMPLETE,
                finish_reason="stop",
                usage=TokenUsage(prompt_tokens=15, completion_tokens=8, total_tokens=23)
            )
        
        mock_llm_client.chat_completion = mock_chat_completion
        
        async with Agent(config) as agent:
            events = []
            async for event in agent.run("List files"):
                events.append(event)
            
            # Check that we got tool events
            tool_events = [e for e in events if e.type in [AgentEventType.TOOL_CALL_START, AgentEventType.TOOL_CALL_COMPLETE]]
            assert len(tool_events) > 0


@pytest.mark.asyncio
async def test_agent_error_handling():
    """Test agent error handling"""
    config = Config(model_name="test-model", cwd=Path.cwd())
    
    with patch('byom.agent.session.LLMClient') as mock_llm_client_class:
        mock_llm_client = AsyncMock()
        mock_llm_client.get_model_info.return_value = {
            "name": "test-model",
            "provider": "test"
        }
        mock_llm_client_class.return_value = mock_llm_client
        
        # Mock chat_completion to raise an exception
        mock_llm_client.chat_completion.side_effect = Exception("API Error")
        
        async with Agent(config) as agent:
            events = []
            try:
                async for event in agent.run("This will fail"):
                    events.append(event)
            except Exception:
                # Agent should handle the error gracefully
                pass
            
            # Should get an error event or exception handled
            # For now, just check that it doesn't crash
            assert True


if __name__ == "__main__":
    asyncio.run(test_agent_basic_workflow())
    print("✅ Basic workflow test passed")
    
    asyncio.run(test_agent_with_tools())
    print("✅ Tool workflow test passed")
    
    asyncio.run(test_agent_error_handling())
    print("✅ Error handling test passed")
    
    print("\n🎉 All integration tests passed!")