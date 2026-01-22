"""
BYOM LLM Provider Base Classes

Defines the abstract interface that all LLM providers must implement.
Supports streaming, tool calling, and thinking model output parsing.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator
import re


class ThinkingMode(str, Enum):
    """How to handle thinking/reasoning tokens from the model."""
    DISABLED = "disabled"       # Don't expect or parse thinking tokens
    TAGS = "tags"              # Parse <think>...</think> or <thinking>...</thinking> tags  
    STREAMING = "streaming"    # Model streams thinking as separate content type


@dataclass
class ProviderConfig:
    """Configuration for an LLM provider."""
    api_key: str | None = None
    base_url: str | None = None
    organization: str | None = None
    timeout: float = 120.0
    max_retries: int = 3
    
    # Thinking model support
    thinking_mode: ThinkingMode = ThinkingMode.DISABLED
    thinking_budget: int | None = None  # Max tokens for thinking (Claude extended thinking)
    
    # Additional provider-specific options
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass  
class StreamEvent:
    """Event emitted during streaming response."""
    type: str
    content: str | None = None
    thinking: str | None = None  # Thinking/reasoning content
    tool_call_id: str | None = None
    tool_name: str | None = None
    tool_arguments: dict[str, Any] | None = None
    finish_reason: str | None = None
    usage: dict[str, int] | None = None
    error: str | None = None


class ThinkingParser:
    """Parses thinking tags from model output."""
    
    # Patterns for different thinking tag formats
    THINKING_PATTERNS = [
        (re.compile(r'<think>(.*?)</think>', re.DOTALL), 'think'),
        (re.compile(r'<thinking>(.*?)</thinking>', re.DOTALL), 'thinking'),
        (re.compile(r'<reasoning>(.*?)</reasoning>', re.DOTALL), 'reasoning'),
    ]
    
    @classmethod
    def extract_thinking(cls, text: str) -> tuple[str, str]:
        """
        Extract thinking content from text.
        
        Returns:
            Tuple of (cleaned_text, thinking_content)
        """
        thinking_parts = []
        cleaned = text
        
        for pattern, _ in cls.THINKING_PATTERNS:
            matches = pattern.findall(cleaned)
            thinking_parts.extend(matches)
            cleaned = pattern.sub('', cleaned)
        
        return cleaned.strip(), '\n'.join(thinking_parts)
    
    @classmethod
    def is_thinking_start(cls, text: str) -> bool:
        """Check if text starts a thinking block."""
        return any(
            text.strip().startswith(f'<{tag}>')
            for _, tag in cls.THINKING_PATTERNS
        )
    
    @classmethod
    def is_thinking_end(cls, text: str) -> bool:
        """Check if text ends a thinking block."""
        return any(
            text.strip().endswith(f'</{tag}>')
            for _, tag in cls.THINKING_PATTERNS
        )


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    Implement this class to add support for a new LLM provider.
    The BYOM architecture allows users to bring any model that implements
    this interface.
    """
    
    # Provider identification
    name: str = "base"
    display_name: str = "Base Provider"
    
    # Model patterns this provider supports (regex patterns)
    model_patterns: list[str] = []
    
    def __init__(self, config: ProviderConfig) -> None:
        self.config = config
        self._thinking_buffer = ""
        self._in_thinking_block = False
    
    @classmethod
    def supports_model(cls, model_name: str) -> bool:
        """
        Check if this provider supports the given model name.
        
        Override this for custom matching logic, or set model_patterns
        for simple regex matching.
        """
        for pattern in cls.model_patterns:
            if re.match(pattern, model_name, re.IGNORECASE):
                return True
        return False
    
    @abstractmethod
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
        Send a chat completion request to the provider.
        
        Args:
            messages: List of conversation messages
            model: Model name/identifier
            tools: Optional list of tool definitions
            stream: Whether to stream the response
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Yields:
            StreamEvent objects for each part of the response
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close any open connections."""
        pass
    
    def _process_thinking(self, content: str) -> tuple[str, str | None]:
        """
        Process content for thinking tags based on thinking_mode.
        
        Returns:
            Tuple of (display_content, thinking_content)
        """
        if self.config.thinking_mode == ThinkingMode.DISABLED:
            return content, None
            
        if self.config.thinking_mode == ThinkingMode.TAGS:
            # Check for thinking block boundaries
            if ThinkingParser.is_thinking_start(content):
                self._in_thinking_block = True
                
            if self._in_thinking_block:
                self._thinking_buffer += content
                if ThinkingParser.is_thinking_end(content):
                    self._in_thinking_block = False
                    cleaned, thinking = ThinkingParser.extract_thinking(self._thinking_buffer)
                    self._thinking_buffer = ""
                    return cleaned, thinking
                return "", None  # Still accumulating thinking
            
            # Normal content (not in thinking block)
            cleaned, thinking = ThinkingParser.extract_thinking(content)
            return cleaned, thinking if thinking else None
            
        return content, None
    
    def _reset_thinking_state(self) -> None:
        """Reset thinking parser state between messages."""
        self._thinking_buffer = ""
        self._in_thinking_block = False
    
    def build_tool_schema(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Convert tool definitions to provider-specific format.
        
        Override this method if your provider uses a different tool format.
        Default implementation uses OpenAI-style function calling.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get(
                        "parameters",
                        {"type": "object", "properties": {}},
                    ),
                },
            }
            for tool in tools
        ]
