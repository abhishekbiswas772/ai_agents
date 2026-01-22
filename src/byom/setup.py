"""
BYOM AI Agents - Setup and First-Run Experience

Handles welcome banner, setup wizard, and configuration initialization.
"""
from pathlib import Path
import os
import pyfiglet
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich import box

from byom import __version__
from byom.config.loader import get_config_dir, get_data_dir
from byom.providers.presets import PROVIDER_PRESETS, get_config_for_preset

console = Console()


def show_welcome_banner(first_run: bool = False):
    """
    Show BYOM AI Agents banner

    Args:
        first_run: If True, show full setup banner. Otherwise show compact version.
    """
    banner = pyfiglet.figlet_format("BYOM AI", font="slant")

    if first_run:
        welcome_text = f"""[bright_cyan]{banner}[/bright_cyan]
[bold bright_white]Bring Your Own Model AI Coding Agent[/bold bright_white]
[dim]Version {__version__}[/dim]

Welcome! Let's get you set up with your preferred AI provider.
        """
        console.print(
            Panel(
                welcome_text,
                title="[bold]Welcome to BYOM AI Agents[/bold]",
                border_style="bright_cyan",
                box=box.DOUBLE,
            )
        )
    else:
        # Compact banner for subsequent runs
        console.print(f"[bright_cyan]{banner}[/bright_cyan]", highlight=False)
        console.print(f"[dim]v{__version__}[/dim]\n")


