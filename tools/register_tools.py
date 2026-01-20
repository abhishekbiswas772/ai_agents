from pathlib import Path
from typing import Any, Dict, List
from tools.base import Tool, ToolInvocation, ToolResult
import logging
from tools.builtin import get_all_buildin_tools
from configs.configs import Config

logger = logging.getLogger(__name__)


class ToolRegistery:
    def __init__(self):
        self._tools : Dict[str, Any] = {}


    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            logger.warning(f"Overwriting exiting tool: {tool.name}")

        self._tools[tool.name] = tool
        logger.debug(f"Register tool: {tool.name}")

    def unregister(self, name : str) -> bool:
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def get_tools(self) -> list[Tool]:
        tools : list[Tool] = []
        for tool in self._tools.values():
            tools.append(tool)
        return tools

    def get_schemas(self) -> List[Dict[str, Any]]:
        return [tool.to_openai_schema() for tool in self.get_tools()]

    def get(self, name: str) -> Tool | None:
        if name in self._tools:
            return self._tools[name]
        return None

    async def invoke(self, name: str, params: Dict[str, Any], cwd: Path) -> ToolResult:
        tool = self.get(name=name)
        if tool is None:
            return ToolResult.error_result(
                f"Unknown tool: {name}",
                metadata = {
                    "tool_name" : name
                }
            )
        validation_errors = tool.validate_params(params)
        if validation_errors:
            return ToolResult.error_result(
                f"Invalid Parameters : {'; '.join(validation_errors)}",
                metadata = {
                    "tool_name" : name,
                    "validation_errors" : validation_errors
                }
            )
        invocation = ToolInvocation(
            params=params,
            cwd=cwd
        )
        try:
            result = await tool.execute(invocation)

        except Exception as e:
            logger.exception(f"Tool {name} raised unexcepted error")
            result = ToolResult.error_result(
                f"Internal error : {str(e)}",
                metadata={
                    "tool_name": name
                }
            )
        return result



def create_default_registry(config: Config) -> ToolRegistery:
    registry =  ToolRegistery()
    for tool_class in get_all_buildin_tools():
        registry.register(tool_class(config))
    return registry
