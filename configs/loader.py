from pathlib import Path
from typing import Any, Dict
from configs.configs import Config
from platformdirs import user_config_dir
from tomli import TOMLDecodeError
from utils.errors import ConfigError
import tomli
import logging
import os
from dotenv import load_dotenv


load_dotenv()

logger = logging.getLogger(__name__)

CONFIG_FILE_NAME = "config.toml"
AGENT_MD_FILE = "AGENT.md"

def get_config_dir(create: bool = False) -> Path:
    config_dir = Path(user_config_dir('ai-agents'))
    if create and not config_dir.exists():
        config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir

def get_system_path_config() -> Path:
    return get_config_dir() / CONFIG_FILE_NAME


def _parse_toml(path: Path):
    try:
        with open(path, 'rb') as file:
            return tomli.load(file)
    except TOMLDecodeError as e:
        raise ConfigError("Invalid TOML in {path}: {e}", config_file=str(path)) from e
    except (OSError | IOError) as e:
        raise ConfigError("Fail to read config file {path}: {e}", config_file=str(path)) from e


def _get_project_config(cwd: Path) -> Path | None:
    current_dir = cwd.resolve()
    agent_dir = current_dir/ '.ai-agents'
    if agent_dir.is_dir():
        config_file = agent_dir / CONFIG_FILE_NAME
        if config_file.is_file():
            return config_file
    return None 


def _get_agent_md_files(cwd: Path) -> Path | None:
    current_dir = cwd.resolve()
    if current_dir.is_dir():
        agent_md_file = current_dir / AGENT_MD_FILE
        if agent_md_file.is_file():
            content = agent_md_file.read_text(encoding='utf-8')
            return content
    return None 

def _merge_dict(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_dict(result[key], value)
        else:
            result[key] = value
    return result


def load_config(cwd: Path | None) -> Config:
    cwd = cwd or Path.cwd()
    system_path = get_system_path_config()
    config_dict : Dict[str, Any] = {}
    if system_path.is_file():
        try:
            config_dict = _parse_toml(system_path)
        except ConfigError:
            logger.warning(f"skipping invalid system config: {system_path}")

    project_path = _get_project_config(cwd=cwd)
    if project_path:
        try:
            project_config_dict = _parse_toml(project_path)
            config_dict = _merge_dict(config_dict, project_config_dict)
        except Exception as e:
            print(e)

    if "cwd" not in config_dict:
        config_dict["cwd"] = cwd

    if "developer_instructions" not in config_dict:
        agent_md_content = _get_agent_md_files(cwd)
        if agent_md_content:
            config_dict['developer_instructions'] = agent_md_content

    model_from_env = os.environ.get("MODEL")
    if model_from_env:
        if "model" not in config_dict:
            config_dict["model"] = {}
        config_dict["model"]["name"] = model_from_env
    provider_from_env = os.environ.get("PROVIDER")
    if provider_from_env:
        config_dict["provider"] = provider_from_env

    try:
        config = Config(**config_dict)
    except Exception as e:
        raise ConfigError(f'Invalid configuartion: {e}') from e
    return config


    
