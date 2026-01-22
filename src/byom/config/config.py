"""
BYOM AI Agents - Configuration Models

Pydantic models for all configuration options.
Supports BYOM (Bring Your Own Model) provider configuration.
"""

from __future__ import annotations
from enum import Enum
import os
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field, model_validator


class ProviderType(str, Enum):
    """Supported LLM provider types."""
    AUTO = "auto"           # Auto-detect from model name
    OPENAI = "openai"       # OpenAI and compatible APIs
    ANTHROPIC = "anthropic" # Anthropic Claude
    GOOGLE = "google"       # Google Gemini


class ThinkingConfig(BaseModel):
    """Configuration for thinking/reasoning models."""
    enabled: bool = False
    mode: str = "tags"  # "tags", "streaming", or "disabled"
    budget_tokens: int | None = None  # For Claude extended thinking


class ModelConfig(BaseModel):
    """Model configuration with BYOM support."""
    name: str = "gpt-4o-mini"
    provider: ProviderType = ProviderType.AUTO
    temperature: float = Field(default=1.0, ge=0.0, le=2.0)
    context_window: int = 128_000
    max_output_tokens: int | None = None
    
    # Provider-specific settings
    api_key_env: str = "API_KEY"      # Environment variable for API key
    base_url_env: str = "BASE_URL"    # Environment variable for base URL
    
    # Thinking model support
    thinking: ThinkingConfig = Field(default_factory=ThinkingConfig)


class ShellEnvironmentPolicy(BaseModel):
    """Shell environment security policy."""
    ignore_default_excludes: bool = False
    exclude_patterns: list[str] = Field(
        default_factory=lambda: ["*KEY*", "*TOKEN*", "*SECRET*", "*PASSWORD*"]
    )
    set_vars: dict[str, str] = Field(default_factory=dict)


class MCPServerConfig(BaseModel):
    """MCP (Model Context Protocol) server configuration."""
    enabled: bool = True
    startup_timeout_sec: float = 10

    # stdio transport
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    cwd: Path | None = None

    # http/sse transport
    url: str | None = None

    @model_validator(mode="after")
    def validate_transport(self) -> MCPServerConfig:
        has_command = self.command is not None
        has_url = self.url is not None

        if not has_command and not has_url:
            raise ValueError(
                "MCP Server must have either 'command' (stdio) or 'url' (http/sse)"
            )

        if has_command and has_url:
            raise ValueError(
                "MCP Server cannot have both 'command' (stdio) and 'url' (http/sse)"
            )

        return self


class ApprovalPolicy(str, Enum):
    """Tool execution approval policy."""
    ON_REQUEST = "on-request"   # Ask for each tool call
    ON_FAILURE = "on-failure"   # Ask only on errors
    AUTO = "auto"               # Auto-approve safe operations
    AUTO_EDIT = "auto-edit"     # Auto-approve including file edits
    NEVER = "never"             # Never auto-approve
    YOLO = "yolo"               # Approve everything (dangerous!)


class HookTrigger(str, Enum):
    """When to trigger hooks."""
    BEFORE_AGENT = "before_agent"
    AFTER_AGENT = "after_agent"
    BEFORE_TOOL = "before_tool"
    AFTER_TOOL = "after_tool"
    ON_ERROR = "on_error"


class HookConfig(BaseModel):
    """Custom hook configuration."""
    name: str
    trigger: HookTrigger
    command: str | None = None
    script: str | None = None
    timeout_sec: float = 30
    enabled: bool = True

    @model_validator(mode="after")
    def validate_hook(self) -> HookConfig:
        if not self.command and not self.script:
            raise ValueError("Hook must have either 'command' or 'script'")
        return self


class UIConfig(BaseModel):
    """Terminal UI configuration."""
    theme: str = "monokai"
    show_thinking: bool = True      # Show model reasoning if available
    show_token_usage: bool = True   # Show token counts
    compact_mode: bool = False      # Compact output
    max_output_lines: int = 100     # Max lines before truncation


class Config(BaseModel):
    """
    Main BYOM AI Agents configuration.
    
    Supports multiple providers, thinking models, and extensive customization.
    """
    model: ModelConfig = Field(default_factory=ModelConfig)
    cwd: Path = Field(default_factory=Path.cwd)
    shell_environment: ShellEnvironmentPolicy = Field(
        default_factory=ShellEnvironmentPolicy
    )
    ui: UIConfig = Field(default_factory=UIConfig)
    
    hooks_enabled: bool = False
    hooks: list[HookConfig] = Field(default_factory=list)
    approval: ApprovalPolicy = ApprovalPolicy.ON_REQUEST
    max_turns: int = 100
    mcp_servers: dict[str, MCPServerConfig] = Field(default_factory=dict)

    allowed_tools: list[str] | None = Field(
        None,
        description="If set, only these tools will be available",
    )

    developer_instructions: str | None = None
    user_instructions: str | None = None

    debug: bool = False
    
    # First-run tracking
    first_run: bool = True

    @property
    def api_key(self) -> str | None:
        """Get API key from environment."""
        return os.environ.get(self.model.api_key_env) or os.environ.get("API_KEY")

    @property
    def base_url(self) -> str | None:
        """Get base URL from environment."""
        return os.environ.get(self.model.base_url_env) or os.environ.get("BASE_URL")

    @property
    def model_name(self) -> str:
        return self.model.name

    @model_name.setter
    def model_name(self, value: str) -> None:
        self.model.name = value

    @property
    def temperature(self) -> float:
        return self.model.temperature

    @temperature.setter
    def temperature(self, value: float) -> None:
        self.model.temperature = value

    @property
    def provider(self) -> ProviderType:
        return self.model.provider

    def validate_config(self) -> list[str]:
        """
        Validate configuration and return list of errors.
        
        Returns:
            List of error messages, empty if valid
        """
        errors: list[str] = []

        if not self.api_key:
            errors.append(
                f"No API key found. Set {self.model.api_key_env} or API_KEY environment variable"
            )

        if not self.cwd.exists():
            errors.append(f"Working directory does not exist: {self.cwd}")

        return errors

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary."""
        return self.model_dump(mode="json")
