"""
BYOM AI Agents - Command Line Interface

Main CLI module with enhanced first-run experience and figlet banner.
"""
import asyncio
from pathlib import Path
import sys
import click
import pyfiglet
from rich.console import Console
from rich.panel import Panel
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style as PromptStyle
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.completion import Completer, Completion, NestedCompleter

from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.filters import completion_is_selected

from byom.utils.file_indexer import FileIndexer, FileCompleter
from byom.commands.registry import CommandRegistry, CommandCompleter
from byom.commands.base import CommandContext
from byom.commands.core import register_default_commands
from byom.ui.constants import MESSAGES, ICONS

from byom import __version__
from byom.agent.agent import Agent
from byom.agent.events import AgentEventType
from byom.agent.persistence import PersistenceManager, SessionSnapshot
from byom.agent.session import Session
from byom.config.config import ApprovalPolicy, Config
from byom.config.loader import load_config, is_first_run
from byom.ui.tui import TUI, get_console
from byom.setup import show_welcome_banner, run_setup_wizard

console = get_console()


class MasterCompleter(Completer):
    """
    Delegates to FileCompleter for '@' and CommandCompleter for '/'.
    """
    def __init__(self, file_completer: FileCompleter, command_completer: CommandCompleter):
        self.file_completer = file_completer
        self.command_completer = command_completer

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if text.startswith('/'):
            yield from self.command_completer.get_completions(document, complete_event)
        else:
            # File completer handles '@' trigger internally
            yield from self.file_completer.get_completions(document, complete_event)

class CLI:
    """Main CLI handler for BYOM AI Agents"""

    def __init__(self, config: Config):
        self.agent: Agent | None = None
        self.config = config
        self.tui = TUI(config, console)
        self.file_indexer = FileIndexer(config.cwd)
        # Ensure index is up to date on startup
        self.file_indexer.scan_workspace()
        self.file_indexer.start_watching()
        
        # Initialize Command Registry
        self.command_registry = CommandRegistry()
        register_default_commands(self.command_registry)

    def _create_key_bindings(self) -> KeyBindings:
        """Create custom key bindings for the session"""
        kb = KeyBindings()

        @kb.add("enter", filter=completion_is_selected)
        def _(event):
            # If a completion is selected, accept it but don't submit the prompt
            event.current_buffer.complete_state = None
        
        return kb

    async def run_interactive(self) -> str | None:
        """Run interactive chat session"""
        self.tui.print_welcome(
            "BYOM AI Agents",
            lines=[
                f"version: {__version__}",
                f"model: {self.config.model_name}",
                f"cwd: {self.config.cwd}",
                "commands: /help /config /approval /model /exit",
            ],
        )

        async with Agent(
            self.config,
            confirmation_callback=self.tui.handle_confirmation,
        ) as agent:
            self.agent = agent

            # Initialize prompt toolkit session
            session = PromptSession(
                completer=MasterCompleter(
                    FileCompleter(self.file_indexer),
                    self.command_registry.get_completer()
                ),
                style=PromptStyle.from_dict({
                    # User Input
                    '': '#ffffff',
                    
                    # Completion menu - shared style
                    'completion-menu': 'bg:#2e3440 #d8dee9',
                    'completion-menu.completion': 'bg:#2e3440 #d8dee9',
                    'completion-menu.completion.current': 'bg:#5e81ac #ffffff bold',
                    'completion-menu.meta.completion': 'bg:#2e3440 #88c0d0',
                    'completion-menu.meta.completion.current': 'bg:#5e81ac #ffffff bold',
                    
                    # Scrollbar
                    'scrollbar.background': 'bg:#2e3440',
                    'scrollbar.button': 'bg:#4c566a',
                    
                    # Bottom toolbar if used
                    'bottom-toolbar': '#444444 bg:#ffffff',
                }),
                key_bindings=self._create_key_bindings(),
            )

            while True:
                try:
                    # Use prompt_toolkit for input
                    user_input = await session.prompt_async(
                        HTML("<b><ansiblue>💬 You ></ansiblue></b> "),
                    )
                    user_input = user_input.strip()

                    if not user_input:
                        continue

                    if user_input.startswith("/"):
                        # Create context for command execution
                        cmd_context = CommandContext(
                            agent=self.agent,
                            config=self.config,
                            tui=self.tui,
                            console=console
                        )
                        should_continue = await self.command_registry.handle_input(cmd_context, user_input)
                        if not should_continue:
                            break
                        continue

                    await self._process_message(user_input)
                except KeyboardInterrupt:
                    console.print(f"\n[dim]{MESSAGES['interrupt_hint']}[/dim]")
                except EOFError:
                    break

            self.file_indexer.stop_watching()
            console.print(f"\n[bright_cyan]{MESSAGES['goodbye']}[/bright_cyan]")

    def _get_tool_kind(self, tool_name: str) -> str | None:
        """Get tool kind for display purposes"""
        tool_kind = None
        tool = self.agent.session.tool_registry.get(tool_name)
        if not tool:
            return None

        tool_kind = tool.kind.value
        return tool_kind

    async def _process_message(self, message: str) -> str | None:
        """Process a user message and handle agent events"""
        if not self.agent:
            return None

        assistant_streaming = False
        final_response: str | None = None

        async for event in self.agent.run(message):
            if event.type == AgentEventType.TEXT_DELTA:
                content = event.data.get("content", "")
                if not assistant_streaming:
                    self.tui.begin_assistant()
                    assistant_streaming = True
                self.tui.stream_assistant_delta(content)
            elif event.type == AgentEventType.TEXT_COMPLETE:
                final_response = event.data.get("content")
                if assistant_streaming:
                    self.tui.end_assistant()
                    assistant_streaming = False
            elif event.type == AgentEventType.AGENT_END:
                # Show token usage if available
                usage_data = event.data.get("usage")
                if usage_data and self.config.ui.show_token_usage:
                    self.tui.show_token_usage(
                        usage_data.get("input_tokens", 0),
                        usage_data.get("output_tokens", 0),
                        usage_data.get("total_tokens", 0),
                    )
            elif event.type == AgentEventType.AGENT_ERROR:
                error = event.data.get("error", "Unknown error")
                console.print(f"\n[error]❌ Error: {error}[/error]")
            elif event.type == AgentEventType.TOOL_CALL_START:
                tool_name = event.data.get("name", "unknown")
                tool_kind = self._get_tool_kind(tool_name)
                self.tui.tool_call_start(
                    event.data.get("call_id", ""),
                    tool_name,
                    tool_kind,
                    event.data.get("arguments", {}),
                )
            elif event.type == AgentEventType.TOOL_CALL_COMPLETE:
                tool_name = event.data.get("name", "unknown")
                tool_kind = self._get_tool_kind(tool_name)
                self.tui.tool_call_complete(
                    event.data.get("call_id", ""),
                    tool_name,
                    tool_kind,
                    event.data.get("success", False),
                    event.data.get("output", ""),
                    event.data.get("error"),
                    event.data.get("metadata"),
                    event.data.get("diff"),
                    event.data.get("truncated", False),
                    event.data.get("exit_code"),
                )

        return final_response




