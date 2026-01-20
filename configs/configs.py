from pathlib import Path
from typing import List
from pydantic import BaseModel, Field
import os
from dotenv import load_dotenv

load_dotenv()

class ModelConfig(BaseModel):
    name : str = ""
    temperature : float = Field(default=1, ge=0.0, le=2.0)
    context_window : int = 256_000

class ShellEnviormentPolicy(BaseModel):
    ignore_default_exclude : bool = False
    exclude_pattern : List[str] = Field(default_factory= lambda : ['*KEY*', '*TOKEN*', '*SECRET*'])
    set_vars : dict[str, str] = Field(default_factory=dict)
    

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

