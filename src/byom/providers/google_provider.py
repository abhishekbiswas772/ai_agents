"""
Google Gemini LLM Provider

Supports:
- Gemini Pro
- Gemini 1.5 Pro/Flash
- Gemini 2.0 models
"""

from __future__ import annotations
import json
from typing import Any, AsyncGenerator
import logging

try:
    import google.generativeai as genai
    from google.generativeai.types import GenerateContentResponse, Content
    HAS_GOOGLE = True
except ImportError:
    HAS_GOOGLE = False

from byom.providers.base import (
    LLMProvider,
    ProviderConfig,
    StreamEvent,
    ThinkingMode,
)
from byom.providers.registry import register_provider

logger = logging.getLogger(__name__)


if HAS_GOOGLE:
    @register_provider
    class GoogleProvider(LLMProvider):
        """
        Google Gemini provider.

        Supports Gemini Pro and 1.5 model families with function calling.
        """

        name = "google"
        display_name = "Google Gemini"

        model_patterns = [
            r"^gemini-.*",              # All Gemini models
            r"^google/gemini-.*",       # OpenRouter format
        ]

        def __init__(self, config: ProviderConfig) -> None:
            super().__init__(config)
            self._configured = False

        def _configure_genai(self) -> None:
            """Configure the Google Generative AI library."""
            if not self._configured and self.config.api_key:
                genai.configure(api_key=self.config.api_key)
                self._configured = True

        async def close(self) -> None:
            """Close the Google client."""
            # Google SDK doesn't require explicit cleanup
            pass

        def _convert_messages(
            self, messages: list[dict[str, Any]]
        ) -> tuple[str | None, list[Content]]:
            """
            Convert OpenAI-style messages to Gemini format.

            Returns:
                Tuple of (system_instruction, contents)
            """
            system_instruction = None
            contents = []

            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")

                if role == "system":
                    system_instruction = content
                elif role == "assistant":
                    # Gemini uses "model" for assistant
                    parts = []

                    if content:
                        parts.append({"text": content})

                    # Handle tool calls
                    if msg.get("tool_calls"):
                        for tc in msg["tool_calls"]:
                            func = tc.get("function", {})
                            args = func.get("arguments", "")
                            if isinstance(args, str):
                                try:
                                    args = json.loads(args)
                                except json.JSONDecodeError:
                                    args = {}

                            parts.append({
                                "function_call": {
                                    "name": func.get("name", ""),
                                    "args": args,
                                }
                            })

                    contents.append(Content(role="model", parts=parts))

                elif role == "tool":
                    # Tool results in Gemini format
                    tool_call_id = msg.get("tool_call_id", "")
                    # Gemini expects function_response
                    contents.append(Content(
                        role="function",
                        parts=[{
                            "function_response": {
                                "name": tool_call_id,  # Use ID as name
                                "response": {"result": content},
                            }
                        }]
                    ))
                else:
                    # User messages
                    contents.append(Content(role="user", parts=[{"text": content}]))

            return system_instruction, contents

        def build_tool_schema(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
            """Convert to Gemini function declarations."""
            declarations = []

            for tool in tools:
                func_decl = {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                }

                # Convert JSON schema to Gemini's parameter format
                params = tool.get("parameters", {})
                if params:
                    func_decl["parameters"] = params

                declarations.append(func_decl)

            return declarations

        async def chat_completion(
            self,
            messages: list[dict[str, Any]],
            model: str,
            tools: list[dict[str, Any]] | None = None,
            stream: bool = True,
            temperature: float = 1.0,
            max_tokens: int | None = None,
        ) -> AsyncGenerator[StreamEvent, None]:
            """Send a chat completion request to Gemini."""
            self._reset_thinking_state()
            self._configure_genai()

            # Strip provider prefix if present
            if model.startswith("google/"):
                model = model[len("google/"):]

            system_instruction, converted_messages = self._convert_messages(messages)

            # Create model instance
            generation_config = {
                "temperature": temperature,
            }
            if max_tokens:
                generation_config["max_output_tokens"] = max_tokens

            tool_config = None
            if tools:
                tool_config = self.build_tool_schema(tools)

            try:
                gemini_model = genai.GenerativeModel(
                    model_name=model,
                    generation_config=generation_config,
                    tools=tool_config,
                    system_instruction=system_instruction,
                )

                if stream:
                    async for event in self._stream_response(gemini_model, converted_messages):
                        yield event
                else:
                    event = await self._non_stream_response(gemini_model, converted_messages)
                    yield event

            except Exception as e:
                yield StreamEvent(type="error", error=f"Google API error: {e}")

        async def _stream_response(
            self,
            model: Any,
            messages: list[Content],
        ) -> AsyncGenerator[StreamEvent, None]:
            """Handle streaming response from Gemini."""
            try:
                response = await model.generate_content_async(
                    messages,
                    stream=True,
                )

                async for chunk in response:
                    if not chunk.candidates:
                        continue

                    candidate = chunk.candidates[0]
                    content = candidate.content

                    if not content.parts:
                        continue

                    for part in content.parts:
                        # Handle text content
                        if hasattr(part, 'text') and part.text:
                            text_content, thinking = self._process_thinking(part.text)
                            if thinking:
                                yield StreamEvent(type="thinking", thinking=thinking)
                            if text_content:
                                yield StreamEvent(type="text", content=text_content)

                        # Handle function calls
                        if hasattr(part, 'function_call') and part.function_call:
                            fc = part.function_call
                            # Generate a call ID for Gemini (it doesn't provide one)
                            call_id = f"gemini_{fc.name}_{hash(str(fc.args))}"

                            yield StreamEvent(
                                type="tool_call_start",
                                tool_call_id=call_id,
                                tool_name=fc.name,
                            )

                            # Convert args dict to match expected format
                            args = dict(fc.args) if fc.args else {}

                            yield StreamEvent(
                                type="tool_call",
                                tool_call_id=call_id,
                                tool_name=fc.name,
                                tool_arguments=args,
                            )

                # Completion event
                # Note: Gemini doesn't provide detailed usage stats in streaming
                yield StreamEvent(
                    type="done",
                    finish_reason="stop",
                )

            except Exception as e:
                logger.exception("Error in Gemini streaming")
                yield StreamEvent(type="error", error=str(e))

        async def _non_stream_response(
            self,
            model: Any,
            messages: list[Content],
        ) -> StreamEvent:
            """Handle non-streaming response from Gemini."""
            try:
                response = await model.generate_content_async(messages)

                if not response.candidates:
                    return StreamEvent(
                        type="done",
                        content=None,
                        finish_reason="blocked",
                    )

                candidate = response.candidates[0]
                content = candidate.content

                text_parts = []
                thinking_parts = []
                tool_calls = []

                for part in content.parts:
                    if hasattr(part, 'text') and part.text:
                        clean, thinking = self._process_thinking(part.text)
                        if clean:
                            text_parts.append(clean)
                        if thinking:
                            thinking_parts.append(thinking)

                    if hasattr(part, 'function_call') and part.function_call:
                        fc = part.function_call
                        call_id = f"gemini_{fc.name}_{hash(str(fc.args))}"

                        tool_calls.append({
                            "id": call_id,
                            "name": fc.name,
                            "arguments": dict(fc.args) if fc.args else {},
                        })

                usage = None
                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    um = response.usage_metadata
                    usage = {
                        "prompt_tokens": um.prompt_token_count,
                        "completion_tokens": um.candidates_token_count,
                        "total_tokens": um.total_token_count,
                    }

                return StreamEvent(
                    type="done",
                    content="\n".join(text_parts) if text_parts else None,
                    thinking="\n".join(thinking_parts) if thinking_parts else None,
                    finish_reason=candidate.finish_reason.name if candidate.finish_reason else "stop",
                    usage=usage,
                )

            except Exception as e:
                logger.exception("Error in Gemini non-streaming")
                return StreamEvent(type="error", error=str(e))
