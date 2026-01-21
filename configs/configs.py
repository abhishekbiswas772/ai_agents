from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List
from pydantic import BaseModel, Field
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator
from enum import Enum

load_dotenv()

class ModelConfig(BaseModel):
    name : str = ""
    temperature : float = Field(default=1, ge=0.0, le=2.0)
    context_window : int = 256_000

class ShellEnviormentPolicy(BaseModel):
    ignore_default_exclude : bool = False
    exclude_pattern : List[str] = Field(default_factory= lambda : ['*KEY*', '*TOKEN*', '*SECRET*'])
    set_vars : dict[str, str] = Field(default_factory=dict)


class MCPServerConfig(BaseModel):
    enabled: bool = True 
    startup_timeout_sec: float = 10
    command : str | None = None 
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    cwd: Path | None = None
    url: str | None = None 

    @model_validator(model = "after")
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
    ON_REQUEST = "on-request"
    ON_FAILURE = "on-failure"
    AUTO = "auto"
    AUTO_EDIT = "auto-edit"
    NEVER = "never"
    YOLO = "yolo"

class HookTrigger(str, Enum):
    BEFORE_AGENT = "before_agent"
    AFTER_AGENT = "after_agent"
    BEFORE_TOOL = "before_tool"
    AFTER_TOOL = "after_tool"
    ON_ERROR = "on_error"

class HookConfig(BaseModel):
    name : str
    trigger : HookTrigger
    command: str | None = None 
    script : str | None = None 
    timeout_sec : float = 30
    enabled: bool = True 

    @model_validator(mode = "after")
    def validate_hook(self) -> HookConfig:
        if not self.command and not self.script:
            raise ValueError("Hook must either have 'command' or 'script'")
        return self


class Config(BaseModel):
    model : ModelConfig = Field(default_factory=ModelConfig)
    cwd: Path = Field(default_factory=Path.cwd)
    shell_enviorment : ShellEnviormentPolicy = Field(default_factory=ShellEnviormentPolicy)
    max_turns : int = 100
    developer_instructions : str | None = None
    user_instructions : str | None = None
    debug : bool = False
    provider : str = "openai"  # openai, claude, gemini, lmstudio, ollama, openrouter


    @property
    def api_key(self) -> str | None:
        return os.environ.get("API_KEY")


    @property
    def base_url(self) -> str | None:
        return os.environ.get("BASE_URL")

    @property
    def provider_name(self) -> str:
        """Get the provider name from environment or config."""
        return os.environ.get("PROVIDER", self.provider).lower()

    @property
    def model_name(self) -> str:
        return self.model.name

    @model_name.setter
    def model_name(self, value : str) -> None:
        self.model.name = value

    @property
    def temperature(self) -> float:
        return self.model.temperature

    @temperature.setter
    def temperature(self, value : float) -> None:
        self.model.temperature = value

    def validate(self) -> List[str]:
        errors : List[str] = []
        if not self.api_key:
            errors.append("No API key found. Set API_KEY in enviorment variable")

        if not self.cwd.exists():
            errors.append(f"Working directory doesnot exits: {self.cwd}")

        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode = "json")

