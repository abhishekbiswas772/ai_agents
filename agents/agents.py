from __future__ import annotations
from pathlib import Path
from typing import AsyncGenerator, List
from agents.events import AgentEvent, AgentEventType
from clients.llm_client import LLMClient
from clients.response import StreamEventType, ToolCall
from context.manager import ContextManager
from tools.register_tools import create_default_registry


class Agent:
    def __init__(self):
        self.client = LLMClient() 
        self.context_manager = ContextManager()
        self.tool_registry = create_default_registry()

    

    async def run(self, message: str):
        yield AgentEvent.agent_start(message=message)
        self.context_manager.add_user_message(content=message)
        final_response = ""
        async for event in self._agentic_loop():
            yield event
            if event.type == AgentEventType.TEXT_COMPLETE:
                final_response = event.data.get("content", "")

        
        yield AgentEvent.agent_end(response=final_response)


    async def _agentic_loop(self) -> AsyncGenerator[AgentEvent, None]:
        response_text = ""
        tool_schemas = self.tool_registry.get_schemas()
        had_error = False
        tool_calls: List[ToolCall] = []
        async for event in self.client.chat_completion(
            messages=self.context_manager.get_messages(),
            tools = tool_schemas if tool_schemas else None,
            stream=True
        ):
            if event.type == StreamEventType.TEXT_DELTA:
                if event.text_delta:
                    content = event.text_delta.content
                    response_text += content
                    yield AgentEvent.text_delta(content=content)
            elif event.type == StreamEventType.TOOL_CALL_COMPLETE:
                if event.tool_call:
                    tool_calls.append(event.tool_call)
            elif event.type == StreamEventType.ERROR:
                had_error = True
                yield AgentEvent.agent_error(error=event.error or "unknown error occured")
                return

        if not had_error and response_text:
            self.context_manager.add_assistant_message(content=response_text)
            yield AgentEvent.text_complete(content=response_text)

        for tool_call in tool_calls:
            yield AgentEvent.tool_call_start(
                call_id=tool_call.call_id,
                name=tool_call.name,
                arguments=tool_call.arguments
            )
            result = await self.tool_registry.invoke(
                tool_call.name,
                tool_call.arguments,
                Path.cwd
            )
                

    async def __aenter__(self) -> Agent:
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.client:
            await self.client.close()
            self.client = None 
        

