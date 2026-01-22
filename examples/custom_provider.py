"""
Custom Provider Example - BYOM AI Agents

This example shows how to use BYOM with different LLM providers.
"""

import asyncio
from pathlib import Path
import os
from byom import Agent
from byom.config.config import Config


async def openai_example():
    """Example using OpenAI"""
    config = Config(
        model_name="gpt-4-turbo",
        cwd=Path.cwd(),
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    async with Agent(config) as agent:
        async for event in agent.run("What is 2+2?"):
            pass  # Process events


async def anthropic_example():
    """Example using Anthropic Claude"""
    config = Config(
        model_name="claude-3-5-sonnet-20241022",
        cwd=Path.cwd(),
        api_key=os.getenv("ANTHROPIC_API_KEY"),
    )

    async with Agent(config) as agent:
        async for event in agent.run("What is 2+2?"):
            pass  # Process events


async def ollama_example():
    """Example using local Ollama model"""
    config = Config(
        model_name="llama3",
        cwd=Path.cwd(),
        api_base_url="http://localhost:11434/v1",
        api_key="not-needed",  # Ollama doesn't need an API key
    )

    async with Agent(config) as agent:
        async for event in agent.run("What is 2+2?"):
            pass  # Process events


if __name__ == "__main__":
    # Run one of the examples
    asyncio.run(openai_example())
    # asyncio.run(anthropic_example())
    # asyncio.run(ollama_example())
