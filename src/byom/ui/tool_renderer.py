"""
Tool call rendering utilities for enhanced UI display.

Provides specialized rendering for different tool types with support for
compact and detailed modes.
"""

from __future__ import annotations

import json
from typing import Any

from rich.console import Group
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from byom.ui.constants import ICONS, LANGUAGE_MAP, SYNTAX_THEME, MAX_BLOCK_TOKENS
from byom.utils.paths import display_path_rel_to_cwd
from byom.utils.text import truncate_text


class ToolRenderer:
    """Renders tool calls with intelligent formatting and truncation."""

    def __init__(self, cwd: str | None = None, max_tokens: int = MAX_BLOCK_TOKENS):
        """Initialize tool renderer."""
        self.cwd = cwd
        self.max_tokens = max_tokens

    def render_tool_header(
        self,
        call_id: str,
        name: str,
        tool_kind: str | None,
        status: str = "running",
    ) -> Text:
        """Render tool call header with icon and ID."""
        icon = ICONS.get(tool_kind, ICONS.get("tool", "🔧"))
        status_icon = "⏳" if status == "running" else "✅" if status == "success" else "❌"

        header = Text.assemble(
            (f"{icon} ", "tool"),
            (name, "tool"),
            ("  ", "muted"),
            (f"#{call_id[:8]}", "muted"),
            ("  ", "muted"),
            (status_icon, "status.done" if status == "success" else "status.running" if status == "running" else "status.failed"),
        )
        return header

    def render_compact_args(self, tool_name: str, args: dict[str, Any], max_length: int = 100) -> str:
        """Render arguments in compact form."""
        if not args:
            return "(no args)"

        # Priority args for display
        priority_keys = self._get_priority_keys(tool_name)
        display_parts = []

        # Add priority args first
        for key in priority_keys:
            if key in args:
                val = args[key]
                display_parts.append(self._format_arg_value(key, val, max_length=30))

        # Add remaining args (non-verbose)
        remaining = set(args.keys()) - set(priority_keys)
        for key in sorted(remaining):
            if key not in {"content", "old_string", "new_string"}:  # Skip verbose fields
                val = args[key]
                display_parts.append(self._format_arg_value(key, val, max_length=20))

        return " | ".join(display_parts[:4])  # Show max 4 args

    def render_detailed_args(self, tool_name: str, args: dict[str, Any]) -> Table:
        """Render full argument table."""
        table = Table.grid(padding=(0, 1))
        table.add_column(style="muted", justify="right", no_wrap=True, width=20)
        table.add_column(style="code", overflow="fold")

        for key in self._ordered_keys(tool_name, args.keys()):
            value = args[key]

            # Special handling for large text fields
            if isinstance(value, str):
                if key in {"content", "old_string", "new_string"}:
                    line_count = len(value.splitlines()) or 0
                    byte_count = len(value.encode("utf-8", errors="replace"))
                    value = f"<{line_count} lines • {byte_count} bytes>"
                elif len(value) > 60:
                    value = value[:60] + "..."

            table.add_row(str(key), str(value))

        return table

    def render_output(self, output: str, tool_name: str, language: str | None = None) -> Syntax:
        """Render tool output with syntax highlighting."""
        displayed = truncate_text(
            output,
            "",  # No model name needed for context
            self.max_tokens,
        )

        # Guess language from tool type if not provided
        if not language:
            language = self._guess_language(tool_name)

        return Syntax(
            displayed,
            language,
            theme=SYNTAX_THEME,
            word_wrap=True,
            line_numbers=language != "text",
        )

    def render_diff(self, diff_text: str) -> Syntax:
        """Render a diff with syntax highlighting."""
        displayed = truncate_text(diff_text, "", self.max_tokens)
        return Syntax(
            displayed,
            "diff",
            theme=SYNTAX_THEME,
            word_wrap=True,
        )

    def render_summary(self, parts: list[str]) -> Text:
        """Render a summary line from parts."""
        return Text(" • ".join(parts), style="muted")

    @staticmethod
    def _get_priority_keys(tool_name: str) -> list[str]:
        """Get priority keys for a tool type."""
        priority_map = {
            "read_file": ["path"],
            "write_file": ["path"],
            "edit_file": ["path"],
            "edit": ["path"],
            "shell": ["command"],
            "grep": ["pattern"],
            "glob": ["pattern"],
            "web_search": ["query"],
            "web_fetch": ["url"],
            "list_dir": ["path"],
        }
        return priority_map.get(tool_name, [])

    @staticmethod
    def _ordered_keys(tool_name: str, keys) -> list[str]:
        """Get ordered list of keys by priority."""
        priority = ToolRenderer._get_priority_keys(tool_name)
        ordered = []
        seen = set()

        # Add priority keys first
        for key in priority:
            if key in keys:
                ordered.append(key)
                seen.add(key)

        # Add remaining keys
        for key in sorted(set(keys) - seen):
            ordered.append(key)

        return ordered

    @staticmethod
    def _format_arg_value(key: str, value: Any, max_length: int = 30) -> str:
        """Format a single argument for compact display."""
        if isinstance(value, bool):
            return f"{key}={str(value).lower()}"
        elif isinstance(value, (int, float)):
            return f"{key}={value}"
        elif isinstance(value, str):
            if len(value) > max_length:
                return f"{key}={value[:max_length]}..."
            return f"{key}={value}"
        elif isinstance(value, dict):
            return f"{key}={{...}}"
        elif isinstance(value, list):
            return f"{key}=[...]"
        else:
            return f"{key}={type(value).__name__}"

    @staticmethod
    def _guess_language(tool_name: str) -> str:
        """Guess output language based on tool type."""
        language_map = {
            "shell": "bash",
            "python": "python",
            "javascript": "javascript",
            "json": "json",
            "grep": "text",
            "list_dir": "text",
            "read_file": "text",  # Will be overridden by file extension
        }
        return language_map.get(tool_name, "text")
