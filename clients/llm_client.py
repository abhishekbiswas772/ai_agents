
from typing import Any, AsyncGenerator, Dict, List
from openai import APIConnectionError, APIError, AsyncOpenAI, RateLimitError
from clients.response import TextDelta, TokenUsage, StreamEvent, StreamEventType, ToolCall, ToolCallDelta, parse_tool_call_arguments
import asyncio



class LLMClient:
    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None 
        self.max_retries: int = 3

    def get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key='sk-xx',
                base_url='http://127.0.0.1:1234/v1'
            ) 
        return self._client


    #closing the clinet when not needed 
    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None 

    async def _stream_response(self, client : AsyncGenerator, kwargs : Dict[str, Any]) -> AsyncGenerator[StreamEvent, None]:
        response = await client.chat.completions.create(**kwargs)
        finish_reason : str | None = None 
        usage : TokenUsage | None = None 
        tool_calls: Dict[int, Dict[str, Any]] = {}

        async for chunk in response:
            if hasattr(chunk, "usage") and chunk.usage:
                usage = TokenUsage(
                    prompt_tokens=chunk.usage.prompt_tokens,
                    completion_tokens=chunk.usage.completion_tokens,
                    total_tokens=chunk.usage.total_tokens,
                    cached_tokens=chunk.usage.prompt_tokens_details.cached_tokens
                )
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            delta = choice.delta 

            if choice.finish_reason:
                finish_reason = choice.finish_reason

            if delta.content:
                yield StreamEvent(
                    type=StreamEventType.TEXT_DELTA,
                    text_delta=TextDelta(content=delta.content),
                )
            if delta.tool_calls:
                for tool_call_delta in delta.tool_calls:
                    idx =  tool_call_delta.index
                    if idx not in tool_calls:
                        tool_calls[idx] = {
                            'id': tool_call_delta.id or "",
                            'name' : '',
                            'arguments' : ''
                        }

                        if tool_call_delta.function:
                            if tool_call_delta.function.name:
                                tool_calls[idx]['name'] = tool_call_delta.function.name
                                yield StreamEvent(
                                    type=StreamEventType.TOOL_CALL_START,
                                    tool_call_delta=ToolCallDelta(
                                        call_id=tool_calls[idx]['id'],
                                        name=tool_call_delta.function.name,
                                    )
                                )

                        if tool_call_delta.function.arguments:
                            tool_calls[idx]['arguments'] += tool_call_delta.function.arguments
                            yield StreamEvent(
                                type=StreamEventType.TOOL_CALL_DELTA,
                                tool_call_delta=ToolCallDelta(
                                    call_id=tool_calls[idx]['id'],
                                    name=tool_call_delta.function.name,
                                    arguments_delta=tool_call_delta.function.arguments
                                )
                            )

        for idx, tc in tool_calls.items():
            yield StreamEvent(
                type=StreamEventType.TOOL_CALL_COMPLETE,
                tool_call_delta=ToolCall(
                    call_id=tc['id'],
                    name=tc['name'],
                    arguments=parse_tool_call_arguments(tc['arguments'])
                )
            ) 

        yield StreamEvent(
            type=StreamEventType.MESSAGE_COMPLETE,
            finish_reason=finish_reason,
            usage=usage
        )


    async def _non_stream_response(self, client: AsyncOpenAI, kwargs: Dict[str, Any]) -> StreamEvent:
        response = await client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        message = choice.message
        text_delta = None
        usage = None
        tool_calls : List[ToolCall] = []
        if message.content:
            text_delta = TextDelta(content = message.content)

        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append(ToolCall(
                    call_id=tc.id,
                    name=tc.function_name,
                    arguments=parse_tool_call_arguments(tc.function.arguments)
                ))


        if response.usage:
            usage = TokenUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                cached_tokens=response.usage.prompt_tokens_details.cached_tokens
            )

        return StreamEvent(
            type=StreamEventType.MESSAGE_COMPLETE,
            text_delta=text_delta,
            finish_reason=choice.finish_reason,
            usage=usage
        )
    
    def _build_tools(self, tools: List[Dict[str, Any]]):
        return [
            {
                'type' : 'function',
                'function' : {
                    'name' : tool['name'],
                    'description' : tool['description'],
                    'parameters' : tool.get(
                        "parameters",
                        {
                            'type' : 'object',
                            'properties' : {}
                        }
                    )

                }
            }
            for tool in tools
        ]
            

    async def chat_completion(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]] | None = None, stream: bool = True) -> AsyncGenerator[StreamEvent, None]:
        client = self.get_client()
        kwargs : Dict[str, Any] = {
            "model" : "qwen/qwen3-1.7b",
            "messages" : messages,
            "stream" : stream,
        }
        if tools:
            kwargs['tools'] = self._build_tools(tools=tools)
            kwargs['tool_choice'] = "auto"

        for attemps in range(self.max_retries + 1):
            try:
                if stream:
                    async for event in self._stream_response(client=client, kwargs=kwargs):
                        yield event
                else:
                    event = await self._non_stream_response(client=client, kwargs=kwargs)
                    yield event
                return 

            except RateLimitError as e:
                if attemps < self.max_retries:
                    wait_time = 2 ** attemps
                    await asyncio.sleep(wait_time)
                else:
                    yield StreamEvent(
                        type=StreamEventType.ERROR,
                        error=f"Rate limit is exceeded: {e}",
                    )
                    return
            except APIConnectionError as e:
                if attemps < self.max_retries:
                    wait_time = 2 ** attemps
                    await asyncio.sleep(wait_time)
                else:
                    yield StreamEvent(
                        type=StreamEventType.ERROR,
                        error=f"Connection Error: {e}",
                    )
                    return
            except APIError as e:
                yield StreamEvent(
                    type=StreamEventType.ERROR,
                    error=f"API Error: {e}",
                )
                return 