@click.command()
@click.argument("prompt", required=False)
@click.option(
    "--cwd",
    "-c",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Current working directory",
)
@click.option(
    "--version",
    "-v",
    is_flag=True,
    help="Show version and exit",
)
@click.option(
    "--reset",
    "-r",
    is_flag=True,
    help="Reset configuration and run setup wizard again",
)
def main(
    prompt: str | None,
    cwd: Path | None,
    version: bool,
    reset: bool,
):
    """
    BYOM AI Agents - Bring Your Own Model AI Coding Assistant

    A terminal-based AI coding agent that works with any LLM provider.
    """
    if version:
        banner = pyfiglet.figlet_format("BYOM AI", font="slant")
        console.print(banner, style="bright_cyan")
        console.print(f"Version: {__version__}\n", style="bright_white")
        return

    # Check for first run and show setup wizard
    if reset:
        # Delete existing config to trigger setup wizard
        from byom.config.loader import get_config_dir, CONFIG_FILE_NAME
        config_file = get_config_dir() / CONFIG_FILE_NAME
        if config_file.exists():
            config_file.unlink()
            console.print("[dim]Existing configuration deleted.[/dim]\n")
        show_welcome_banner(first_run=True)
        if not run_setup_wizard():
            console.print("[error]Setup cancelled[/error]")
            sys.exit(1)
    elif is_first_run():
        show_welcome_banner(first_run=True)
        if not run_setup_wizard():
            console.print("[error]Setup cancelled[/error]")
            sys.exit(1)
    else:
        # Show compact banner for subsequent runs
        show_welcome_banner(first_run=False)

    try:
        config = load_config(cwd=cwd)
    except Exception as e:
        console.print(f"[error]Configuration Error: {e}[/error]")
        sys.exit(1)

    errors = config.validate_config()

    if errors:
        for error in errors:
            console.print(f"[error]{error}[/error]")
        sys.exit(1)

    cli = CLI(config)

    if prompt:
        result = asyncio.run(cli.run_single(prompt))
        if result is None:
            sys.exit(1)
    else:
        asyncio.run(cli.run_interactive())


if __name__ == "__main__":
    main()
