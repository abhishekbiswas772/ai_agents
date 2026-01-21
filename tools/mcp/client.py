from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from fastmcp import Client
from fastmcp.client.transports import SSETransport, StdioTransport
from configs.configs import MCPServerConfig

from configs.configs import MCPServerConfig

class MCPServerStatus(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class MCPToolInfo:
    name : str
    description : str
    input_schema : dict[str, Any] = field(default_factory=dict)
    server_name : str = ""

class MCPClient:
    def __init__(
        self,
        name : str, 
        config : MCPServerConfig,
        cwd: Path
    ):
        self.name = name
        self.config = config
        self.cwd = cwd
        self.status = MCPServerStatus.DISCONNECTED
        self._client: Client | None = None
        self._tool: dict[str, MCPToolInfo] = dict()


    @property
    def tool(self) -> List[MCPToolInfo]:
        return list(self._tool.values())
    

    async def connect(self) -> None:
        if self.status == MCPServerStatus.CONNECTED:
            return 
        
        self.status = MCPServerStatus.CONNECTING
        try:
            self._client.__aenter__()
            tool_result = await self._client.list_tools()
            for tool in tool_result:
                self._tool[tool.name] = MCPToolInfo(
                    name=tool.name,
                    description=tool.description or "",
                    input_schema=(
                        tool.inputSchema if hasattr(tool, "inputSchema") else {}
                    ),
                    server_name=self.name
                )
            self.status = MCPServerStatus.CONNECTED
        except Exception:
            self.status = MCPServerStatus.CONNECTED
            raise 

    async def disconnected(self) -> None:
        if self._client:
            await self._client.__aexit__(None, None, None)
            self._client = None 
        self._tool.clear()
        self.status = MCPServerStatus.DISCONNECTED


    async def call_tool(self, tool_name: str, arguments: Dict[str,  Any]):
        if not self._client or self.status != MCPServerStatus.CONNECTED:
            raise RuntimeError(f"Not conncted to server {self.name}")
        result = await self._client.call_tool(tool_name, arguments)
        output = []
        for item in result.content:
            if hasattr(item, "text"):
                output.append(item.text)
            else:
                output.append(str(item))
        return {
            "output" : "\n".join(output),
            "is_error" : result.is_error
        }

