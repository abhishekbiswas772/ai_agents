from typing import Dict, List, Optional
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document

from byom.commands.base import Command, CommandContext

class CommandRegistry:
    """Registry to manage and execute commands."""

    def __init__(self):
        self._commands: Dict[str, Command] = {}

    def register(self, command: Command) -> None:
        """Register a new command."""
        self._commands[command.name.lower()] = command

    def get_command(self, name: str) -> Optional[Command]:
        """Retrieve a command by name."""
        return self._commands.get(name.lower())

    def get_all_commands(self) -> List[Command]:
        """Get all registered commands."""
        return list(self._commands.values())

    async def handle_input(self, context: CommandContext, input_str: str) -> bool:
        """
        Parse and execute a command from input string.
        Returns:
            bool: True to continue, False to exit.
        """
        parts = input_str.strip().split(maxsplit=1)
        if not parts:
            return True
            
        cmd_name = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        command = self.get_command(cmd_name)
        if command:
            # Execute command
            # Note: We need to ensure performace, commands are async
            return await command.execute(context, args)
        else:
            # Unknown command
            context.console.print(f"[error]Unknown command: {cmd_name}[/error]")
            return True

    def get_completer(self) -> Completer:
        """Returns a prompt_toolkit completer for this registry."""
        return CommandCompleter(self)


class CommandCompleter(Completer):
    """Completer for slash commands based on the registry."""
    
    def __init__(self, registry: CommandRegistry):
        self.registry = registry

    def get_completions(self, document: Document, complete_event):
        text = document.text_before_cursor
        
        # Only suggest if the line starts with / and we are typing the command part
        if not text.startswith('/'):
            return
            
        # If there's spaces, we might be typing args, don't complete command name
        if ' ' in text:
            return

        for command in self.registry.get_all_commands():
            if command.name.startswith(text):
                yield Completion(
                    command.name,
                    start_position=-len(text),
                    display=command.name,
                    display_meta=command.description
                )
