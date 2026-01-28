from byom.commands.base import Command, CommandContext
from byom.config.config import ApprovalPolicy

class ExitCommand(Command):
    name = "/exit"
    description = "Exit the application"

    async def execute(self, context: CommandContext, args: str) -> bool:
        return False

class HelpCommand(Command):
    name = "/help"
    description = "Show help message"

    async def execute(self, context: CommandContext, args: str) -> bool:
        context.tui.show_help()
        return True


class ConfigCommand(Command):
    name = "/config"
    description = "Show current configuration"

    async def execute(self, context: CommandContext, args: str) -> bool:
        c = context.config
        context.console.print("\n[bold bright_cyan]⚙️  Current Configuration[/bold bright_cyan]")
        context.console.print(f"  🤖 Model: [highlight]{c.model_name}[/highlight]")
        context.console.print(f"  🌡️  Temperature: [highlight]{c.temperature}[/highlight]")
        context.console.print(f"  ✅ Approval: [highlight]{c.approval.value}[/highlight]")
        context.console.print(f"  📂 Working Dir: [muted]{c.cwd}[/muted]")
        context.console.print(f"  🔄 Max Turns: [highlight]{c.max_turns}[/highlight]")
        # hooks_enabled might not exist on config directly in some versions, checking implementation
        if hasattr(c, 'hooks_enabled'):
            context.console.print(f"  🎣 Hooks Enabled: [highlight]{c.hooks_enabled}[/highlight]")
        return True

class ModelCommand(Command):
    name = "/model"
    description = "Get or set the current model"

    async def execute(self, context: CommandContext, args: str) -> bool:
        if args:
            context.config.model_name = args.strip()
            context.console.print(f"[success]Model changed to: {args.strip()}[/success]")
        else:
            context.console.print(f"Current model: {context.config.model_name}")
        return True

class ApprovalCommand(Command):
    name = "/approval"
    description = "Set approval policy"

    async def execute(self, context: CommandContext, args: str) -> bool:
        if args:
            try:
                approval = ApprovalPolicy(args.strip())
                context.config.approval = approval
                context.console.print(f"[success]Approval policy changed to: {args}[/success]")
            except:
                context.console.print(f"[error]Incorrect approval policy: {args}[/error]")
                context.console.print(f"Valid options: {', '.join(p for p in ApprovalPolicy)}")
        else:
             context.console.print(f"Current approval policy: {context.config.approval.value}")
        return True




def register_default_commands(registry):
    """Helper to register all default commands."""
    commands = [
        ExitCommand(),
        HelpCommand(),
        ConfigCommand(),
        ModelCommand(),
        ApprovalCommand()
    ]
    
    # We can handle aliases by registering same instance with different name if Command structure allowed it,
    # or just separate classes. For now let's just make a QuitCommand or handle in registry.
    # To keep it simple, I'll add QuitCommand here as subclass
    
    class QuitCommand(ExitCommand):
        name = "/quit"
    
    commands.append(QuitCommand())
    
    for cmd in commands:
        registry.register(cmd)
