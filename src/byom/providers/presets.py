"""
Provider Configuration Presets

Pre-configured settings for popular LLM providers including
Ollama, LM Studio, OpenRouter, and others.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class ProviderPreset:
    """Configuration preset for a provider"""

    name: str
    display_name: str
    provider: str
    base_url: str | None
    default_model: str
    requires_api_key: bool
    api_key_env_var: str | None
    description: str
    example_models: list[str]


# Provider presets
PROVIDER_PRESETS = {
    "openai": ProviderPreset(
        name="openai",
        display_name="OpenAI",
        provider="openai",
        base_url=None,  # Uses default OpenAI URL
        default_model="gpt-4-turbo",
        requires_api_key=True,
        api_key_env_var="OPENAI_API_KEY",
        description="OpenAI's GPT models (GPT-4, GPT-3.5)",
        example_models=["gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"],
    ),
    "anthropic": ProviderPreset(
        name="anthropic",
        display_name="Anthropic",
        provider="anthropic",
        base_url=None,
        default_model="claude-3-5-sonnet-20241022",
        requires_api_key=True,
        api_key_env_var="ANTHROPIC_API_KEY",
        description="Anthropic's Claude models",
        example_models=[
            "claude-3-5-sonnet-20241022",
            "claude-3-opus-20240229",
            "claude-3-haiku-20240307",
        ],
    ),
    "ollama": ProviderPreset(
        name="ollama",
        display_name="Ollama (Local)",
        provider="openai",  # Uses OpenAI-compatible API
        base_url="http://localhost:11434/v1",
        default_model="llama3",
        requires_api_key=False,
        api_key_env_var=None,
        description="Run models locally with Ollama",
        example_models=[
            "llama3",
            "llama3:70b",
            "codellama",
            "mistral",
            "mixtral",
            "deepseek-coder",
            "qwen2.5-coder",
            "phi3",
        ],
    ),
    "lmstudio": ProviderPreset(
        name="lmstudio",
        display_name="LM Studio (Local)",
        provider="openai",  # Uses OpenAI-compatible API
        base_url="http://localhost:1234/v1",
        default_model="local-model",
        requires_api_key=False,
        api_key_env_var=None,
        description="Run models locally with LM Studio",
        example_models=[
            "TheBloke/CodeLlama-13B-Instruct-GGUF",
            "TheBloke/Mistral-7B-Instruct-v0.2-GGUF",
            "local-model",  # Whatever you've loaded
        ],
    ),
    "openrouter": ProviderPreset(
        name="openrouter",
        display_name="OpenRouter",
        provider="openai",  # Uses OpenAI-compatible API
        base_url="https://openrouter.ai/api/v1",
        default_model="anthropic/claude-3.5-sonnet",
        requires_api_key=True,
        api_key_env_var="OPENROUTER_API_KEY",
        description="Access 200+ models through OpenRouter",
        example_models=[
            "anthropic/claude-3.5-sonnet",
            "openai/gpt-4-turbo",
            "google/gemini-pro-1.5",
            "meta-llama/llama-3-70b-instruct",
            "mistralai/mixtral-8x7b-instruct",
            "deepseek/deepseek-coder",
        ],
    ),
    "google": ProviderPreset(
        name="google",
        display_name="Google AI",
        provider="google",
        base_url=None,
        default_model="gemini-pro",
        requires_api_key=True,
        api_key_env_var="GOOGLE_API_KEY",
        description="Google's Gemini models",
        example_models=["gemini-pro", "gemini-1.5-pro", "gemini-1.5-flash"],
    ),
    "azure": ProviderPreset(
        name="azure",
        display_name="Azure OpenAI",
        provider="openai",
        base_url=None,  # User must provide their Azure endpoint
        default_model="gpt-4",
        requires_api_key=True,
        api_key_env_var="AZURE_OPENAI_API_KEY",
        description="Azure OpenAI Service",
        example_models=["gpt-4", "gpt-35-turbo"],
    ),
}


def get_preset(name: str) -> ProviderPreset | None:
    """Get a provider preset by name."""
    return PROVIDER_PRESETS.get(name)


def list_presets() -> list[ProviderPreset]:
    """List all available presets."""
    return list(PROVIDER_PRESETS.values())


def get_config_for_preset(preset_name: str, **overrides: Any) -> dict[str, Any]:
    """
    Get configuration dict for a preset.

    Args:
        preset_name: Name of the preset
        **overrides: Override any preset values

    Returns:
        Configuration dictionary ready for config.toml
    """
    preset = get_preset(preset_name)
    if not preset:
        raise ValueError(f"Unknown preset: {preset_name}")

    config = {
        "model": {
            "name": preset.default_model,
            "provider": preset.provider,
        },
        "api": {},
    }

    if preset.base_url:
        config["api"]["base_url"] = preset.base_url

    if preset.requires_api_key and preset.api_key_env_var:
        config["api"][
            "_comment"
        ] = f"Set {preset.api_key_env_var} environment variable"

    # Apply overrides
    for key, value in overrides.items():
        if "." in key:
            section, field = key.split(".", 1)
            if section not in config:
                config[section] = {}
            config[section][field] = value
        else:
            config[key] = value

    return config
