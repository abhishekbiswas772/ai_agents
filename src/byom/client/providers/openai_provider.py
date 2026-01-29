"""
OpenAI provider implementation for BYOM.

Supports GPT-4, GPT-4 Turbo, and other OpenAI models through their native API
or via OpenAI-compatible servers.
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator

from openai import APIConnectionError, APIError, AsyncOpenAI, RateLimitError

from byom.client.provider_base import LLMProvider, ProviderConfig, ProviderType
from byom.client.response import StreamEvent, StreamEventType, TextDelta, TokenUsage, ToolCall
from byom.tools.tool_call_parser import parse_json_safe


class OpenAIProvider(LLMProvider):
    """OpenAI API provider implementation."""

    def __init__(self, config: ProviderConfig) -> None:
        """Initialize OpenAI provider."""
        super().__init__(config)
        assert config.provider_type == ProviderType.OPENAI
        self._client: AsyncOpenAI | None = None

    async def initialize(self) -> None:
        """Initialize the OpenAI client."""
        if self._client is None:
            kwargs: dict[str, Any] = {
                "api_key": self.config.api_key or "",
            }
            if self.config.base_url:
                kwargs["base_url"] = self.config.base_url
            if self.config.timeout:
                kwargs["timeout"] = self.config.timeout
            if self.config.max_retries:
                kwargs["max_retries"] = self.config.max_retries

            self._client = AsyncOpenAI(**kwargs)

    async def close(self) -> None:
        """Close the OpenAI client."""
        if self._client:
            await self._client.close()
            self._client = None

    def _get_client(self) -> AsyncOpenAI:
        """Get or initialize the client."""
        if self._client is None:
            raise RuntimeError(
                "Provider not initialized. Call await provider.initialize() first."
            )
        return self._client

    def format_tool_schema(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Format tools for OpenAI's function calling format.

        Returns:
            List of tool definitions in OpenAI format
        """
        formatted = []
        for tool in tools:
            formatted.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.get("name", ""),
                        "description": tool.get("description", ""),
                        "parameters": tool.get(
                            "parameters",
                            {"type": "object", "properties": {}},
                        ),
                    },
                }
            )
        return formatted

    async def handle_provider_error(self, error: Exception) -> bool:
        """Handle OpenAI-specific errors and determine if retry should occur."""
        if isinstance(error, RateLimitError):
            await asyncio.sleep(2)
            return True
        elif isinstance(error, APIConnectionError):
            await asyncio.sleep(1)
            return True
        elif isinstance(error, APIError):
            # Some API errors are retryable, others are not
            error_msg = str(error).lower()
            if "timeout" in error_msg or "connection" in error_msg:
                return True
        return False

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        stream: bool = True,
    ) -> AsyncGenerator[StreamEvent, None]:
        """Send a chat completion request to OpenAI."""
        await self.initialize()
        client = self._get_client()

        # Build request kwargs
        kwargs: dict[str, Any] = {
            "model": self.config.model_name,
            "messages": messages,
            "stream": stream,
            "temperature": self.config.temperature,
        }

        if self.config.max_tokens:
            kwargs["max_tokens"] = self.config.max_tokens

        if tools:
            kwargs["tools"] = self.format_tool_schema(tools)
            kwargs["tool_choice"] = "auto"

        # Add provider-specific options
        if self.config.provider_options:
            for key, value in self.config.provider_options.items():
                if key not in kwargs:
                    kwargs[key] = value

        # Retry loop
        for attempt in range(self.config.max_retries + 1):
            try:
                if stream:
                    async for event in self._stream_response(client, kwargs):
                        yield event
                else:
                    event = await self._non_stream_response(client, kwargs)
                    yield event
                return
            except (RateLimitError, APIConnectionError, APIError) as e:
                should_retry = await self.handle_provider_error(e)
                if should_retry and attempt < self.config.max_retries:
                    continue
                else:
                    yield StreamEvent(
                        type=StreamEventType.ERROR,
                        error=f"OpenAI API error (attempt {attempt + 1}): {str(e)}",
                    )
                    return

    async def _stream_response(
        self,
        client: AsyncOpenAI,
        kwargs: dict[str, Any],
    ) -> AsyncGenerator[StreamEvent, None]:
        """Handle streaming response from OpenAI."""
        response = await client.chat.completions.create(**kwargs)

        finish_reason: str | None = None
        usage: TokenUsage | None = None
        tool_calls: dict[int, dict[str, Any]] = {}

        async for chunk in response:
            # Extract usage if available
            if hasattr(chunk, "usage") and chunk.usage:
                usage = TokenUsage(
                    prompt_tokens=chunk.usage.prompt_tokens,
                    completion_tokens=chunk.usage.completion_tokens,
                    total_tokens=chunk.usage.total_tokens,
                    cached_tokens=(
                        chunk.usage.prompt_tokens_details.cached_tokens
                        if hasattr(chunk.usage, "prompt_tokens_details")
                        else 0
                    ),
                )

            if not chunk.choices:
                continue

            choice = chunk.choices[0]
            delta = choice.delta

            # Track finish reason
            if choice.finish_reason:
                finish_reason = choice.finish_reason

            # Handle text content
            if delta.content:
                yield StreamEvent(
                    type=StreamEventType.TEXT_DELTA,
                    text_delta=TextDelta(delta.content),
                )

            # Handle tool calls
            if delta.tool_calls:
                for tool_call_delta in delta.tool_calls:
                    idx = tool_call_delta.index

                    # Initialize tool call if needed
                    if idx not in tool_calls:
                        tool_calls[idx] = {
                            "id": tool_call_delta.id or "",
                            "name": "",
                            "arguments": "",
                        }

                        # Emit tool call start event
                        if tool_call_delta.function and tool_call_delta.function.name:
                            tool_calls[idx]["name"] = tool_call_delta.function.name
                            yield StreamEvent(
                                type=StreamEventType.TOOL_CALL_START,
                                tool_call_delta=self._make_tool_call_delta(
                                    tool_calls[idx]["id"],
                                    tool_call_delta.function.name,
                                ),
                            )

                    # Accumulate arguments
                    if (
                        tool_call_delta.function
                        and tool_call_delta.function.arguments
                    ):
                        tool_calls[idx]["arguments"] += (
                            tool_call_delta.function.arguments
                        )

                        # Emit delta event
                        yield StreamEvent(
                            type=StreamEventType.TOOL_CALL_DELTA,
                            tool_call_delta=self._make_tool_call_delta(
                                tool_calls[idx]["id"],
                                tool_calls[idx]["name"],
                                tool_call_delta.function.arguments,
                            ),
                        )

        # Emit completed tool calls
        for idx, tc in tool_calls.items():
            parsed_args = parse_json_safe(tc["arguments"])
            yield StreamEvent(
                type=StreamEventType.TOOL_CALL_COMPLETE,
                tool_call=ToolCall(
                    call_id=tc["id"],
                    name=tc["name"],
                    arguments=parsed_args,
                ),
            )

        # Emit final completion event
        yield StreamEvent(
            type=StreamEventType.MESSAGE_COMPLETE,
            finish_reason=finish_reason,
            usage=usage,
        )

    async def _non_stream_response(
        self,
        client: AsyncOpenAI,
        kwargs: dict[str, Any],
    ) -> StreamEvent:
        """Handle non-streaming response from OpenAI."""
        response = await client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        message = choice.message

        # Extract text content
        text_delta = None
        if message.content:
            text_delta = TextDelta(content=message.content)

        # Extract tool calls
        tool_calls: list[ToolCall] = []
        if message.tool_calls:
            for tc in message.tool_calls:
                parsed_args = parse_json_safe(tc.function.arguments or "")
                tool_calls.append(
                    ToolCall(
                        call_id=tc.id,
                        name=tc.function.name,
                        arguments=parsed_args,
                    )
                )

        # Extract usage
        usage = None
        if response.usage:
            usage = TokenUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                cached_tokens=(
                    response.usage.prompt_tokens_details.cached_tokens
                    if hasattr(response.usage, "prompt_tokens_details")
                    else 0
                ),
            )

        return StreamEvent(
            type=StreamEventType.MESSAGE_COMPLETE,
            text_delta=text_delta,
            finish_reason=choice.finish_reason,
            usage=usage,
        )

    @staticmethod
    def _make_tool_call_delta(call_id: str, name: str | None = None, args_delta: str | None = None):
        """Helper to create tool call delta events."""
        from byom.client.response import ToolCallDelta
        return ToolCallDelta(
            call_id=call_id,
            name=name,
            arguments_delta=args_delta or "",
        )

    @property
    def supports_streaming(self) -> bool:
        """OpenAI supports streaming."""
        return True

    @property
    def max_context_length(self) -> int:
        """Return max context length based on model."""
        model = self.config.model_name.lower()
        if "gpt-4-turbo" in model or "gpt-4-1106" in model:
            return 128000
        elif "gpt-4" in model:
            return 8192
        elif "gpt-3.5" in model:
            return 4096
        return 128000
