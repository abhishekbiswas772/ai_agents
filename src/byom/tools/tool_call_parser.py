"""
Tool call parsing and validation utilities.

Handles parsing of tool calls from various LLM providers with robust error handling,
JSON repair, and fallback strategies.
"""

from __future__ import annotations

import json
import re
from typing import Any

from byom.client.response import ToolCall


class ToolCallParseError(Exception):
    """Raised when tool call parsing fails."""

    pass


def repair_json(json_str: str) -> str:
    """
    Attempt to repair malformed JSON strings.

    Common issues handled:
    - Trailing commas in objects/arrays
    - Missing quotes around keys
    - Single quotes instead of double quotes
    - Unescaped newlines in strings
    - Truncated structures (unclosed braces/brackets)
    """
    if not json_str or not json_str.strip():
        return "{}"

    repaired = json_str

    # 1. Replace single quotes with double quotes (if not in strings)
    # This is a simple heuristic - doesn't handle all cases
    if "'" in repaired and '"' not in repaired:
        repaired = repaired.replace("'", '"')

    # 2. Remove trailing commas before closing braces/brackets
    repaired = re.sub(r',\s*}', '}', repaired)
    repaired = re.sub(r',\s*]', ']', repaired)

    # 3. Add missing quotes around unquoted keys (simple pattern)
    repaired = re.sub(r'(\{|\,)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', repaired)

    # 4. Handle truncated JSON by closing open structures
    open_braces = repaired.count('{') - repaired.count('}')
    open_brackets = repaired.count('[') - repaired.count(']')

    if open_braces > 0:
        repaired += '}' * open_braces
    if open_brackets > 0:
        repaired += ']' * open_brackets

    # 5. Remove control characters that break JSON
    repaired = re.sub(r'[\x00-\x1f\x7f]', '', repaired)

    # 6. Handle escaped newlines
    repaired = repaired.replace('\\n', ' ')

    return repaired


def parse_json_safe(json_str: str) -> dict[str, Any]:
    """
    Safely parse a JSON string with repair and fallback.

    Returns:
        Parsed dict or {"raw_arguments": json_str} if parsing fails
    """
    if not json_str or not json_str.strip():
        return {}

    # Strategy 1: Direct JSON parse
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Repair and retry
    try:
        repaired = repair_json(json_str)
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    # Strategy 3: Extract JSON object if it's embedded in text
    try:
        # Look for {...} pattern
        match = re.search(r'\{.*\}', json_str, re.DOTALL)
        if match:
            extracted = match.group()
            return json.loads(repair_json(extracted))
    except json.JSONDecodeError:
        pass

    # Strategy 4: Heuristic key-value extraction
    try:
        extracted = _extract_key_values_heuristic(json_str)
        if extracted:
            return extracted
    except Exception:
        pass

    # Last resort: return raw string with error flag
    return {"raw_arguments": json_str, "_parse_error": True}


def _extract_key_values_heuristic(text: str) -> dict[str, Any]:
    """
    Heuristic extraction of key-value pairs from malformed JSON-like text.

    This is a last-resort fallback that tries to extract useful information
    even when JSON is severely malformed.
    """
    result = {}

    # Pattern: "key": value or key: value
    pattern = r'["\']?([a-zA-Z_][a-zA-Z0-9_]*)["\']?\s*:\s*([^,\}\]]+)'

    matches = re.finditer(pattern, text)
    for match in matches:
        key = match.group(1)
        value_str = match.group(2).strip()

        # Try to parse the value
        if value_str.startswith('"') and value_str.endswith('"'):
            result[key] = value_str[1:-1]
        elif value_str.startswith("'") and value_str.endswith("'"):
            result[key] = value_str[1:-1]
        elif value_str.lower() == 'true':
            result[key] = True
        elif value_str.lower() == 'false':
            result[key] = False
        elif value_str.lower() == 'null':
            result[key] = None
        else:
            # Try to parse as number
            try:
                if '.' in value_str:
                    result[key] = float(value_str)
                else:
                    result[key] = int(value_str)
            except ValueError:
                # Keep as string
                result[key] = value_str.strip('"\'')

    return result


