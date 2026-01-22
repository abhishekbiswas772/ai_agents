"""BYOM AI Agents - LLM Providers Package

This package implements the Bring Your Own Model (BYOM) architecture,
allowing users to connect any LLM provider.

Supported providers:
- OpenAI (and OpenAI-compatible APIs like OpenRouter, Azure, Ollama)
- Anthropic (Claude models)
- Google (Gemini models)
"""

from byom.providers.base import LLMProvider, ProviderConfig
from byom.providers.registry import get_provider, register_provider, list_providers

__all__ = [
    "LLMProvider",
    "ProviderConfig",
    "get_provider",
    "register_provider", 
    "list_providers",
]
