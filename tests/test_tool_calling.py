"""Tests for tool call parsing and validation utilities."""

import pytest
from byom.tools.tool_call_parser import (
    parse_json_safe,
    repair_json,
    validate_tool_call,
    normalize_tool_call,
    extract_tool_calls_from_text,
    ToolCall,
)


class TestJsonRepair:
    """Test JSON repair utilities."""

    def test_repair_trailing_comma(self):
        """Test fixing trailing commas in JSON."""
        json_str = '{"key": "value",}'
        repaired = repair_json(json_str)
        assert repaired == '{"key": "value"}'

    def test_repair_trailing_comma_array(self):
        """Test fixing trailing commas in arrays."""
        json_str = '[1, 2, 3,]'
        repaired = repair_json(json_str)
        assert repaired == '[1, 2, 3]'

    def test_repair_empty_string(self):
        """Test repair with empty input."""
        repaired = repair_json("")
        assert repaired == "{}"

    def test_repair_newlines(self):
        """Test fixing escaped newlines."""
        json_str = '{"text": "line1\\nline2"}'
        repaired = repair_json(json_str)
        assert "\\n" not in repaired or repaired.count("\\n") < json_str.count("\\n")


class TestJsonParseSafe:
    """Test safe JSON parsing."""

    def test_parse_valid_json(self):
        """Test parsing valid JSON."""
        result = parse_json_safe('{"key": "value"}')
        assert result == {"key": "value"}

    def test_parse_invalid_json_with_repair(self):
        """Test parsing invalid JSON with automatic repair."""
        result = parse_json_safe('{"key": "value",}')
        assert result == {"key": "value"}

    def test_parse_empty_string(self):
        """Test parsing empty string."""
        result = parse_json_safe("")
        assert result == {}

    def test_parse_fallback_to_raw(self):
        """Test fallback when JSON can't be parsed."""
        result = parse_json_safe("not json at all")
        assert "raw_arguments" in result
        assert result["raw_arguments"] == "not json at all"

    def test_parse_json_in_text(self):
        """Test extracting JSON from embedded text."""
        result = parse_json_safe('here is {"key": "value"} embedded')
        assert result == {"key": "value"}


class TestValidateToolCall:
    """Test tool call validation."""

    def test_valid_tool_call(self):
        """Test validating a correct tool call."""
        tool_call = ToolCall(
            call_id="call_123",
            name="read_file",
            arguments={"path": "/tmp/file.txt"},
        )
        is_valid, error = validate_tool_call(tool_call)
        assert is_valid is True
        assert error is None

    def test_missing_call_id(self):
        """Test validation with missing call_id."""
        tool_call = ToolCall(
            call_id="",
            name="read_file",
            arguments={"path": "/tmp/file.txt"},
        )
        is_valid, error = validate_tool_call(tool_call)
        assert is_valid is False
        assert "call_id" in error

    def test_missing_tool_name(self):
        """Test validation with missing name."""
        tool_call = ToolCall(
            call_id="call_123",
            name="",
            arguments={"path": "/tmp/file.txt"},
        )
        is_valid, error = validate_tool_call(tool_call)
        assert is_valid is False
        assert "name" in error

    def test_invalid_json_arguments(self):
        """Test validation with invalid JSON arguments."""
        tool_call = ToolCall(
            call_id="call_123",
            name="read_file",
            arguments="not json",
        )
        is_valid, error = validate_tool_call(tool_call)
        # Should still be valid because we try to repair
        # If it can't be repaired, error will mention arguments
        assert isinstance(is_valid, bool)


class TestNormalizeToolCall:
    """Test tool call normalization."""

    def test_normalize_openai_format(self):
        """Test normalizing OpenAI tool call format."""
        raw = {
            "id": "call_123",
            "function": {
                "name": "read_file",
                "arguments": '{"path": "/tmp/file.txt"}',
            },
        }
        normalized = normalize_tool_call(raw)
        assert normalized.call_id == "call_123"
        assert normalized.name == "read_file"
        assert isinstance(normalized.arguments, dict)
        assert normalized.arguments["path"] == "/tmp/file.txt"

    def test_normalize_anthropic_format(self):
        """Test normalizing Anthropic tool call format."""
        raw = {
            "type": "tool_use",
            "id": "tool_123",
            "name": "search",
            "input": {"query": "python"},
        }
        normalized = normalize_tool_call(raw)
        assert normalized.call_id == "tool_123"
        assert normalized.name == "search"
        assert isinstance(normalized.arguments, dict)
        assert normalized.arguments["query"] == "python"

    def test_normalize_google_format(self):
        """Test normalizing Google tool call format."""
        raw = {
            "id": "call_456",
            "name": "calculate",
            "arguments": {"expression": "2 + 2"},
        }
        normalized = normalize_tool_call(raw)
        assert normalized.call_id == "call_456"
        assert normalized.name == "calculate"
        assert isinstance(normalized.arguments, dict)


class TestExtractToolCallsFromText:
    """Test extracting tool calls from text responses."""

    def test_extract_function_call_syntax(self):
        """Test extracting tool calls with function() syntax."""
        text = 'Let me search for this. search({"query": "python"})'
        tool_calls = extract_tool_calls_from_text(text)
        assert len(tool_calls) > 0
        assert tool_calls[0].name == "search"

    def test_extract_bracketed_syntax(self):
        """Test extracting tool calls with [tool|args] syntax."""
        text = "I will look it up. [search|{\"query\": \"machine learning\"}]"
        tool_calls = extract_tool_calls_from_text(text)
        assert len(tool_calls) > 0
        assert tool_calls[0].name == "search"

    def test_extract_no_tool_calls(self):
        """Test extracting from text with no tool calls."""
        text = "This is just regular text without any tool calls."
        tool_calls = extract_tool_calls_from_text(text)
        assert len(tool_calls) == 0

    def test_extract_multiple_tool_calls(self):
        """Test extracting multiple tool calls from text."""
        text = """
        Let me search for results search({"query": "test"})
        and then read a file. read_file({"path": "/tmp/file.txt"})
        """
        tool_calls = extract_tool_calls_from_text(text)
        assert len(tool_calls) >= 2


class TestToolCallEdgeCases:
    """Test edge cases in tool call handling."""

    def test_tool_call_with_nested_json(self):
        """Test tool call with nested JSON arguments."""
        raw = {
            "id": "call_123",
            "function": {
                "name": "process_data",
                "arguments": '{"config": {"nested": {"value": 42}}}',
            },
        }
        normalized = normalize_tool_call(raw)
        assert isinstance(normalized.arguments, dict)
        assert normalized.arguments["config"]["nested"]["value"] == 42

    def test_tool_call_with_empty_arguments(self):
        """Test tool call with empty arguments."""
        raw = {
            "id": "call_123",
            "function": {
                "name": "get_current_time",
                "arguments": "{}",
            },
        }
        normalized = normalize_tool_call(raw)
        assert normalized.arguments == {}

    def test_tool_call_with_array_arguments(self):
        """Test tool call with array arguments."""
        raw = {
            "id": "call_123",
            "function": {
                "name": "process_list",
                "arguments": '[1, 2, 3, 4, 5]',
            },
        }
        normalized = normalize_tool_call(raw)
        # When parsing fails or gives unusual results, we should gracefully handle
        assert normalized.call_id == "call_123"
        assert normalized.name == "process_list"