def validate_tool_call(tool_call: ToolCall) -> tuple[bool, str | None]:
    """
    Validate a tool call.

    Returns:
        (is_valid, error_message)
    """
    errors = []

    if not tool_call.call_id or not tool_call.call_id.strip():
        errors.append("call_id is empty")

    if not tool_call.name or not tool_call.name.strip():
        errors.append("tool name is empty")

    if isinstance(tool_call.arguments, str) and tool_call.arguments.strip():
        try:
            json.loads(tool_call.arguments)
        except json.JSONDecodeError:
            # Try repair
            try:
                json.loads(repair_json(tool_call.arguments))
            except json.JSONDecodeError:
                errors.append(f"arguments are not valid JSON: {tool_call.arguments[:100]}")

    return (len(errors) == 0, "; ".join(errors) if errors else None)


def normalize_tool_call(raw_tool_call: dict[str, Any]) -> ToolCall:
    """
    Normalize a tool call from any provider format to standard ToolCall.

    Handles different provider formats:
    - OpenAI: {id, function: {name, arguments}}
    - Anthropic: {type, id, name, input}
    - Google: {functionCalls: [{name, arguments}]}
    """
    # Standard OpenAI format
    if "function" in raw_tool_call:
        func = raw_tool_call.get("function", {})
        return ToolCall(
            call_id=raw_tool_call.get("id", ""),
            name=func.get("name", ""),
            arguments=parse_json_safe(func.get("arguments", "")),
        )

    # Anthropic format
    if raw_tool_call.get("type") == "tool_use":
        args = raw_tool_call.get("input", {})
        if isinstance(args, dict):
            args = json.dumps(args)
        return ToolCall(
            call_id=raw_tool_call.get("id", ""),
            name=raw_tool_call.get("name", ""),
            arguments=parse_json_safe(args),
        )

    # Google format
    if "name" in raw_tool_call and "arguments" in raw_tool_call:
        return ToolCall(
            call_id=raw_tool_call.get("id", ""),
            name=raw_tool_call.get("name", ""),
            arguments=parse_json_safe(
                json.dumps(raw_tool_call.get("arguments", {}))
                if isinstance(raw_tool_call.get("arguments"), dict)
                else raw_tool_call.get("arguments", "")
            ),
        )

    # Fallback: assume flattened format
    return ToolCall(
        call_id=raw_tool_call.get("call_id", raw_tool_call.get("id", "")),
        name=raw_tool_call.get("name", ""),
        arguments=parse_json_safe(
            json.dumps(raw_tool_call.get("arguments", {}))
            if isinstance(raw_tool_call.get("arguments"), dict)
            else raw_tool_call.get("arguments", "")
        ),
    )


def extract_tool_calls_from_text(text: str) -> list[ToolCall]:
    """
    Attempt to extract tool calls from text response.

    This is a fallback for when the model returns tool calls as text
    instead of structured data (sometimes happens with lesser models).
    """
    tool_calls: list[ToolCall] = []

    # Look for patterns like: tool_name(...) or [tool_name|{...}]
    patterns = [
        r'(\w+)\s*\(\s*({[^}]*})\s*\)',  # function_name({...})
        r'\[(\w+)\|({[^}]*})\]',  # [function_name|{...}]
        r'"(\w+)"\s*:\s*({[^}]*})',  # "function_name": {...}
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, text, re.DOTALL):
            try:
                tool_name = match.group(1)
                args_str = match.group(2)

                parsed_args = parse_json_safe(args_str)
                if parsed_args:
                    tool_calls.append(
                        ToolCall(
                            call_id=f"fallback_{len(tool_calls)}",
                            name=tool_name,
                            arguments=parsed_args,
                        )
                    )
            except (IndexError, ValueError):
                continue

    return tool_calls
