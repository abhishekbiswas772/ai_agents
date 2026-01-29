"""Tests for LLM provider implementations."""

import pytest
from byom.providers.base import ProviderConfig
from byom.providers.openai_provider import OpenAIProvider
from byom.providers.registry import get_provider


class TestProviderConfig:
    """Test ProviderConfig dataclass."""

    def test_create_provider_config(self):
        """Test creating a provider config."""
        config = ProviderConfig(
            api_key="sk-test",
            base_url="https://api.openai.com/v1",
            timeout=120.0,
            max_retries=3,
        )

        assert config.api_key == "sk-test"
        assert config.base_url == "https://api.openai.com/v1"
        assert config.timeout == 120.0
        assert config.max_retries == 3

    def test_provider_config_defaults(self):
        """Test default values in ProviderConfig."""
        config = ProviderConfig(api_key="sk-test")

        assert config.api_key == "sk-test"
        assert config.timeout == 120.0
        assert config.max_retries == 3
        assert config.base_url is None


class TestOpenAIProvider:
    """Test OpenAI provider implementation."""

    def test_init_openai_provider(self):
        """Test initializing OpenAI provider."""
        config = ProviderConfig(api_key="sk-test")
        provider = OpenAIProvider(config)

        assert provider.config == config
        assert provider._client is None
        assert provider.name == "openai"
        assert provider.display_name == "OpenAI Compatible"

    def test_format_tool_schema(self):
        """Test tool schema formatting for OpenAI."""
        config = ProviderConfig(api_key="sk-test")
        provider = OpenAIProvider(config)

        tools = [
            {
                "name": "search",
                "description": "Search the web",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"}
                    },
                    "required": ["query"],
                },
            }
        ]

        formatted = provider.build_tool_schema(tools)

        assert len(formatted) == 1
        assert formatted[0]["type"] == "function"
        assert formatted[0]["function"]["name"] == "search"
        assert formatted[0]["function"]["description"] == "Search the web"
        assert "parameters" in formatted[0]["function"]

    def test_supports_model(self):
        """Test model pattern matching."""
        assert OpenAIProvider.supports_model("gpt-4")
        assert OpenAIProvider.supports_model("gpt-3.5-turbo")
        assert OpenAIProvider.supports_model("mistral-7b")
        assert OpenAIProvider.supports_model("anthropic/claude-3-opus")  # OpenRouter format


class TestProviderRegistry:
    """Test provider registry functionality."""

    def test_get_openai_provider(self):
        """Test getting OpenAI provider from registry."""
        config = ProviderConfig(api_key="sk-test")
        provider = get_provider("gpt-4", config)

        assert provider is not None
        assert provider.name == "openai"
        assert isinstance(provider, OpenAIProvider)

    def test_get_anthropic_provider(self):
        """Test getting Anthropic provider from registry."""
        config = ProviderConfig(api_key="sk-test")
        provider = get_provider("claude-3-opus", config)

        assert provider is not None
        assert provider.name == "anthropic"

    def test_explicit_provider_selection(self):
        """Test explicit provider selection."""
        config = ProviderConfig(api_key="sk-test")
        provider = get_provider("unknown-model", config, provider_name="openai")

        assert provider is not None
        assert provider.name == "openai"
