from pathlib import Path
from typing import Any
from rich.console import Console
from rich.theme import Theme
from rich.rule import Rule
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.prompt import Prompt
from rich.console import Group
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.progress import Progress, BarColumn, TextColumn, SpinnerColumn
import re

from byom.config.config import Config
from byom.tools.base import ToolConfirmation
from byom.utils.paths import display_path_rel_to_cwd
from byom.utils.text import truncate_text
from byom.ui.constants import (
    ICONS,
    MESSAGES,
    LANGUAGE_MAP,
    TOOL_ARG_ORDER,
    SYNTAX_THEME,
    MAX_BLOCK_TOKENS,
    SHORTCUTS,
)

AGENT_THEME = Theme(
    {
        # General
        "info": "dodger_blue2",
        "warning": "yellow1",
        "error": "red1 bold",
        "success": "green3 bold",
        "dim": "grey50",
        "muted": "grey58",
        "border": "grey42",
        "highlight": "bold bright_cyan",
        # Roles
        "user": "bright_blue bold",
        "assistant": "bright_white",
        "assistant.header": "bright_cyan bold",
        # Tools
        "tool": "magenta bold",
        "tool.read": "cyan",
        "tool.write": "yellow1",
        "tool.shell": "medium_purple1",
        "tool.network": "dodger_blue1",
        "tool.memory": "green3",
        "tool.mcp": "bright_cyan",
        # Code / blocks
        "code": "grey93",
        # Status
        "status.running": "yellow1",
        "status.done": "green3",
        "status.failed": "red1",
    }
)

_console: Console | None = None


def get_console() -> Console:
    global _console
    if _console is None:
        _console = Console(theme=AGENT_THEME, highlight=False)

    return _console


