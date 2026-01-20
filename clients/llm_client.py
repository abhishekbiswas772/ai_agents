from typing import Any, AsyncGenerator, Dict, List
from openai import APIConnectionError, APIError, AsyncOpenAI, RateLimitError
from clients.response import TextDelta, TokenUsage, StreamEvent, StreamEventType, ToolCall, ToolCallDelta, parse_tool_call_arguments
import asyncio
import os
from dotenv import load_dotenv

from configs.configs import Config



class LLMClient:
    """
    Multi-provider LLM client supporting OpenAI, Claude, Gemini, and local models.

    Supported providers:
    - openai: OpenAI API (GPT-4, GPT-3.5, etc.)
    - openrouter: OpenRouter API (multi-model gateway)
    - claude: Anthropic Claude (via OpenAI-compatible endpoint)
    - gemini: Google Gemini (via OpenAI-compatible endpoint)
    - lmstudio: LM Studio (local models)
    - ollama: Ollama (local models)
    """

    def __init__(self, config: Config) -> None:
        self._client: AsyncOpenAI | None = None
        self.max_retries: int = 3
        self._think_buffer: str = ""
        self._in_think_tag: bool = False
        self.config = config
        self.provider = config.provider_name

    def get_client(self) -> AsyncOpenAI:
        """
        Get or create the appropriate client based on the configured provider.

        All providers use OpenAI-compatible APIs, so we use AsyncOpenAI client
        but configure it with provider-specific base URLs and authentication.
        """
        if self._client is None:
            load_dotenv()

            api_key = self.config.api_key or "dummy"
            base_url = self.config.base_url

            # Provider-specific configuration
            if self.provider in ["openai", "openrouter"]:
                # OpenAI and OpenRouter use standard configuration
                self._client = AsyncOpenAI(
                    api_key=api_key,
                    base_url=base_url
                )
            elif self.provider == "claude":
                # Claude via OpenAI-compatible endpoint
                # Note: For native Anthropic SDK support, use anthropic library
                self._client = AsyncOpenAI(
                    api_key=api_key,
                    base_url=base_url or "https://api.anthropic.com"
                )
            elif self.provider == "gemini":
                # Gemini via OpenAI-compatible endpoint
                self._client = AsyncOpenAI(
                    api_key=api_key,
                    base_url=base_url or "https://generativelanguage.googleapis.com"
                )
            elif self.provider in ["lmstudio", "ollama"]:
                # Local model providers
                default_urls = {
                    "lmstudio": "http://localhost:1234/v1",
                    "ollama": "http://localhost:11434/v1"
                }
                self._client = AsyncOpenAI(
                    api_key="dummy",  # Local models don't need API keys
                    base_url=base_url or default_urls.get(self.provider)
                )
            else:
                # Fallback: treat as OpenAI-compatible
                self._client = AsyncOpenAI(
                    api_key=api_key,
                    base_url=base_url
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
            "model" : self.config.model_name,
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
