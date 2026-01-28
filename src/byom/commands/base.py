from dataclasses import dataclass
from typing import Protocol, Any, TYPE_CHECKING
from rich.console import Console

if TYPE_CHECKING:
    from byom.agent.agent import Agent
    from byom.config.config import Config
    from byom.ui.tui import TUI

@dataclass
class CommandContext:
    """Context passed to commands during execution."""
    agent: 'Agent'
    config: 'Config'
    tui: 'TUI'
    console: Console

class Command(Protocol):
    """Protocol for CLI commands."""
    
    @property
    def name(self) -> str:
        """The command name, e.g. '/help'."""
        ...
        
    @property
    def description(self) -> str:
        """Short description for help/completion."""
        ...
        
    async def execute(self, context: CommandContext, args: str) -> bool:
        """
        Execute the command.
        Returns:
            bool: True if execution should continue, False to exit the application.
        """
        ...
