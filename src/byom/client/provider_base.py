"""
Abstract base class and interfaces for LLM provider implementations.

This module defines the unified interface that all LLM providers must implement,
allowing seamless switching between OpenAI, Anthropic, Google, and local providers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, AsyncGenerator

from byom.client.response import StreamEvent
from byom.config.config import Config


class ProviderType(str, Enum):
    """Supported LLM provider types."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    LOCAL = "local"  # Ollama, LM Studio, vLLM, etc.


@dataclass
class ProviderConfig:
    """Configuration for a provider."""

    provider_type: ProviderType
    model_name: str
    api_key: str | None = None
    base_url: str | None = None
    temperature: float = 0.7
    max_tokens: int | None = None
    timeout: float = 60.0
    max_retries: int = 3
    extra_headers: dict[str, str] | None = None
    provider_options: dict[str, Any] | None = None  # Provider-specific options


class LLMProvider(ABC):
    """Abstract base class for LLM provider implementations."""

    def __init__(self, config: ProviderConfig) -> None:
        """Initialize the provider with configuration."""
        self.config = config
        self._client: Any = None

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the provider client (if needed)."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close and cleanup the provider client."""
        pass

    @abstractmethod
    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        stream: bool = True,
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Send a chat completion request to the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: Optional list of tool/function definitions
            stream: Whether to stream the response

        Yields:
            StreamEvent instances for each chunk/event
        """
        pass

    @abstractmethod
    def format_tool_schema(self, tools: list[dict[str, Any]]) -> Any:
        """
        Format tool schemas for this provider's API.

        Different providers have different tool/function calling formats:
        - OpenAI: {"type": "function", "function": {...}}
        - Anthropic: {"name": ..., "description": ..., "input_schema": {...}}
        - Google: Different format for function definitions
        """
        pass

    @abstractmethod
    async def handle_provider_error(self, error: Exception) -> bool:
        """
        Handle provider-specific errors.

        Returns True if the error was handled and should be retried,
        False if it's a fatal error.
        """
        pass

    @property
    def supports_native_tools(self) -> bool:
        """Whether this provider supports native tool calling."""
        return True

    @property
    def supports_streaming(self) -> bool:
        """Whether this provider supports streaming responses."""
        return True

    @property
    def max_context_length(self) -> int:
        """Maximum context window length for this provider."""
        return 128000  # Default, should be overridden by subclasses
