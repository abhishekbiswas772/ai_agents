from pathlib import Path
import sys
from agents.agents import Agent
import asyncio
import click
from agents.events import AgentEventType
from ui.tui import TUI, get_console

console = get_console()

class CLI:
    def __init__(self):
        self.agent: Agent | None = None
        self.tui = TUI(console=console)

    async def run_single(self, message: str) -> str | None:
        async with Agent() as agent:
            self.agent = agent
            return await self._process_message(message)
        
    async def run_interactive(self) -> str | None:
        self.tui.print_welcome(
            title="AI Agents", 
            lines=[
                f"qwen/qwen3-1.7b",
                f"cwd: {Path.cwd()}",
                'commands: /help, /config, /approval, /model, /exit'
            ]
        )
        async with Agent() as agent:
            self.agent = agent
            while True:
                try:
                    user_input = console.input("\n[user]>[/user] ").strip()
                    if not user_input:
                        continue

                    # Check for exit command
                    if user_input.lower() in ['/exit', '/quit']:
                        break

                    await self._process_message(user_input)
                except KeyboardInterrupt:
                    console.print("\n[dim] user /exit to quit[/dim]")
                except EOFError:
                    break
        console.print("\n[dim]Goodbye![/dim]")
        
    def _get_tool_kind(self, tool_name : str) -> str | None:
        tool = self.agent.tool_registry.get(tool_name)
        if not tool:
            return None
        return tool.kind.value.lower()

    async def _process_message(self, message: str) -> str | None:
        if not self.agent:
            return None
        assistance_streaming = False
        final_response: str | None = None
        async for event in self.agent.run(message=message):
            # print(event)  # Uncomment for debugging
            if event.type == AgentEventType.TEXT_DELTA:
                content = event.data.get("content", "")
                if not assistance_streaming:
                    self.tui.begin_assistance()
                    assistance_streaming = True
                self.tui.stream_assistant_delta(content=content)
            elif event.type == AgentEventType.TEXT_COMPLETE:
                final_response = event.data.get("content")
                if assistance_streaming:
                    self.tui.end_assistance()
                    assistance_streaming = False
            elif event.type == AgentEventType.TOOL_CALL_START:
                call_id = event.data.get("call_id", "")
                tool_name = event.data.get("name", "unknown")
                arguments = event.data.get("arguments", {})
                tool_kind = self._get_tool_kind(tool_name)
                self.tui.tool_call_start(call_id, tool_name, tool_kind, arguments)
            elif event.type == AgentEventType.TOOL_CALL_COMPLETE:
                call_id = event.data.get("call_id", "")
                tool_name = event.data.get("name", "")
                tool_kind = self._get_tool_kind(tool_name)
                arguments = event.data.get("arguments", {})
                success = event.data.get("success", False)
                self.tui.tool_call_complete(
                    call_id,
                    tool_name,
                    tool_kind,
                    success,
                    event.data.get("output", ""),
                    event.data.get("error", ""),
                    event.data.get("metadata", {}),
                    event.data.get("truncated", False),
                )
            elif event.type == AgentEventType.AGENT_ERROR:
                error = event.data.get("error", "unknown error")
                console.print(f"\n[error]Error: {error}[/error]")


        return final_response



@click.command()
@click.argument("prompt", required=False)
def main(prompt : str | None):
    cli = CLI()
    if prompt:
        result = asyncio.run(cli.run_single(prompt))
        if result is None:
            sys.exit(1)
    else:
        asyncio.run(cli.run_interactive())
    

if __name__ == "__main__":
    main()

    