from tools.base import Tool, ToolInvocation, ToolKind, ToolResult
from urllib.parse import urlparse
from pydantic import BaseModel, Field
import httpx

class WebFetchParams(BaseModel):
    url : str = Field(..., description="URL to fetch (must be http:// or https://)")
    timeout : int = Field(30, ge=30, le=120, description="Request timeout in seconds (default: 120)")

class WebFetchTool(Tool):
    name : str = "web_fetch"
    description : str = "Fetch content from a URL. Returns the response body as text"
    kind : ToolKind = ToolKind.NETWORK
    schema = WebFetchParams
    _MAX_BODY_LENGTH = 100 * 1024

    async def execute(self, invocation : ToolInvocation) -> ToolResult:
        params = WebFetchParams(**invocation.params)
        parsed_url = urlparse(params.url)
        if not parsed_url.scheme or parsed_url.scheme not in ("http", "https"):
            return ToolResult.error_result("Url must be http:// or https://")

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(params.timeout),
                follow_redirects=True,
            ) as client:
                response = await client.get(params.url)
                response.raise_for_status()
                text = response.text
        except httpx.HTTPStatusError as e:
            return ToolResult.error_result(
                f"HTTP {e.response.status_code}: {e.response.reason_phrase}",
            )
        except Exception as e:
            return ToolResult.error_result(f"Request failed: {e}")

        if len(text) > self._MAX_BODY_LENGTH:
            text = text[: self._MAX_BODY_LENGTH] + "\n... [content truncated]"

        return ToolResult.success_result(
            text,
            metadata={
                "status_code": response.status_code,
                "content_length": len(response.content),
            },
        )
