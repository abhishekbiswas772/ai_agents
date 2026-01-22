"""
OpenAI-Compatible LLM Provider

Supports:
- OpenAI API (gpt-4, gpt-3.5, etc.)
- OpenRouter (any model via openrouter.ai)
- Azure OpenAI
- Local servers (Ollama, LM Studio, vLLM, etc.)
- Any OpenAI-compatible API
"""

from __future__ import annotations
import asyncio
import json
from typing import Any, AsyncGenerator
import logging

from openai import APIConnectionError, APIError, AsyncOpenAI, RateLimitError

from byom.providers.base import (
    LLMProvider,
    ProviderConfig,
    StreamEvent,
    ThinkingMode,
)
from byom.providers.registry import register_provider

logger = logging.getLogger(__name__)


@register_provider
class OpenAIProvider(LLMProvider):
    """
    OpenAI-compatible provider.
    
    Works with:
    - OpenAI API directly
    - OpenRouter (model routing service)
    - Azure OpenAI
    - Ollama (local)
    - LM Studio (local)
    - Any OpenAI-compatible API
    """
    
    name = "openai"
    display_name = "OpenAI Compatible"
    
    # Model patterns for auto-detection
    model_patterns = [
        r"^gpt-.*",                    # OpenAI GPT models
        r"^o1-.*",                     # OpenAI o1 models
        r"^text-.*",                   # OpenAI text models
        r"^davinci.*",                 # Legacy models
        r".*/.*",                      # OpenRouter format (provider/model)
        r"^mistral.*",                 # Mistral models  
        r"^mixtral.*",                 # Mixtral models
        r"^llama.*",                   # Llama models
        r"^codellama.*",               # CodeLlama
        r"^deepseek.*",                # DeepSeek models
        r"^qwen.*",                    # Qwen models
        r"^phi-.*",                    # Microsoft Phi
        r"^gemma.*",                   # Google Gemma
    ]
    
    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        self._client: AsyncOpenAI | None = None
    
    def _get_client(self) -> AsyncOpenAI:
        """Get or create the OpenAI client."""
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                organization=self.config.organization,
                timeout=self.config.timeout,
                max_retries=0,  # We handle retries ourselves
            )
        return self._client
    
    async def close(self) -> None:
        """Close the OpenAI client."""
        if self._client:
            await self._client.close()
            self._client = None
    
    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        model: str,
        tools: list[dict[str, Any]] | None = None,
        stream: bool = True,
        temperature: float = 1.0,
        max_tokens: int | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Send a chat completion request.
        
        Yields StreamEvent objects for text chunks, tool calls, and completion.
        """
        self._reset_thinking_state()
        client = self._get_client()
        
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "temperature": temperature,
        }
        
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        
        if tools:
            kwargs["tools"] = self.build_tool_schema(tools)
            kwargs["tool_choice"] = "auto"
        
        # Add stream options for usage tracking
        if stream:
            kwargs["stream_options"] = {"include_usage": True}
        
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
                    wait_time = 2 ** attempt
                    logger.warning(f"Rate limited, retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    yield StreamEvent(
                        type="error",
                        error=f"Rate limit exceeded after {self.config.max_retries} retries: {e}",
                    )
                    return
                    
            except APIConnectionError as e:
                if attempt < self.config.max_retries:
                    wait_time = 2 ** attempt
                    logger.warning(f"Connection error, retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    yield StreamEvent(
                        type="error",
                        error=f"Connection error after {self.config.max_retries} retries: {e}",
                    )
                    return
                    
            except APIError as e:
                yield StreamEvent(
                    type="error",
                    error=f"API error: {e}",
                )
                return
    
    async def _stream_response(
        self,
        client: AsyncOpenAI,
        kwargs: dict[str, Any],
    ) -> AsyncGenerator[StreamEvent, None]:
        """Handle streaming response."""
        response = await client.chat.completions.create(**kwargs)
        
        finish_reason: str | None = None
        usage: dict[str, int] | None = None
        tool_calls: dict[int, dict[str, Any]] = {}
        
        async for chunk in response:
            # Handle usage in final chunk
            if hasattr(chunk, "usage") and chunk.usage:
                usage = {
                    "prompt_tokens": chunk.usage.prompt_tokens,
                    "completion_tokens": chunk.usage.completion_tokens,
                    "total_tokens": chunk.usage.total_tokens,
                }
                if hasattr(chunk.usage, "prompt_tokens_details"):
                    details = chunk.usage.prompt_tokens_details
                    if details and hasattr(details, "cached_tokens"):
                        usage["cached_tokens"] = details.cached_tokens
            
            if not chunk.choices:
                continue
            
            choice = chunk.choices[0]
            delta = choice.delta
            
            if choice.finish_reason:
                finish_reason = choice.finish_reason
            
            # Handle text content
            if delta.content:
                content, thinking = self._process_thinking(delta.content)
                
                if thinking:
                    yield StreamEvent(
                        type="thinking",
                        thinking=thinking,
                    )
                
                if content:
                    yield StreamEvent(
                        type="text",
                        content=content,
                    )
            
            # Handle tool calls
            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    
                    if idx not in tool_calls:
                        tool_calls[idx] = {
                            "id": tc_delta.id or "",
                            "name": "",
                            "arguments": "",
                        }
                        
                        if tc_delta.function and tc_delta.function.name:
                            tool_calls[idx]["name"] = tc_delta.function.name
                            yield StreamEvent(
                                type="tool_call_start",
                                tool_call_id=tool_calls[idx]["id"],
                                tool_name=tc_delta.function.name,
                            )
                    
                    if tc_delta.function and tc_delta.function.arguments:
                        tool_calls[idx]["arguments"] += tc_delta.function.arguments
        
        # Emit completed tool calls
        for idx, tc in tool_calls.items():
            try:
                args = json.loads(tc["arguments"]) if tc["arguments"] else {}
            except json.JSONDecodeError:
                args = {"_raw": tc["arguments"]}
            
            yield StreamEvent(
                type="tool_call",
                tool_call_id=tc["id"],
                tool_name=tc["name"],
                tool_arguments=args,
            )
        
        # Emit completion event
        yield StreamEvent(
            type="done",
            finish_reason=finish_reason,
            usage=usage,
        )
    
    async def _non_stream_response(
        self,
        client: AsyncOpenAI,
        kwargs: dict[str, Any],
    ) -> StreamEvent:
        """Handle non-streaming response."""
        kwargs["stream"] = False
        kwargs.pop("stream_options", None)
        
        response = await client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        message = choice.message
        
        # Build combined event
        content = None
        thinking = None
        tool_calls_data = None
        
        if message.content:
            content, thinking = self._process_thinking(message.content)
        
        if message.tool_calls:
            tool_calls_data = []
            for tc in message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except json.JSONDecodeError:
                    args = {"_raw": tc.function.arguments}
                
                tool_calls_data.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": args,
                })
        
        usage = None
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        
        return StreamEvent(
            type="done",
            content=content,
            thinking=thinking,
            finish_reason=choice.finish_reason,
            usage=usage,
        )
