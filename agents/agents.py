from __future__ import annotations
from typing import AsyncGenerator
from agents.events import AgentEvent, AgentEventType
from clients.llm_client import LLMClient
from clients.response import StreamEventType


class Agent:
    def __init__(self):
        self.client = LLMClient() 

    

    async def run(self, messages: str):
        yield AgentEvent.agent_start(message=messages)
        final_response = ""
        async for event in self._agentic_loop():
            yield event
            if event.type == AgentEventType.TEXT_COMPLETE:
                final_response = event.data.get("content", "")

        
        yield AgentEvent.agent_end(response=final_response)


    async def _agentic_loop(self) -> AsyncGenerator[AgentEvent, None]:
        messages = [
            {
                "role" : "user",
                "content" : "what up man? how are you"
            }
        ]
        response_text = ""
        async for event in self.client.chat_completion(
            messages=messages,
            stream=True
        ):
            if event.type == StreamEventType.TEXT_DELTA:
                if event.text_delta:
                    content = event.text_delta.content
                    response_text += content
                    yield AgentEvent.text_delta(content=content)
            elif event.type == StreamEventType.ERROR:
                yield AgentEvent.agent_error(error=event.error or "unknown error occured")
            elif event.type == StreamEventType.MESSAGE_COMPLETE:
                # Stream finished; emit complete event with full accumulated response
                yield AgentEvent.text_complete(content=response_text)
                break

    async def __aenter__(self) -> Agent:
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.client:
            await self.client.close()
            self.client = None 
        

