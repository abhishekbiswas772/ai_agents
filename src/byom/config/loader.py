"""
BYOM AI Agents - Configuration Loader

Handles loading configuration from files and environment,
auto-creating directories on first run, and merging configs.
Automatically loads .env files for development convenience.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any
import os
import logging

from platformdirs import user_config_dir, user_data_dir
from dotenv import load_dotenv
import tomli

from byom.config.config import Config

logger = logging.getLogger(__name__)

# Auto-load .env files for development (silent, doesn't override existing env vars)
load_dotenv(verbose=False, override=False)

APP_NAME = "byom-ai"
CONFIG_FILE_NAME = "config.toml"
AGENT_MD_FILE = "AGENT.md"


class ConfigError(Exception):
    """Configuration error with file context."""
    def __init__(self, message: str, config_file: str | None = None):
        super().__init__(message)
        self.config_file = config_file


def get_config_dir() -> Path:
    """Get the user config directory for BYOM AI."""
    return Path(user_config_dir(APP_NAME))


def get_data_dir() -> Path:
    """Get the user data directory for BYOM AI."""
    return Path(user_data_dir(APP_NAME))


def get_sessions_dir() -> Path:
    """Get the sessions storage directory."""
    return get_data_dir() / "sessions"


def get_todos_file() -> Path:
    """Get the todos storage file."""
    return get_data_dir() / "todos.json"


def get_memory_dir() -> Path:
    """Get the memory/scratchpad directory."""
    return get_data_dir() / "memory"


def is_first_run() -> bool:
    """
    Check if this is the first run (config directory doesn't exist).

    Returns:
        True if this is first run
    """
    config_dir = get_config_dir()
    config_file = config_dir / CONFIG_FILE_NAME

    # Consider it first run if config directory doesn't exist or config file is missing
    return not config_dir.exists() or not config_file.exists()


def ensure_directories() -> bool:
    """
    Ensure all required directories exist.

    Returns:
        True if this is first run (directories were created)
    """
    first_run = not get_config_dir().exists()

    # Create all directories
    get_config_dir().mkdir(parents=True, exist_ok=True)
    get_data_dir().mkdir(parents=True, exist_ok=True)
    get_sessions_dir().mkdir(parents=True, exist_ok=True)
    get_memory_dir().mkdir(parents=True, exist_ok=True)

    return first_run


def get_system_config_path() -> Path:
    """Get path to system-wide config file."""
    return get_config_dir() / CONFIG_FILE_NAME


def _parse_toml(path: Path) -> dict[str, Any]:
    """Parse a TOML file."""
    try:
        with open(path, "rb") as f:
            return tomli.load(f)
    except tomli.TOMLDecodeError as e:
        raise ConfigError(f"Invalid TOML in {path}: {e}", config_file=str(path)) from e
    except (OSError, IOError) as e:
        raise ConfigError(f"Failed to read config file {path}: {e}", config_file=str(path)) from e


def _get_project_config(cwd: Path) -> Path | None:
    """Find project-local config file."""
    current = cwd.resolve()
    
    # Check for .byom directory
    byom_dir = current / ".byom"
    if byom_dir.is_dir():
        config_file = byom_dir / CONFIG_FILE_NAME
        if config_file.is_file():
            return config_file
    
    # Legacy: check for .ai-agent directory
    agent_dir = current / ".ai-agent"
    if agent_dir.is_dir():
        config_file = agent_dir / CONFIG_FILE_NAME
        if config_file.is_file():
            return config_file

    return None


def _get_agent_md_content(cwd: Path) -> str | None:
    """Read AGENT.md file if present."""
    for filename in [AGENT_MD_FILE, "AGENT.MD", "agent.md"]:
        agent_md_path = cwd / filename
        if agent_md_path.is_file():
            try:
                return agent_md_path.read_text(encoding="utf-8")
            except (OSError, IOError):
                pass
    return None


def _merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


def create_default_config() -> str:
    """Generate default configuration file content."""
    return '''# BYOM AI Agents Configuration
# See documentation for all options

[model]
name = "gpt-4o-mini"  # Model name
provider = "auto"       # auto, openai, anthropic, google
temperature = 1.0

# For thinking models (DeepSeek, Claude with extended thinking)
[model.thinking]
enabled = false
mode = "tags"  # "tags" for <think> parsing, "streaming" for native

[ui]
theme = "monokai"
show_thinking = true
show_token_usage = true

# Behavior settings
approval = "on-request"  # on-request, auto, auto-edit, never, yolo
max_turns = 100

# Hooks (custom scripts triggered on events)
hooks_enabled = false
# hooks = []  # Add custom hooks here

# MCP Servers (optional)
# [mcp_servers.filesystem]
# command = "npx"
# args = ["-y", "@anthropic-ai/mcp-server-filesystem", "./"]
'''


def load_config(cwd: Path | None = None) -> Config:
    """
    Load configuration from files and environment.
    
    Config is loaded in order of precedence (later overrides earlier):
    1. Built-in defaults
    2. System config (~/.config/byom-ai/config.toml)
    3. Project config (.byom/config.toml in project root)
    4. Environment variables
    
    Args:
        cwd: Working directory (defaults to current)
        
    Returns:
        Loaded Config object
    """
    cwd = (cwd or Path.cwd()).resolve()
    
    # Ensure directories exist and check if first run
    first_run = ensure_directories()
    
    # Start with empty config dict
    config_dict: dict[str, Any] = {}
    
    # Load system config
    system_path = get_system_config_path()
    if system_path.is_file():
        try:
            config_dict = _parse_toml(system_path)
        except ConfigError as e:
            logger.warning(f"Skipping invalid system config: {e}")
    elif first_run:
        # Create default config on first run
        try:
            system_path.write_text(create_default_config(), encoding="utf-8")
            logger.info(f"Created default config at {system_path}")
        except (OSError, IOError) as e:
            logger.warning(f"Could not create default config: {e}")
    
    # Load project config
    project_path = _get_project_config(cwd)
    if project_path:
        try:
            project_config = _parse_toml(project_path)
            config_dict = _merge_dicts(config_dict, project_config)
        except ConfigError as e:
            logger.warning(f"Skipping invalid project config: {e}")
    
    # Set working directory
    if "cwd" not in config_dict:
        config_dict["cwd"] = cwd
    
    # Load AGENT.md as developer instructions
    if "developer_instructions" not in config_dict:
        agent_md = _get_agent_md_content(cwd)
        if agent_md:
            config_dict["developer_instructions"] = agent_md
    
    # Track first run
    config_dict["first_run"] = first_run
    
    try:
        config = Config(**config_dict)
    except Exception as e:
        raise ConfigError(f"Invalid configuration: {e}") from e
    
    return config


def save_config(config: Config, path: Path | None = None) -> None:
    """
    Save configuration to file.
    
    Args:
        config: Config to save
        path: Path to save to (defaults to system config)
    """
    import tomli_w
    
    path = path or get_system_config_path()
    
    # Convert to dict, excluding runtime-only fields
    data = config.to_dict()
    data.pop("cwd", None)
    data.pop("first_run", None)
    
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        tomli_w.dump(data, f)
