"""
Basic Usage Example - BYOM AI Agents

This example shows how to use BYOM AI Agents programmatically.
"""

import asyncio
from pathlib import Path
from byom import Agent
from byom.config.config import Config
from byom.agent.events import AgentEventType


async def basic_example():
    """Run a simple query with BYOM Agent"""

    # Create configuration
    config = Config(
        model_name="gpt-4-turbo",
        cwd=Path.cwd(),
        temperature=0.7,
    )

    # Create and run agent
    async with Agent(config) as agent:
        print("🤖 Running query...")

        async for event in agent.run("List all Python files in the current directory"):
            if event.type == AgentEventType.TEXT_DELTA:
                # Stream assistant response
                print(event.data.get("content", ""), end="", flush=True)
            elif event.type == AgentEventType.TEXT_COMPLETE:
                print("\n")  # Newline after complete response
            elif event.type == AgentEventType.TOOL_CALL_START:
                tool_name = event.data.get("name")
                print(f"\n🔧 Using tool: {tool_name}")
            elif event.type == AgentEventType.TOOL_CALL_COMPLETE:
                success = event.data.get("success", False)
                status = "✅" if success else "❌"
                print(f"{status} Tool completed")


if __name__ == "__main__":
    asyncio.run(basic_example())
