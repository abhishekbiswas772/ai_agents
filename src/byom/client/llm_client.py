import asyncio
from typing import Any, AsyncGenerator
import logging

from byom.client.response import (
    StreamEventType,
    StreamEvent,
    TextDelta,
    TokenUsage,
    ToolCall,
    ToolCallDelta,
    parse_tool_call_arguments,
)
from byom.client.provider_bridge import ProviderBridge
from byom.config.config import Config
from byom.providers.base import ProviderConfig, ThinkingMode
from byom.providers.registry import get_provider

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Unified LLM client that works with any provider.

    This class uses the provider abstraction layer to support multiple
    LLM providers (OpenAI, Anthropic, Google, local models) through
    a single unified interface.
    """

    def __init__(self, config: Config) -> None:
        self._provider = None
        self._bridge = ProviderBridge()
        self._max_retries: int = 3
        self.config = config

    def _get_provider(self):
        """Get or create the provider instance."""
        if self._provider is None:
            # Create provider config from main config
            provider_config = ProviderConfig(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                timeout=120.0,
                max_retries=self._max_retries,
                thinking_mode=ThinkingMode(self.config.model.thinking.mode)
                if self.config.model.thinking.enabled
                else ThinkingMode.DISABLED,
                thinking_budget=self.config.model.thinking.budget_tokens,
            )

            # Get provider instance using registry
            self._provider = get_provider(
                model=self.config.model_name,
                config=provider_config,
                provider_name=self.config.model.provider.value
                if self.config.model.provider.value != "auto"
                else None,
            )

            logger.info(
                f"Initialized provider: {self._provider.display_name} "
                f"for model: {self.config.model_name}"
            )

        return self._provider

    async def close(self) -> None:
        """Close the provider connection."""
        if self._provider:
            await self._provider.close()
            self._provider = None

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        stream: bool = True,
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Send a chat completion request using the configured provider.

        This method uses the provider abstraction layer and bridges
        provider events to client events for backward compatibility.

        Args:
            messages: Conversation messages
            tools: Optional tool definitions
            stream: Whether to stream the response

        Yields:
            StreamEvent objects compatible with the agent loop
        """
        provider = self._get_provider()

        # Call provider's chat_completion and bridge the events
        provider_stream = provider.chat_completion(
            messages=messages,
            model=self.config.model_name,
            tools=tools,
            stream=stream,
            temperature=self.config.temperature,
            max_tokens=self.config.model.max_output_tokens,
        )

        # Bridge provider events to client events
        async for event in self._bridge.adapt_stream(provider_stream):
            yield event
