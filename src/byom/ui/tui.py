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
from byom.config.config import Config
from byom.tools.base import ToolConfirmation
from byom.utils.paths import display_path_rel_to_cwd
import re

from byom.utils.text import truncate_text

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
        self._max_block_tokens = 2500

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
        _PREFERRED_ORDER = {
            "read_file": ["path", "offset", "limit"],
            "write_file": ["path", "create_directories", "content"],
            "edit": ["path", "replace_all", "old_string", "new_string"],
            "shell": ["command", "timeout", "cwd"],
            "list_dir": ["path", "include_hidden"],
            "grep": ["path", "case_insensitive", "pattern"],
            "glob": ["path", "pattern"],
            "todos": ["id", "action", "content"],
            "memory": ["action", "key", "value"],
        }

        preferred = _PREFERRED_ORDER.get(tool_name, [])
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
        self._tool_args_by_call_id[call_id] = arguments
        border_style = f"tool.{tool_kind}" if tool_kind else "tool"

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
                else Text(
                    "(no args)",
                    style="muted",
                )
            ),
            title=title,
            title_align="left",
            subtitle=Text("⏳ running...", style="status.running"),
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
        if not path:
            return "text"
        suffix = Path(path).suffix.lower()
        return {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "jsx",
            ".ts": "typescript",
            ".tsx": "tsx",
            ".json": "json",
            ".toml": "toml",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".md": "markdown",
            ".sh": "bash",
            ".bash": "bash",
            ".zsh": "bash",
            ".rs": "rust",
            ".go": "go",
            ".java": "java",
            ".kt": "kotlin",
            ".swift": "swift",
            ".c": "c",
            ".h": "c",
            ".cpp": "cpp",
            ".hpp": "cpp",
            ".css": "css",
            ".html": "html",
            ".xml": "xml",
            ".sql": "sql",
        }.get(suffix, "text")

    def print_welcome(self, title: str, lines: list[str]) -> None:
        # Create a richer welcome display
        content = []

        for line in lines:
            if line.startswith("version:"):
                content.append(Text(f"📦 {line}", style="info"))
            elif line.startswith("model:"):
                content.append(Text(f"🤖 {line}", style="highlight"))
            elif line.startswith("cwd:"):
                content.append(Text(f"📂 {line}", style="muted"))
            elif line.startswith("commands:"):
                content.append(Text(f"⌨️  {line}", style="dim"))
            else:
                content.append(Text(line, style="code"))

        self.console.print(
            Panel(
                Group(*content),
                title=Text(f"✨ {title}", style="highlight"),
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
                        theme="monokai",
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
                        theme="monokai",
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
                    theme="monokai",
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
                    theme="monokai",
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
                    theme="monokai",
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
                    theme="monokai",
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
                    theme="monokai",
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
                    theme="monokai",
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
                    theme="monokai",
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
                    theme="monokai",
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
                    theme="monokai",
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
                        theme="monokai",
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
                    theme="monokai",
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
        """Display token usage statistics"""
        if not self.config.ui.show_token_usage:
            return

        usage_table = Table.grid(padding=(0, 2))
        usage_table.add_column(style="muted", justify="right")
        usage_table.add_column(style="info")

        usage_table.add_row("📥 Input:", f"{input_tokens:,} tokens")
        usage_table.add_row("📤 Output:", f"{output_tokens:,} tokens")
        usage_table.add_row("📊 Total:", f"{total_tokens:,} tokens")

        self.console.print(
            Panel(
                usage_table,
                title=Text("💰 Token Usage", style="muted"),
                title_align="left",
                border_style="dim",
                box=box.ROUNDED,
                padding=(0, 1),
            )
        )

    def show_help(self) -> None:
        help_text = """
# 📚 BYOM AI Agents - Help

## 🎮 Basic Commands

| Command | Description |
|---------|-------------|
| `/help` | Show this help message |
| `/exit` or `/quit` | Exit the agent |
| `/clear` | Clear conversation history |

## ⚙️  Configuration

| Command | Description |
|---------|-------------|
| `/config` | Show current configuration |
| `/model <name>` | Change the model |
| `/approval <mode>` | Change approval mode (auto/on-request/never) |

## 📊 Information

| Command | Description |
|---------|-------------|
| `/stats` | Show session statistics |
| `/tools` | List available tools |
| `/mcp` | Show MCP server status |

## 💾 Session Management

| Command | Description |
|---------|-------------|
| `/save` | Save current session |
| `/sessions` | List saved sessions |
| `/resume <session_id>` | Resume a saved session |
| `/checkpoint` | Create a checkpoint |
| `/restore <checkpoint_id>` | Restore a checkpoint |

## 💡 Tips

- 💬 **Chat**: Just type your message to interact with the agent
- 🔧 **Tools**: The agent has access to file operations, shell commands, and more
- ✅ **Approval**: Some operations may require approval (configurable with `/approval`)
- 📝 **Context**: The agent maintains conversation context automatically
- 🎯 **Specific**: Be specific in your requests for better results

## 🚀 Quick Start Examples

```bash
# Ask the agent to read a file
What's in src/main.py?

# Request code changes
Add error handling to the login function

# Run shell commands
Run the tests and show me the results
```
"""
        self.console.print()
        self.console.print(Markdown(help_text))
        self.console.print()
