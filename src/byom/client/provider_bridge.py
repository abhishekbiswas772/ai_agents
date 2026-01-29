"""
Provider Bridge Layer

Converts between provider StreamEvents and client response formats.
This provides backward compatibility while migrating to the new provider abstraction.
"""

from __future__ import annotations
from typing import Any, AsyncGenerator
import logging

from byom.client.response import (
    StreamEvent as ClientStreamEvent,
    StreamEventType,
    TextDelta,
    ToolCall as ClientToolCall,
    ToolCallDelta,
    TokenUsage,
)
from byom.providers.base import StreamEvent as ProviderStreamEvent
from byom.tools.tool_call_parser import parse_json_safe

logger = logging.getLogger(__name__)


class ProviderBridge:
    """
    Bridges between provider-agnostic StreamEvents and client response types.

    This allows the agent loop to work with the old client/response.py types
    while providers use the new unified StreamEvent format.
    """

    def __init__(self):
        self._tool_call_buffers: dict[str, dict[str, Any]] = {}
        self._current_text = ""

    async def adapt_stream(
        self,
        provider_stream: AsyncGenerator[ProviderStreamEvent, None],
    ) -> AsyncGenerator[ClientStreamEvent, None]:
        """
        Convert provider StreamEvents to client StreamEvents.

        Args:
            provider_stream: Stream of provider events

        Yields:
            Client-compatible StreamEvent objects
        """
        self._tool_call_buffers = {}
        self._current_text = ""

        async for event in provider_stream:
            # Convert provider event to client event(s)
            async for client_event in self._convert_event(event):
                yield client_event

    async def _convert_event(
        self, event: ProviderStreamEvent
    ) -> AsyncGenerator[ClientStreamEvent, None]:
        """Convert a single provider event to one or more client events."""

        if event.type == "text":
            # Text content delta
            if event.content:
                self._current_text += event.content
                yield ClientStreamEvent(
                    type=StreamEventType.TEXT_DELTA,
                    text_delta=TextDelta(content=event.content),
                )

        elif event.type == "thinking":
            # Thinking content (could be shown separately in UI)
            # For now, we'll just log it
            if event.thinking:
                logger.debug(f"Model thinking: {event.thinking[:100]}...")

        elif event.type == "tool_call_start":
            # Initialize tool call buffer
            if event.tool_call_id and event.tool_name:
                self._tool_call_buffers[event.tool_call_id] = {
                    "id": event.tool_call_id,
                    "name": event.tool_name,
                    "arguments": "",
                }

                # Emit start event
                yield ClientStreamEvent(
                    type=StreamEventType.TOOL_CALL_START,
                    tool_call_delta=ToolCallDelta(
                        call_id=event.tool_call_id,
                        name=event.tool_name,
                    ),
                )

        elif event.type == "tool_call":
            # Complete tool call
            if event.tool_call_id and event.tool_name:
                # Parse arguments if they're a dict (already parsed by provider)
                args = event.tool_arguments or {}

                yield ClientStreamEvent(
                    type=StreamEventType.TOOL_CALL_COMPLETE,
                    tool_call=ClientToolCall(
                        call_id=event.tool_call_id,
                        name=event.tool_name,
                        arguments=args,
                    ),
                )

        elif event.type == "done":
            # Message complete
            usage = None
            if event.usage:
                usage = TokenUsage(
                    prompt_tokens=event.usage.get("prompt_tokens", 0),
                    completion_tokens=event.usage.get("completion_tokens", 0),
                    total_tokens=event.usage.get("total_tokens", 0),
                    cached_tokens=event.usage.get("cached_tokens", 0),
                )

            yield ClientStreamEvent(
                type=StreamEventType.MESSAGE_COMPLETE,
                finish_reason=event.finish_reason,
                usage=usage,
            )

        elif event.type == "error":
            # Error event
            yield ClientStreamEvent(
                type=StreamEventType.ERROR,
                error=event.error,
            )


def create_bridge() -> ProviderBridge:
    """Create a new provider bridge instance."""
    return ProviderBridge()