def run_setup_wizard() -> bool:
    """
    Run interactive setup wizard for first-time configuration

    Returns:
        bool: True if setup completed successfully, False if cancelled
    """
    console.print("\n[bold]Setup Wizard[/bold]", style="bright_yellow")
    console.print("This wizard will help you configure BYOM AI Agents.\n")

    # Step 1: Choose provider
    console.print("[bold]Step 1: Choose Your LLM Provider[/bold]\n")

    provider_table = Table(show_header=True, box=box.ROUNDED)
    provider_table.add_column("Option", style="cyan", width=8)
    provider_table.add_column("Provider", style="green", width=20)
    provider_table.add_column("Type", style="yellow", width=15)
    provider_table.add_column("Description", style="white")

    # Add provider options
    options = [
        (
            "1",
            "Ollama",
            "🏠 Local",
            "Run models locally (recommended for privacy)",
        ),
        (
            "2",
            "LM Studio",
            "🏠 Local",
            "Run models locally with GUI",
        ),
        (
            "3",
            "OpenRouter",
            "☁️  Cloud",
            "Access 200+ models through one API",
        ),
        (
            "4",
            "OpenAI",
            "☁️  Cloud",
            "GPT-4, GPT-3.5-turbo",
        ),
        (
            "5",
            "Anthropic",
            "☁️  Cloud",
            "Claude 3.5 Sonnet, Opus, Haiku",
        ),
        (
            "6",
            "Google AI",
            "☁️  Cloud",
            "Gemini Pro, Gemini 1.5",
        ),
    ]

    for opt, provider, ptype, desc in options:
        provider_table.add_row(opt, provider, ptype, desc)

    console.print(provider_table)
    console.print()

    provider_choice = Prompt.ask(
        "Select your provider", choices=["1", "2", "3", "4", "5", "6"], default="1"
    )

    # Map choice to preset
    preset_map = {
        "1": "ollama",
        "2": "lmstudio",
        "3": "openrouter",
        "4": "openai",
        "5": "anthropic",
        "6": "google",
    }

    preset_name = preset_map[provider_choice]
    preset = PROVIDER_PRESETS[preset_name]

    # Step 2: Configuration
    console.print(f"\n[bold]Step 2: Configure {preset.display_name}[/bold]\n")
    console.print(f"[dim]{preset.description}[/dim]\n")

    # Collect configuration
    config_data = {}

    # Model selection
    console.print("[bold]Available Models:[/bold]")
    for model in preset.example_models[:5]:
        console.print(f"  • {model}")
    if len(preset.example_models) > 5:
        console.print(f"  • ... and more")
    console.print()

    model = Prompt.ask("Enter model name", default=preset.default_model)
    config_data["model.name"] = model

    # Base URL (if needed)
    if preset.base_url:
        use_default_url = Confirm.ask(
            f"Use default URL ({preset.base_url})?", default=True
        )
        if use_default_url:
            base_url = preset.base_url
        else:
            base_url = Prompt.ask("Enter base URL")
        config_data["api.base_url"] = base_url

    # API Key (if required)
    api_key = None
    if preset.requires_api_key:
        env_key = os.environ.get(preset.api_key_env_var, "")
        if env_key:
            console.print(
                f"[green]✓[/green] Found {preset.api_key_env_var} in environment"
            )
            api_key = env_key
        else:
            console.print(f"\n[bold yellow]🔑 API Key Required[/bold yellow]")
            console.print(f"You can paste your API key here to store it securely in the config file.")
            console.print(f"[dim]Alternatively, leave empty to set {preset.api_key_env_var} environment variable manually.[/dim]")
            
            entered_key = Prompt.ask("Enter API Key", password=True)
            if entered_key:
                api_key = entered_key
                config_data["api.api_key"] = entered_key
            else:
                console.print(
                    f"[yellow]ℹ[/yellow] No key entered. You'll need to set {preset.api_key_env_var} manually."
                )

    # Step 3: Additional Settings
    console.print(f"\n[bold]Step 3: Additional Settings[/bold]\n")

    temperature = Prompt.ask(
        "Temperature (0.0-2.0, higher = more creative)",
        default="0.7",
    )
    config_data["model.temperature"] = float(temperature)

    # Approval policy with numbered options
    console.print("\n[bold]Approval Policy:[/bold]")
    console.print("  [cyan]1[/cyan] - auto: Auto-approve safe operations")
    console.print("  [cyan]2[/cyan] - on-request: Ask for each tool call (recommended)")
    console.print("  [cyan]3[/cyan] - never: Never auto-approve")

    approval_choice = Prompt.ask(
        "Select approval policy",
        choices=["1", "2", "3"],
        default="2",
    )

    approval_map = {
        "1": "auto",
        "2": "on-request",
        "3": "never",
    }
    config_data["behavior.approval_policy"] = approval_map[approval_choice]

    # Step 4: Create configuration
    console.print(f"\n[bold]Step 4: Saving Configuration[/bold]\n")

    # Create directories
    config_dir = get_config_dir()
    data_dir = get_data_dir()

    config_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"[dim]Config directory: {config_dir}[/dim]")
    console.print(f"[dim]Data directory: {data_dir}[/dim]\n")

    # Generate config.toml
    config = get_config_for_preset(preset_name, **config_data)

    config_content = f"""# BYOM AI Agents Configuration
# Generated by setup wizard for {preset.display_name}

[model]
name = "{config['model']['name']}"
provider = "{config['model']['provider']}"
temperature = {config_data.get('model.temperature', 0.7)}
max_tokens = 4096

[api]
"""

    if "api.base_url" in config_data:
        config_content += f"""base_url = "{config_data['api.base_url']}"
"""

    if "api.api_key" in config_data:
        config_content += f"""api_key = "{config_data['api.api_key']}"
"""
    elif preset.requires_api_key:
        if api_key:
            # Key found in env during setup, but not entered by user (so we don't save to config)
            config_content += f"""# API Key found in environment: {preset.api_key_env_var}
# api_key = "..." 
"""
        else:
            config_content += f"""# Set your API key via environment variable:
# export {preset.api_key_env_var}=your-key-here
# Or uncomment below to set directly:
# api_key = "your-key-here"
"""

    config_content += f"""
[behavior]
approval = "{config_data.get('behavior.approval_policy', 'auto')}"
max_turns = 25

# Hooks (custom scripts triggered on events)
hooks_enabled = false
# hooks = []  # Add custom hooks here

# MCP Servers (Model Context Protocol)
# [mcp_servers.example]
# command = "npx"
# args = ["-y", "@modelcontextprotocol/server-filesystem", "./"]
"""

    # Write config file
    config_file = config_dir / "config.toml"
    config_file.write_text(config_content)

    console.print(f"[green]✓[/green] Configuration saved to: {config_file}\n")

    # Environment setup instructions
    if preset.requires_api_key and not api_key:
        import platform
        is_windows = platform.system() == "Windows"
        
        console.print("\n[bold yellow]⚠️  API Key Setup Required[/bold yellow]")
        console.print(f"\n[bold]Set your API key as an environment variable:[/bold]\n")
        
        if is_windows:
            console.print(f"  [bold]Windows (Command Prompt):[/bold]")
            console.print(f"  [cyan]setx {preset.api_key_env_var} \"your-api-key\"[/cyan]")
            console.print(f"\n  [bold]Windows (PowerShell):[/bold]")
            console.print(f"  [cyan]$env:{preset.api_key_env_var} = \"your-api-key\"[/cyan]")
            console.print(f"  [dim]For permanent: Add to System Environment Variables[/dim]\n")
        else:
            console.print(f"  [cyan]export {preset.api_key_env_var}=<your-api-key>[/cyan]\n")
            console.print("[bold]Add to your shell profile for persistence:[/bold]")
            console.print("  • For Bash: Add to [cyan]~/.bashrc[/cyan]")
            console.print("  • For Zsh: Add to [cyan]~/.zshrc[/cyan]")
            console.print("  • For Fish: Add to [cyan]~/.config/fish/config.fish[/cyan]\n")

        console.print("[dim]For development: Create a .env file in your project root[/dim]")
        console.print(f"[dim]  echo '{preset.api_key_env_var}=<your-key>' >> .env[/dim]")
        console.print("[dim]  echo '.env' >> .gitignore  # Important![/dim]\n")

    # Special instructions for local providers
    if preset_name == "ollama":
        console.print("\n[bold cyan]📦 Ollama Setup Instructions[/bold cyan]")
        console.print("\n1. Install Ollama from: https://ollama.ai")
        console.print("2. Pull a model:")
        console.print(f"   [cyan]ollama pull {model}[/cyan]")
        console.print("3. Ollama runs automatically on http://localhost:11434\n")

    elif preset_name == "lmstudio":
        console.print("\n[bold cyan]📦 LM Studio Setup Instructions[/bold cyan]")
        console.print("\n1. Install LM Studio from: https://lmstudio.ai")
        console.print("2. Download and load a model")
        console.print("3. Start the local server (default: http://localhost:1234)\n")

    elif preset_name == "openrouter":
        console.print("\n[bold cyan]🔑 OpenRouter Setup[/bold cyan]")
        console.print("\n1. Get API key from: https://openrouter.ai/keys")
        console.print(
            "2. Browse models: https://openrouter.ai/models\n"
        )

    console.print("\n[green bold]✨ Setup complete![/green bold]")
    console.print("\nYou can now start using BYOM AI Agents:")
    console.print("  [cyan]byom[/cyan]              # Start interactive mode")
    console.print("  [cyan]byom 'your question'[/cyan]  # Single query mode\n")

    return True


def ensure_directories():
    """Ensure all required directories exist"""
    config_dir = get_config_dir()
    data_dir = get_data_dir()

    # Create main directories
    config_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    (data_dir / "sessions").mkdir(exist_ok=True)
    (data_dir / "checkpoints").mkdir(exist_ok=True)
    (data_dir / "todos").mkdir(exist_ok=True)
    (data_dir / "memory").mkdir(exist_ok=True)
    (data_dir / "logs").mkdir(exist_ok=True)
