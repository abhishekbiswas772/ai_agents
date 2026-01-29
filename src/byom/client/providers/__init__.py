"""LLM provider implementations."""

from byom.client.provider_base import LLMProvider, ProviderConfig, ProviderType
from byom.client.providers.openai_provider import OpenAIProvider

__all__ = [
    "LLMProvider",
    "ProviderConfig",
    "ProviderType",
    "OpenAIProvider",
]


def create_provider(config: ProviderConfig) -> LLMProvider:
    """Factory function to create LLM provider instances."""
    if config.provider_type == ProviderType.OPENAI:
        return OpenAIProvider(config)
    else:
        raise ValueError(f"Unsupported provider type: {config.provider_type}")
