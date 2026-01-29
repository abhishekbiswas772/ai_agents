"""
Anthropic Claude LLM Provider

Supports:
- Claude 3.5 Sonnet, Opus, Haiku
- Claude 3 models
- Extended thinking (Claude's built-in reasoning)
"""

from __future__ import annotations
import json
from typing import Any, AsyncGenerator
import logging

try:
    from anthropic import AsyncAnthropic, APIError, RateLimitError
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

from byom.providers.base import (
    LLMProvider,
    ProviderConfig,
    StreamEvent,
    ThinkingMode,
)
from byom.providers.registry import register_provider

logger = logging.getLogger(__name__)


if HAS_ANTHROPIC:
    @register_provider
    class AnthropicProvider(LLMProvider):
        """
        Anthropic Claude provider.
        
        Supports Claude 3.5 and Claude 3 model families with native
        tool calling and extended thinking.
        """
        
        name = "anthropic"
        display_name = "Anthropic Claude"
        
        model_patterns = [
            r"^claude-.*",              # All Claude models
            r"^anthropic/claude-.*",    # OpenRouter format
        ]
        
        def __init__(self, config: ProviderConfig) -> None:
            super().__init__(config)
            self._client: AsyncAnthropic | None = None
        
        def _get_client(self) -> AsyncAnthropic:
            """Get or create the Anthropic client."""
            if self._client is None:
                kwargs = {
                    "api_key": self.config.api_key,
                    "timeout": self.config.timeout,
                    "max_retries": 0,
                }
                if self.config.base_url:
                    kwargs["base_url"] = self.config.base_url
                    
                self._client = AsyncAnthropic(**kwargs)
            return self._client
        
        async def close(self) -> None:
            """Close the Anthropic client."""
            if self._client:
                await self._client.close()
                self._client = None
        
        def _convert_messages(
            self, messages: list[dict[str, Any]]
        ) -> tuple[str | None, list[dict[str, Any]]]:
            """
            Convert OpenAI-style messages to Anthropic format.
            
            Returns:
                Tuple of (system_prompt, messages)
            """
            system_prompt = None
            converted = []
            
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                if role == "system":
                    system_prompt = content
                elif role == "assistant":
                    # Handle tool calls in assistant messages
                    if msg.get("tool_calls"):
                        tool_use_blocks = []
                        for tc in msg["tool_calls"]:
                            tool_use_blocks.append({
                                "type": "tool_use",
                                "id": tc["id"],
                                "name": tc["function"]["name"],
                                "input": json.loads(tc["function"]["arguments"])
                                if isinstance(tc["function"]["arguments"], str)
                                else tc["function"]["arguments"],
                            })
                        
                        blocks = []
                        if content:
                            blocks.append({"type": "text", "text": content})
                        blocks.extend(tool_use_blocks)
                        
                        converted.append({"role": "assistant", "content": blocks})
                    else:
                        converted.append({"role": "assistant", "content": content})
                        
                elif role == "tool":
                    # Tool results
                    converted.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": msg.get("tool_call_id", ""),
                            "content": content,
                        }],
                    })
                else:
                    # User messages
                    converted.append({"role": "user", "content": content})
            
            return system_prompt, converted
        
        def build_tool_schema(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
            """Convert to Anthropic tool format."""
            return [
                {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "input_schema": tool.get(
                        "parameters",
                        {"type": "object", "properties": {}},
                    ),
                }
                for tool in tools
            ]
        
        async def chat_completion(
            self,
            messages: list[dict[str, Any]],
            model: str,
            tools: list[dict[str, Any]] | None = None,
            stream: bool = True,
            temperature: float = 1.0,
            max_tokens: int | None = None,
        ) -> AsyncGenerator[StreamEvent, None]:
            """Send a chat completion request to Claude."""
            self._reset_thinking_state()
            client = self._get_client()
            
            # Strip provider prefix if present
            if model.startswith("anthropic/"):
                model = model[len("anthropic/"):]
            
            system_prompt, converted_messages = self._convert_messages(messages)
            
            kwargs: dict[str, Any] = {
                "model": model,
                "messages": converted_messages,
                "max_tokens": max_tokens or 8192,
                "temperature": temperature,
            }
            
            if system_prompt:
                kwargs["system"] = system_prompt
            
            if tools:
                kwargs["tools"] = self.build_tool_schema(tools)
            
            # Extended thinking support
            if self.config.thinking_mode == ThinkingMode.STREAMING:
                if self.config.thinking_budget:
                    kwargs["thinking"] = {
                        "type": "enabled",
                        "budget_tokens": self.config.thinking_budget,
                    }
            
            for attempt in range(self.config.max_retries + 1):
                try:
                    if stream:
                        async for event in self._stream_response(client, kwargs):
                            yield event
                    else:
                        event = await self._non_stream_response(client, kwargs)
                        yield event
                    return

                except RateLimitError as e:
                    if attempt < self.config.max_retries:
                        import asyncio
                        wait_time = 2 ** attempt
                        logger.warning(
                            f"Rate limited (attempt {attempt + 1}/{self.config.max_retries + 1}), "
                            f"retrying in {wait_time}s..."
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        error_msg = (
                            f"Rate limit exceeded after {self.config.max_retries} retries. "
                            f"Provider: {self.display_name}, Model: {model}. "
                            f"Error: {str(e)}"
                        )
                        logger.error(error_msg)
                        yield StreamEvent(type="error", error=error_msg)
                        return

                except APIError as e:
                    error_msg = (
                        f"API error from {self.display_name}. "
                        f"Model: {model}. "
                        f"Error: {str(e)}"
                    )
                    logger.error(error_msg)
                    yield StreamEvent(type="error", error=error_msg)
                    return

                except Exception as e:
                    error_msg = (
                        f"Unexpected error in {self.display_name} provider. "
                        f"Model: {model}. "
                        f"Error: {type(e).__name__}: {str(e)}"
                    )
                    logger.exception(error_msg)
                    yield StreamEvent(type="error", error=error_msg)
                    return
        
        async def _stream_response(
            self,
            client: AsyncAnthropic,
            kwargs: dict[str, Any],
        ) -> AsyncGenerator[StreamEvent, None]:
            """Handle streaming response from Claude."""
            async with client.messages.stream(**kwargs) as stream:
                current_tool_id = None
                current_tool_name = None
                tool_input_buffer = ""
                
                async for event in stream:
                    if event.type == "content_block_start":
                        block = event.content_block
                        if block.type == "thinking":
                            pass  # Will handle in delta
                        elif block.type == "tool_use":
                            current_tool_id = block.id
                            current_tool_name = block.name
                            tool_input_buffer = ""
                            yield StreamEvent(
                                type="tool_call_start",
                                tool_call_id=block.id,
                                tool_name=block.name,
                            )
                    
                    elif event.type == "content_block_delta":
                        delta = event.delta
                        
                        if delta.type == "thinking_delta":
                            yield StreamEvent(
                                type="thinking",
                                thinking=delta.thinking,
                            )
                        elif delta.type == "text_delta":
                            content, thinking = self._process_thinking(delta.text)
                            if thinking:
                                yield StreamEvent(type="thinking", thinking=thinking)
                            if content:
                                yield StreamEvent(type="text", content=content)
                        elif delta.type == "input_json_delta":
                            tool_input_buffer += delta.partial_json
                    
                    elif event.type == "content_block_stop":
                        if current_tool_id:
                            try:
                                args = json.loads(tool_input_buffer) if tool_input_buffer else {}
                            except json.JSONDecodeError:
                                args = {"_raw": tool_input_buffer}
                            
                            yield StreamEvent(
                                type="tool_call",
                                tool_call_id=current_tool_id,
                                tool_name=current_tool_name,
                                tool_arguments=args,
                            )
                            current_tool_id = None
                            current_tool_name = None
                            tool_input_buffer = ""
                    
                    elif event.type == "message_stop":
                        final = await stream.get_final_message()
                        usage = {
                            "prompt_tokens": final.usage.input_tokens,
                            "completion_tokens": final.usage.output_tokens,
                            "total_tokens": final.usage.input_tokens + final.usage.output_tokens,
                        }
                        yield StreamEvent(
                            type="done",
                            finish_reason=final.stop_reason,
                            usage=usage,
                        )
        
        async def _non_stream_response(
            self,
            client: AsyncAnthropic,
            kwargs: dict[str, Any],
        ) -> StreamEvent:
            """Handle non-streaming response."""
            response = await client.messages.create(**kwargs)
            
            content_parts = []
            thinking_parts = []
            tool_calls = []
            
            for block in response.content:
                if block.type == "text":
                    clean, thinking = self._process_thinking(block.text)
                    if clean:
                        content_parts.append(clean)
                    if thinking:
                        thinking_parts.append(thinking)
                elif block.type == "thinking":
                    thinking_parts.append(block.thinking)
                elif block.type == "tool_use":
                    tool_calls.append({
                        "id": block.id,
                        "name": block.name,
                        "arguments": block.input,
                    })
            
            usage = {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            }
            
            return StreamEvent(
                type="done",
                content="\n".join(content_parts) if content_parts else None,
                thinking="\n".join(thinking_parts) if thinking_parts else None,
                finish_reason=response.stop_reason,
                usage=usage,
            )