class TUI:
    def __init__(
        self,
        config: Config,
        console: Console | None = None,
    ) -> None:
        self.console = console or get_console()
        self._assistant_stream_open = False
        self._tool_args_by_call_id: dict[str, dict[str, Any]] = {}
        self.config = config
        self.cwd = self.config.cwd
        self._max_block_tokens = MAX_BLOCK_TOKENS

    def begin_assistant(self) -> None:
        self.console.print()
        self.console.print(
            Rule(
                Text("🤖 Assistant", style="assistant.header"),
                style="border",
            )
        )
        self._assistant_stream_open = True

    def end_assistant(self) -> None:
        if self._assistant_stream_open:
            self.console.print()
            self.console.print()
        self._assistant_stream_open = False

    def stream_assistant_delta(self, content: str) -> None:
        self.console.print(content, end="", markup=False)

    def _ordered_args(self, tool_name: str, args: dict[str, Any]) -> list[tuple]:
        """Order tool arguments for display based on importance."""
        preferred = TOOL_ARG_ORDER.get(tool_name, [])
        ordered: list[tuple[str, Any]] = []
        seen = set()

        for key in preferred:
            if key in args:
                ordered.append((key, args[key]))
                seen.add(key)

        remaining_keys = set(args.keys() - seen)
        ordered.extend((key, args[key]) for key in remaining_keys)

        return ordered

    def _render_args_table(self, tool_name: str, args: dict[str, Any]) -> Table:
        table = Table.grid(padding=(0, 1))
        table.add_column(style="muted", justify="right", no_wrap=True)
        table.add_column(style="code", overflow="fold")

        for key, value in self._ordered_args(tool_name, args):
            if isinstance(value, str):
                if key in {"content", "old_string", "new_string"}:
                    line_count = len(value.splitlines()) or 0
                    byte_count = len(value.encode("utf-8", errors="replace"))
                    value = f"<{line_count} lines • {byte_count} bytes>"

            if isinstance(value, bool):
                value = str(value)
            else:
                value = str(value)

            table.add_row(key, value)

        return table

    def tool_call_start(
        self,
        call_id: str,
        name: str,
        tool_kind: str | None,
        arguments: dict[str, Any],
    ) -> None:
        """Display tool call start with enhanced visuals."""
        self._tool_args_by_call_id[call_id] = arguments
        border_style = f"tool.{tool_kind}" if tool_kind else "tool"

        # Get icon based on tool kind from constants
        icon = ICONS.get(tool_kind, ICONS["tool"])

        title = Text.assemble(
            (f"{icon} ", "tool"),
            (name, "tool"),
            ("  ", "muted"),
            (f"#{call_id[:8]}", "muted"),
        )

        display_args = dict(arguments)
        for key in ("path", "cwd"):
            val = display_args.get(key)
            if isinstance(val, str) and self.cwd:
                display_args[key] = str(display_path_rel_to_cwd(val, self.cwd))

        panel = Panel(
            (
                self._render_args_table(name, display_args)
                if display_args
                else Text(MESSAGES["no_args"], style="muted")
            ),
            title=title,
            title_align="left",
            subtitle=Text(f"{ICONS['running']} running...", style="status.running"),
            subtitle_align="right",
            border_style=border_style,
            box=box.ROUNDED,
            padding=(1, 2),
        )
        self.console.print()
        self.console.print(panel)

    def _extract_read_file_code(self, text: str) -> tuple[int, str] | None:
        body = text
        header_match = re.match(r"^Showing lines (\d+)-(\d+) of (\d+)\n\n", text)

        if header_match:
            body = text[header_match.end() :]

        code_lines: list[str] = []
        start_line: int | None = None

        for line in body.splitlines():
            # 1|def main():
            # 2| print()
            m = re.match(r"^\s*(\d+)\|(.*)$", line)
            if not m:
                return None
            line_no = int(m.group(1))
            if start_line is None:
                start_line = line_no
            code_lines.append(m.group(2))

        if start_line is None:
            return None

        return start_line, "\n".join(code_lines)

    def _guess_language(self, path: str | None) -> str:
        """Guess programming language from file extension."""
        if not path:
            return "text"
        suffix = Path(path).suffix.lower()
        return LANGUAGE_MAP.get(suffix, "text")

    def print_welcome(self, title: str, lines: list[str]) -> None:
        """Display enhanced welcome message with shortcuts."""
        # Create a richer welcome display
        content = []

        for line in lines:
            if line.startswith("version:"):
                content.append(Text(f"{ICONS['version']} {line}", style="info"))
            elif line.startswith("model:"):
                content.append(Text(f"{ICONS['model']} {line}", style="highlight"))
            elif line.startswith("cwd:"):
                content.append(Text(f"{ICONS['cwd']} {line}", style="muted"))
            elif line.startswith("commands:"):
                content.append(Text(f"{ICONS['commands']} {line}", style="dim"))
            else:
                content.append(Text(line, style="code"))

        # Add keyboard shortcuts hint
        content.append(Text())  # Empty line
        shortcuts_text = Text("💡 Shortcuts: ", style="dim")
        shortcuts_text.append("Tab", style="shortcut.key")
        shortcuts_text.append(" autocomplete  ", style="dim")
        shortcuts_text.append("@", style="shortcut.key")
        shortcuts_text.append(" files  ", style="dim")
        shortcuts_text.append("/", style="shortcut.key")
        shortcuts_text.append(" commands", style="dim")
        content.append(shortcuts_text)

        self.console.print(
            Panel(
                Group(*content),
                title=Text(f"{ICONS['welcome']} {title}", style="highlight"),
                title_align="left",
                subtitle=Text("Type your message or /help for commands", style="muted"),
                subtitle_align="right",
                border_style="highlight",
                box=box.DOUBLE,
                padding=(1, 2),
            )
        )
        self.console.print()

    def tool_call_complete(
        self,
        call_id: str,
        name: str,
        tool_kind: str | None,
        success: bool,
        output: str,
        error: str | None,
        metadata: dict[str, Any] | None,
        diff: str | None,
        truncated: bool,
        exit_code: int | None,
    ) -> None:
        border_style = f"tool.{tool_kind}" if tool_kind else "tool"
        status_icon = "✅" if success else "❌"
        status_style = "success" if success else "error"

        # Better icons based on tool kind
        icon_map = {
            "read": "📖",
            "write": "✏️",
            "shell": "⚡",
            "network": "🌐",
            "memory": "💾",
            "mcp": "🔌",
        }
        icon = icon_map.get(tool_kind, "🔧")

        title = Text.assemble(
            (f"{icon} ", "tool"),
            (name, "tool"),
            ("  ", "muted"),
            (f"#{call_id[:8]}", "muted"),
            ("  ", "muted"),
            (f"{status_icon}", status_style),
        )

        args = self._tool_args_by_call_id.get(call_id, {})

        primary_path = None
        blocks = []
        if isinstance(metadata, dict) and isinstance(metadata.get("path"), str):
            primary_path = metadata.get("path")

        if name == "read_file" and success:
            if primary_path:
                start_line, code = self._extract_read_file_code(output)

                shown_start = metadata.get("shown_start")
                shown_end = metadata.get("shown_end")
                total_lines = metadata.get("total_lines")
                pl = self._guess_language(primary_path)

                header_parts = [display_path_rel_to_cwd(primary_path, self.cwd)]
                header_parts.append(" • ")

                if shown_start and shown_end and total_lines:
                    header_parts.append(
                        f"lines {shown_start}-{shown_end} of {total_lines}"
                    )

                header = "".join(header_parts)
                blocks.append(Text(header, style="muted"))
                blocks.append(
                    Syntax(
                        code,
                        pl,
                        theme=SYNTAX_THEME,
                        line_numbers=True,
                        start_line=start_line,
                        word_wrap=False,
                    )
                )
            else:
                output_display = truncate_text(
                    output,
                    "",
                    self._max_block_tokens,
                )
                blocks.append(
                    Syntax(
                        output_display,
                        "text",
                        theme=SYNTAX_THEME,
                        word_wrap=False,
                    )
                )
        elif name in {"write_file", "edit"} and success and diff:
            output_line = output.strip() if output.strip() else "Completed"
            blocks.append(Text(output_line, style="muted"))
            diff_text = diff
            diff_display = truncate_text(
                diff_text,
                self.config.model_name,
                self._max_block_tokens,
            )
            blocks.append(
                Syntax(
                    diff_display,
                    "diff",
                    theme=SYNTAX_THEME,
                    word_wrap=True,
                )
            )
        elif name == "shell" and success:
            command = args.get("command")
            if isinstance(command, str) and command.strip():
                blocks.append(Text(f"$ {command.strip()}", style="muted"))

            if exit_code is not None:
                blocks.append(Text(f"exit_code={exit_code}", style="muted"))

            output_display = truncate_text(
                output,
                self.config.model_name,
                self._max_block_tokens,
            )
            blocks.append(
                Syntax(
                    output_display,
                    "text",
                    theme=SYNTAX_THEME,
                    word_wrap=True,
                )
            )
        elif name == "list_dir" and success:
            entries = metadata.get("entries")
            path = metadata.get("path")
            summary = []
            if isinstance(path, str):
                summary.append(path)

            if isinstance(entries, int):
                summary.append(f"{entries} entries")

            if summary:
                blocks.append(Text(" • ".join(summary), style="muted"))

            output_display = truncate_text(
                output,
                self.config.model_name,
                self._max_block_tokens,
            )
            blocks.append(
                Syntax(
                    output_display,
                    "text",
                    theme=SYNTAX_THEME,
                    word_wrap=True,
                )
            )
        elif name == "grep" and success:
            matches = metadata.get("matches")
            files_searched = metadata.get("files_searched")
            summary = []
            if isinstance(matches, int):
                summary.append(f"{matches} matches")
            if isinstance(files_searched, int):
                summary.append(f"searched {files_searched} files")

            if summary:
                blocks.append(Text(" • ".join(summary), style="muted"))

            output_display = truncate_text(
                output, self.config.model_name, self._max_block_tokens
            )
            blocks.append(
                Syntax(
                    output_display,
                    "text",
                    theme=SYNTAX_THEME,
                    word_wrap=True,
                )
            )
        elif name == "glob" and success:
            matches = metadata.get("matches")
            if isinstance(matches, int):
                blocks.append(Text(f"{matches} matches", style="muted"))

            output_display = truncate_text(
                output,
                self.config.model_name,
                self._max_block_tokens,
            )
            blocks.append(
                Syntax(
                    output_display,
                    "text",
                    theme=SYNTAX_THEME,
                    word_wrap=True,
                )
            )
        elif name == "web_search" and success:
            results = metadata.get("results")
            query = args.get("query")
            summary = []
            if isinstance(query, str):
                summary.append(query)
            if isinstance(results, int):
                summary.append(f"{results} results")

            if summary:
                blocks.append(Text(" • ".join(summary), style="muted"))

            output_display = truncate_text(
                output,
                self.config.model_name,
                self._max_block_tokens,
            )
            blocks.append(
                Syntax(
                    output_display,
                    "text",
                    theme=SYNTAX_THEME,
                    word_wrap=True,
                )
            )
        elif name == "web_fetch" and success:
            status_code = metadata.get("status_code")
            content_length = metadata.get("content_length")
            url = args.get("url")
            summary = []
            if isinstance(status_code, int):
                summary.append(str(status_code))
            if isinstance(content_length, int):
                summary.append(f"{content_length} bytes")
            if isinstance(url, str):
                summary.append(url)

            if summary:
                blocks.append(Text(" • ".join(summary), style="muted"))

            output_display = truncate_text(
                output,
                self.config.model_name,
                self._max_block_tokens,
            )
            blocks.append(
                Syntax(
                    output_display,
                    "text",
                    theme=SYNTAX_THEME,
                    word_wrap=True,
                )
            )
        elif name == "todos" and success:
            output_display = truncate_text(
                output,
                self.config.model_name,
                self._max_block_tokens,
            )
            blocks.append(
                Syntax(
                    output_display,
                    "text",
                    theme=SYNTAX_THEME,
                    word_wrap=True,
                )
            )
        elif name == "memory" and success:
            action = args.get("action")
            key = args.get("key")
            found = metadata.get("found")
            summary = []
            if isinstance(action, str) and action:
                summary.append(action)
            if isinstance(key, str) and key:
                summary.append(key)
            if isinstance(found, bool):
                summary.append("found" if found else "missing")

            if summary:
                blocks.append(Text(" • ".join(summary), style="muted"))
            output_display = truncate_text(
                output,
                self.config.model_name,
                self._max_block_tokens,
            )
            blocks.append(
                Syntax(
                    output_display,
                    "text",
                    theme=SYNTAX_THEME,
                    word_wrap=True,
                )
            )
        else:
            if error and not success:
                blocks.append(Text(error, style="error"))

            output_display = truncate_text(
                output, self.config.model_name, self._max_block_tokens
            )
            if output_display.strip():
                blocks.append(
                    Syntax(
                        output_display,
                        "text",
                        theme=SYNTAX_THEME,
                        word_wrap=True,
                    )
                )
            else:
                blocks.append(Text("(no output)", style="muted"))

        if truncated:
            blocks.append(Text("⚠️  Output was truncated", style="warning"))

        subtitle_text = "✓ done" if success else "✗ failed"
        subtitle_style = "status.done" if success else "status.failed"

        panel = Panel(
            Group(
                *blocks,
            ),
            title=title,
            title_align="left",
            subtitle=Text(subtitle_text, style=subtitle_style),
            subtitle_align="right",
            border_style=border_style,
            box=box.ROUNDED,
            padding=(1, 2),
        )
        self.console.print()
        self.console.print(panel)

    def handle_confirmation(self, confirmation: ToolConfirmation) -> bool:
        output = []

        # Tool header
        output.append(
            Text.assemble(
                ("🔧 Tool: ", "muted"),
                (confirmation.tool_name, "tool"),
            )
        )

        # Action description
        output.append(
            Text.assemble(
                ("📋 Action: ", "muted"),
                (confirmation.description, "code"),
            )
        )

        if confirmation.command:
            output.append(Text(""))
            output.append(
                Text.assemble(
                    ("⚡ Command: ", "warning"),
                    (f"$ {confirmation.command}", "code"),
                )
            )

        if confirmation.diff:
            output.append(Text(""))
            diff_text = confirmation.diff.to_diff()
            output.append(
                Syntax(
                    diff_text,
                    "diff",
                    theme=SYNTAX_THEME,
                    word_wrap=True,
                )
            )

        self.console.print()
        self.console.print(
            Panel(
                Group(*output),
                title=Text("⚠️  Approval Required", style="warning"),
                title_align="left",
                subtitle=Text("y = approve, n = reject", style="muted"),
                subtitle_align="right",
                border_style="warning",
                box=box.HEAVY,
                padding=(1, 2),
            )
        )

        response = Prompt.ask(
            "\n[bold yellow]Approve?[/bold yellow]",
            choices=["y", "n", "yes", "no"],
            default="n",
        )

        return response.lower() in {"y", "yes"}

    def show_token_usage(self, input_tokens: int, output_tokens: int, total_tokens: int) -> None:
        """Display enhanced token usage statistics with visual indicators."""
        if not self.config.ui.show_token_usage:
            return

        # Create a table with better formatting
        usage_table = Table.grid(padding=(0, 2))
        usage_table.add_column(style="stat.label", justify="right", width=12)
        usage_table.add_column(style="stat.value", justify="right", width=15)
        usage_table.add_column(style="dim", width=20)

        # Calculate percentages
        input_pct = (input_tokens / total_tokens * 100) if total_tokens > 0 else 0
        output_pct = (output_tokens / total_tokens * 100) if total_tokens > 0 else 0

        # Create visual bars
        bar_width = 15
        input_bar = "█" * int(input_pct / 100 * bar_width)
        output_bar = "█" * int(output_pct / 100 * bar_width)

        usage_table.add_row(
            f"{ICONS['token']} Input:",
            f"{input_tokens:,}",
            f"[stat.positive]{input_bar}[/] {input_pct:.1f}%"
        )
        usage_table.add_row(
            f"{ICONS['token']} Output:",
            f"{output_tokens:,}",
            f"[stat.neutral]{output_bar}[/] {output_pct:.1f}%"
        )
        usage_table.add_row(
            "",
            "─" * 15,
            ""
        )
        usage_table.add_row(
            f"{ICONS['stats']} Total:",
            f"[bold]{total_tokens:,}[/]",
            ""
        )

        self.console.print(
            Panel(
                usage_table,
                title=Text(f"{ICONS['token']} Token Usage", style="highlight"),
                title_align="left",
                border_style="border",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )

    def show_statistics(
        self,
        turns: int,
        tool_calls: int,
        total_input_tokens: int,
        total_output_tokens: int,
        session_time: float,
    ) -> None:
        """Display comprehensive session statistics dashboard."""
        total_tokens = total_input_tokens + total_output_tokens

        # Create main statistics table
        stats_table = Table.grid(padding=(0, 3))
        stats_table.add_column(style="stat.label", justify="right", width=20)
        stats_table.add_column(style="stat.value", justify="left")

        # Session metrics
        stats_table.add_row(
            f"{ICONS['stats']} Conversation Turns:",
            f"[stat.value]{turns:,}[/]"
        )
        stats_table.add_row(
            f"{ICONS['tool']} Tool Calls:",
            f"[stat.value]{tool_calls:,}[/]"
        )
        stats_table.add_row(
            f"{ICONS['time']} Session Time:",
            f"[stat.value]{session_time:.1f}s[/]"
        )
        stats_table.add_row("", "")  # Spacer

        # Token usage
        stats_table.add_row(
            f"{ICONS['token']} Input Tokens:",
            f"[stat.positive]{total_input_tokens:,}[/]"
        )
        stats_table.add_row(
            f"{ICONS['token']} Output Tokens:",
            f"[stat.neutral]{total_output_tokens:,}[/]"
        )
        stats_table.add_row(
            f"{ICONS['stats']} Total Tokens:",
            f"[bold bright_white]{total_tokens:,}[/]"
        )

        # Calculate averages if we have turns
        if turns > 0:
            avg_tokens_per_turn = total_tokens / turns
            stats_table.add_row("", "")  # Spacer
            stats_table.add_row(
                "📊 Avg Tokens/Turn:",
                f"[stat.value]{avg_tokens_per_turn:,.1f}[/]"
            )

        self.console.print()
        self.console.print(
            Panel(
                stats_table,
                title=Text(f"{ICONS['stats']} Session Statistics", style="highlight"),
                title_align="left",
                subtitle=Text("Current session metrics", style="muted"),
                subtitle_align="right",
                border_style="highlight",
                box=box.DOUBLE,
                padding=(1, 2),
            )
        )
        self.console.print()

    def show_help(self) -> None:
        """Display enhanced help with keyboard shortcuts and examples."""
        help_text = f"""
# {ICONS['help']} BYOM AI Agents - Help

## 🎮 Basic Commands

| Command | Description |
|---------|-------------|
| `/help` | Show this help message |
| `/stats` | Show session statistics dashboard |
| `/config` | Display current configuration |
| `/model <name>` | Change the active model |
| `/approval <mode>` | Set approval policy (auto/on-request/never) |
| `/exit` or `/quit` | Exit the application |

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Tab` | Trigger autocomplete |
| `Shift+Tab` | Navigate completions backward |
| `@` | Autocomplete file paths |
| `/` | Autocomplete slash commands |
| `Ctrl+C` | Interrupt current operation |
| `Ctrl+D` | Exit (EOF) |
| `↑/↓` | Navigate through completions |

## 🚀 Quick Start Examples

```bash
# Ask the agent to read a file
What's in src/main.py?

# Reference files with @ autocomplete
Please review @src/config.py and suggest improvements

# Request code changes
Add error handling to the login function

# Run shell commands
Run the tests and show me the results

# Use slash commands
/stats          # View session statistics
/config         # Check current configuration
/model gpt-4    # Switch to a different model
```

## 💡 Tips

- Use `@` to trigger file path autocomplete
- Use `/` to see available slash commands
- Session statistics are available with `/stats`
- Press `Tab` for intelligent code/path suggestions
- All file paths are shown relative to your working directory

## 📊 Features

- **Smart Autocomplete**: File paths and commands
- **Token Usage Tracking**: Monitor your API usage
- **Session Statistics**: View turns, tool calls, and metrics
- **Approval Policies**: Control what actions require confirmation
- **MCP Integration**: Connect to Model Context Protocol servers
"""
        self.console.print()
        self.console.print(Markdown(help_text))
        self.console.print()
