from pathlib import Path
from typing import Any
from rich.console import Console, Group
from rich.theme import Theme
from rich.rule import Rule
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich import box
from configs.configs import Config
from utils.paths import display_path_rel_to_cwd
from rich.syntax import Syntax
import re

from utils.text import truncate_text

AGENT_THEME = Theme(
    {
        # General
        "info": "cyan",
        "warning": "yellow",
        "error": "bright_red bold",
        "success": "green",
        "dim": "dim",
        "muted": "grey50",
        "border": "grey35",
        "highlight": "bold cyan",
        # Roles
        "user": "bright_blue bold",
        "assistant": "bright_white",
        # Tools
        "tool": "bright_magenta bold",
        "tool.read": "cyan",
        "tool.write": "yellow",
        "tool.shell": "magenta",
        "tool.network": "bright_blue",
        "tool.memory": "green",
        "tool.mcp": "bright_cyan",
        # Code / blocks
        "code": "white",
    }
)

_console : Console | None = None

def get_console() -> Console:
    global _console
    if _console is None:
        _console = Console(theme=AGENT_THEME, highlight=False, force_terminal=True, color_system="auto")
    return _console


class TUI:
    def __init__(self, config: Config, console: Console | None = None, model_name: str = "gpt-3.5-turbo") -> None:
        self.console = console or Console()
        self.config = config
        self._assistance_stream_open = False
        self._tool_args_by_call_id: dict[str, dict[str, Any]] = {}
        self.cwd = self.config.cwd
        self._max_block_tokens = 2500
        self.model_name = model_name


    def stream_assistant_delta(self, content: str) -> None:
        self.console.print(content, end="", markup=False)


    def begin_assistance(self) -> None:
        self.console.print()
        self.console.print(Rule(Text("Assistance", style="assistant")))
        self._assistance_stream_open = True

    def end_assistance(self) -> None:
        if self._assistance_stream_open:
            self.console.print()
        self._assistance_stream_open = False

    def _ordered_args(self, tool_name: str, args: dict[str, Any]) -> list[tuple]:
        _PREFERED_ORDER = {
            "read_file" : ['path', 'offset', 'limit'],
            'write_file' : ['path', 'create_directories', 'content'],
            "edit_file" : ['path', 'replace_all', 'old_string', 'new_string'],
            "shell" : ['command', 'timeout', 'cwd'],
            "list_dir" : ['path', 'include_hidden']
        }
        preferred = _PREFERED_ORDER.get(tool_name, [])
        ordered : list[tuple[str, Any]] = []
        seen = set()
        for key in preferred:
            if key in args:
                ordered.append((key, args[key]))
                seen.add(key)

        remaining_keys = set(args.keys() - seen)
        ordered.extend((key, args[key]) for key in remaining_keys)
        return ordered


    def _render_args_table(self, tool_name: str, arguments: dict[str, Any]) -> Table:
        table = Table.grid(padding=(0, 1))
        table.add_column(style="muted", justify="right", no_wrap=True)
        table.add_column(style="code", overflow="fold")
        for key, value in self._ordered_args(tool_name, arguments):
            if isinstance(value, str):
                if key in {'content', 'old_string', 'new_string'}:
                    line_count = len(value.splitlines()) or 0
                    byte_count = len(value.encode('utf-8', errors='replace'))
                    value = f"<{line_count}> lines * {byte_count} bytes"
            table.add_row(key, value)
        return table


    def tool_call_start(self, call_id: str, tool_name: str, tool_kind: str | None, arguments: dict[str, Any],) -> None:
        self._tool_args_by_call_id[call_id] = arguments
        border_style = f"tool.{tool_kind}" if tool_kind else "tool"
        title = Text.assemble(
            ("*", "muted"),
            (tool_name, "tool"),
            ("  ", "muted"),
            (f"#{call_id[:8]}", "muted")
        )
        display_arguments = dict(arguments)
        for key in ('path', 'cwd'):
            val = display_arguments.get(key)
            if isinstance(val, str) and self.cwd:
                display_arguments[key] = str(display_path_rel_to_cwd(val, self.cwd))

        panel = Panel(
            self._render_args_table(tool_name, arguments) if display_arguments else Text('(no args)', style="muted"),
            title=title,
            box = box.ROUNDED,
            border_style=border_style,
            padding=(1, 2),
            subtitle=Text('runnning', style="muted"),
            title_align='left',
            subtitle_align='right'
        )
        self.console.print()
        self.console.print(panel)

    def _extract_read_file_code(self, text: str) -> tuple[int, str] | None:
        body = text
        header_match = re.match(r"^Showing lines (\d+)-(\d+) of (\d+)\n\n", text)
        if header_match:
            body = text[header_match.end() :]
        code_lines : list[str] = []
        start_lines: int | None = None
        for line in body.splitlines():
            m = re.match(r"^\s*(\d+)\s*\|(.*)$", line)
            if not m:
                return None
            line_no = int(m.group(1))
            if start_lines is None:
                start_lines = line_no
            code_lines.append(m.group(2))
        if start_lines is None:
            return None
        return start_lines, "\n".join(code_lines)

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
        body = "\n".join(lines)
        self.console.print(
            Panel(
                Text(body, style="code"),
                title=Text(title, style="highlight"),
                title_align="left",
                border_style="border",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )

    def tool_call_complete(
        self,
        call_id: str,
        tool_name: str,
        tool_kind : str,
        success: bool,
        output: str, error : str | None,
        metadata: dict[str, Any],
        diff : str | None,
        truncated: bool,
        exit_code : int | None
    ) -> None:
        border_style = f"tool.{tool_kind}" if tool_kind else "tool"
        status_icon = '✓ ' if success else '✕ '
        status_style = 'success' if success else 'error'

        title = Text.assemble(
            (f"{status_icon}", status_style),
            (tool_name, "tool"),
            ("  ", "muted"),
            (f"#{call_id[:8]}", "muted")
        )
        args = self._tool_args_by_call_id.get("call_id", {})
        primary_path = None
        blocks = []
        if isinstance(metadata, dict) and isinstance(metadata.get("path"), str):
            primary_path = metadata.get("path")

        if tool_name == "read_file" and success:
            if primary_path:
                extracted = self._extract_read_file_code(output)

                if extracted:
                    start_line, code = extracted
                    shown_start = metadata.get("shown_start")
                    shown_end = metadata.get("shown_end")
                    total_lines = metadata.get("total_lines")
                    pl = self._guess_language(primary_path)

                    header_parts = [display_path_rel_to_cwd(primary_path, self.cwd)]
                    header_parts.append(" * ")

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
                    # Fallback if extraction fails - still try to show with highlighting
                    # print(f"[DEBUG] Extraction failed, showing raw output")
                    output_display = truncate_text(
                        output,
                        self.model_name,
                        self._max_block_tokens,
                    )
                    pl = self._guess_language(primary_path)
                    blocks.append(
                        Syntax(
                            output_display,
                            pl,
                            theme="monokai",
                            word_wrap=False,
                            line_numbers=False,
                        )
                    )
            else:
                output_display = truncate_text(
                    output,
                    self.model_name,
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
        elif tool_name in {"write_file", "edit"} and success and diff:
            output_line = output.strip() if output.strip() else "Completed"
            blocks.append(Text(output_line, style="muted"))
            diff_text = diff
            diff_display = truncate_text(
                diff_text,
                self.config.model_name,
                self._max_block_tokens
            )
            blocks.append(
                Syntax(
                    diff_display,
                    "diff",
                    theme="monokai",
                    word_wrap=True
                )
            )
        elif tool_name == "shell" and success:
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
        elif tool_name == "list_dir" and success:
            entries = metadata.get("entries")
            path = metadata.get("path")
            summary = []
            if isinstance(path, str):
                summary.append(path)
            
            if isinstance(entries, int):
                summary.append(f"{entries} entries")

            if summary:
                blocks.append(Text(" * ".join(summary), ))
        else:
            if error and not success:
                blocks.append(Text(error, style="error"))

            output_display = truncate_text(
                output, self.model_name, self._max_block_tokens
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
            blocks.append(Text("note: tool output was truncated", style="warning"))

        panel = Panel(
            Group(
                *blocks,
            ),
            title=title,
            title_align="left",
            subtitle=Text("done" if success else "failed", style=status_style),
            subtitle_align="right",
            border_style=border_style,
            box=box.ROUNDED,
            padding=(1, 2),
        )
        self.console.print()
        self.console.print(panel)


