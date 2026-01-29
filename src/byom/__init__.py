"""
BYOM AI Agents - Bring Your Own Model AI Coding Agent

A terminal-based AI coding assistant that works with any LLM provider.
"""

__version__ = "0.1.10"
__author__ = "Abhishek"
__package_name__ = "byom-ai-agents"

from byom.agent.agent import Agent
from byom.config.config import Config
from byom.providers import get_provider, register_provider

__all__ = [
    "Agent",
    "Config", 
    "get_provider",
    "register_provider",
    "__version__",
]
