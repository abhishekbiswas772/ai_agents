"""
BYOM Provider Registry

Manages registration and auto-detection of LLM providers.
Allows dynamic provider selection based on model name or explicit configuration.
"""

from __future__ import annotations
from typing import TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from byom.providers.base import LLMProvider, ProviderConfig

logger = logging.getLogger(__name__)

# Registry of provider classes
_PROVIDERS: dict[str, type["LLMProvider"]] = {}

# Default provider order for auto-detection
_PROVIDER_PRIORITY: list[str] = []


def register_provider(
    provider_class: type["LLMProvider"],
    priority: int | None = None,
) -> type["LLMProvider"]:
    """
    Register an LLM provider.
    
    Can be used as a decorator or called directly:
    
        @register_provider
        class MyProvider(LLMProvider):
            name = "my-provider"
            ...
            
    Args:
        provider_class: The provider class to register
        priority: Optional priority for auto-detection (lower = higher priority)
        
    Returns:
        The registered provider class (for decorator use)
    """
    name = provider_class.name
    
    if name in _PROVIDERS:
        logger.warning(f"Overwriting existing provider: {name}")
    
    _PROVIDERS[name] = provider_class
    
    # Update priority list
    if name not in _PROVIDER_PRIORITY:
        if priority is not None:
            _PROVIDER_PRIORITY.insert(min(priority, len(_PROVIDER_PRIORITY)), name)
        else:
            _PROVIDER_PRIORITY.append(name)
    
    logger.debug(f"Registered provider: {name} ({provider_class.display_name})")
    return provider_class


def get_provider(
    model: str,
    config: "ProviderConfig",
    provider_name: str | None = None,
) -> "LLMProvider":
    """
    Get an LLM provider instance for the given model.
    
    If provider_name is specified, uses that provider directly.
    Otherwise, auto-detects based on model name patterns.
    
    Args:
        model: Model name/identifier
        config: Provider configuration
        provider_name: Optional explicit provider name
        
    Returns:
        Configured LLMProvider instance
        
    Raises:
        ValueError: If no suitable provider found
    """
    # Import providers to trigger registration
    _ensure_providers_loaded()
    
    if provider_name:
        if provider_name not in _PROVIDERS:
            available = ", ".join(_PROVIDERS.keys())
            raise ValueError(
                f"Unknown provider: {provider_name}. Available: {available}"
            )
        return _PROVIDERS[provider_name](config)
    
    # Auto-detect based on model name
    for name in _PROVIDER_PRIORITY:
        provider_class = _PROVIDERS[name]
        if provider_class.supports_model(model):
            logger.info(f"Auto-detected provider '{name}' for model '{model}'")
            return provider_class(config)
    
    # Fall back to first provider (usually OpenAI-compatible)
    if _PROVIDER_PRIORITY:
        fallback = _PROVIDER_PRIORITY[0]
        logger.warning(
            f"No provider matched model '{model}', falling back to '{fallback}'"
        )
        return _PROVIDERS[fallback](config)
    
    raise ValueError(
        f"No providers registered. Install a provider or configure one manually."
    )


def list_providers() -> list[dict[str, str]]:
    """
    List all registered providers.
    
    Returns:
        List of dicts with 'name' and 'display_name' keys
    """
    _ensure_providers_loaded()
    return [
        {"name": name, "display_name": _PROVIDERS[name].display_name}
        for name in _PROVIDER_PRIORITY
    ]


def _ensure_providers_loaded() -> None:
    """Ensure all built-in providers are imported and registered."""
    if _PROVIDERS:
        return
    
    # Import built-in providers to trigger registration
    try:
        from byom.providers import openai_provider  # noqa: F401
    except ImportError:
        pass
    
    try:
        from byom.providers import anthropic_provider  # noqa: F401
    except ImportError:
        pass
    
    try:
        from byom.providers import google_provider  # noqa: F401
    except ImportError:
        pass
