from __future__ import annotations
from pathlib import Path
from typing import AsyncGenerator, List
from agents.events import AgentEvent, AgentEventType
from agents.session import Session
from clients.response import StreamEventType, ToolCall, ToolResultMessage
from configs.configs import Config
import json


class Agent:
    def __init__(self, config: Config):
        self.config = config
        self.session : Session | None = Session(self.config)

    async def run(self, message: str):
        yield AgentEvent.agent_start(message=message)
        enhanced_message = f"""{message}

To complete this task, you MUST use the available tools. Do not just provide text responses - call the appropriate tools first."""

        self.session.context_manager.add_user_message(content=enhanced_message)
        final_response = ""
        async for event in self._agentic_loop():
            yield event
            if event.type == AgentEventType.TEXT_COMPLETE:
                final_response = event.data.get("content", "")


        yield AgentEvent.agent_end(response=final_response)


    async def _agentic_loop(self) -> AsyncGenerator[AgentEvent, None]: #NOSONAR
        tool_schemas = self.session.tool_registry.get_schemas()
        max_iterations = self.config.max_turns
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            _ = self.session.increment_turn()
            response_text = ""
            had_error = False
            tool_calls: List[ToolCall] = []

            async for event in self.session.client.chat_completion(
                messages=self.session.context_manager.get_messages(),
                tools = tool_schemas if tool_schemas else None,
                stream=True
            ):
                # print(f"[AGENT DEBUG] Received event: {event.type}")
                if event.type == StreamEventType.TEXT_DELTA:
                    if event.text_delta:
                        content = event.text_delta.content
                        response_text += content
                        yield AgentEvent.text_delta(content=content)
                elif event.type == StreamEventType.TOOL_CALL_COMPLETE:
                    # print(f"[AGENT DEBUG] Tool call complete: {event.tool_call}")
                    if event.tool_call:
                        tool_calls.append(event.tool_call)
                        # print(f"[AGENT DEBUG] Added tool call: {event.tool_call.name}")
                elif event.type == StreamEventType.ERROR:
                    had_error = True
                    yield AgentEvent.agent_error(error=event.error or "unknown error occured")
                    return

            tool_calls_for_context = []
            if tool_calls:
                for tc in tool_calls:
                    tool_calls_for_context.append({
                        "id": tc.call_id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments) if isinstance(tc.arguments, dict) else tc.arguments
                        }
                    })

            if not had_error and (response_text or tool_calls):
                content_to_add = response_text if response_text else (None if tool_calls else "") #NOSONAR
                self.session.context_manager.add_assistant_message(
                    content=content_to_add,
                    tool_calls=tool_calls_for_context if tool_calls else None
                )
                if response_text:
                    yield AgentEvent.text_complete(content=response_text)

            if not tool_calls:
                return

            tool_call_result : List[ToolResultMessage] = []
            for tool_call in tool_calls:
                yield AgentEvent.tool_call_start(
                    call_id=tool_call.call_id,
                    name=tool_call.name,
                    arguments=tool_call.arguments
                )
                result = await self.session.tool_registry.invoke(
                    tool_call.name,
                    tool_call.arguments,
                    self.config.cwd
                )

                yield AgentEvent.tool_call_complete(
                    tool_call.call_id,
                    tool_call.name,
                    result,
                )
                tool_call_result.append(
                    ToolResultMessage(
                        tool_call_id=tool_call.call_id,
                        content=result.to_model_output(),
                        is_error=not result.success
                    )
                )
            for tool_result in tool_call_result:
                self.session.context_manager.add_tool_call_result(
                    tool_result.tool_call_id,
                    tool_result.content
                )
                

    async def __aenter__(self) -> Agent:
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.session.client:
            await self.session.client.close()
            self.session.client = None 
        

