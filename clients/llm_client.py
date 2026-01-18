from typing import Any, AsyncGenerator, Dict, List
from openai import APIConnectionError, APIError, AsyncOpenAI, RateLimitError
from clients.response import TextDelta, TokenUsage, StreamEvent, StreamEventType, ToolCall, ToolCallDelta, parse_tool_call_arguments
import asyncio
import os
from dotenv import load_dotenv



class LLMClient:
    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None
        self.max_retries: int = 3
        self._think_buffer: str = ""
        self._in_think_tag: bool = False

    def get_client(self) -> AsyncOpenAI:
        if self._client is None:
            # Option 1: Use local LM Studio (uncomment these lines)
            # self._client = AsyncOpenAI(
            #     api_key='sk-xx',
            #     base_url='http://127.0.0.1:1234/v1'
            # )
            load_dotenv()
            self._client = AsyncOpenAI(
                api_key=os.getenv('OPENAI_API_KEY'),
            )
        return self._client


    #closing the clinet when not needed 
    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None

    # def _filter_think_tags(self, content: str) -> str:
    #     """Remove <think> tags and their content from the response."""
    #     result = []
    #     i = 0
    #     while i < len(content):
    #         if self._in_think_tag:
    #             # Look for closing tag
    #             close_idx = content.find('</think>', i)
    #             if close_idx != -1:
    #                 self._in_think_tag = False
    #                 self._think_buffer = ""
    #                 i = close_idx + 8  # Skip past </think>
    #             else:
    #                 # Still inside think tag, buffer everything
    #                 self._think_buffer += content[i:]
    #                 break
    #         else:
    #             # Look for opening tag
    #             open_idx = content.find('<think>', i)
    #             if open_idx != -1:
    #                 # Add content before the tag
    #                 result.append(content[i:open_idx])
    #                 self._in_think_tag = True
    #                 i = open_idx + 7  # Skip past <think>
    #             else:
    #                 # No more tags, add rest of content
    #                 result.append(content[i:])
    #                 break

    #     return ''.join(result) 

    async def _stream_response(self, client : AsyncGenerator, kwargs : Dict[str, Any]) -> AsyncGenerator[StreamEvent, None]:
        response = await client.chat.completions.create(**kwargs)
        finish_reason : str | None = None
        usage : TokenUsage | None = None
        tool_calls: Dict[int, Dict[str, Any]] = {}
        chunk_count = 0

        async for chunk in response:
            chunk_count += 1
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

        # print(f"[DEBUG] Stream finished. Chunks: {chunk_count}, Tool calls: {len(tool_calls)}, Finish reason: {finish_reason}")

        for idx, tc in tool_calls.items():
            yield StreamEvent(
                type=StreamEventType.TOOL_CALL_COMPLETE,
                tool_call=ToolCall(
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
            "model" : "gpt-3.5-turbo",  
            "messages" : messages,
            "stream" : stream,
            "temperature": 0.1,  
            # "max_tokens": 4096,
        }
        if tools:
            kwargs['tools'] = self._build_tools(tools=tools)
            kwargs['tool_choice'] = "auto"

        for attemps in range(self.max_retries + 1):
            try:
                # print(f"[DEBUG] Calling OpenAI API with model: {kwargs['model']}")
                if stream:
                    async for event in self._stream_response(client=client, kwargs=kwargs):
                        yield event
                else:
                    event = await self._non_stream_response(client=client, kwargs=kwargs)
                    yield event
                return 

            except RateLimitError as e:
                # print(f"[DEBUG] Rate limit error: {e}")
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
                # print(f"[DEBUG] Connection error: {e}")
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
                # print(f"[DEBUG] API error: {e}")
                yield StreamEvent(
                    type=StreamEventType.ERROR,
                    error=f"API Error: {e}",
                )
                return
            except Exception as e:
                # print(f"[DEBUG] Unexpected error: {type(e).__name__}: {e}")
                yield StreamEvent(
                    type=StreamEventType.ERROR,
                    error=f"Unexpected error: {e}",
                )
                return 