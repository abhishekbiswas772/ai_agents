from typing import List
from tools.base import Tool
from tools.builtin.read_file import ReadFileTool
from tools.builtin.write_file import WriteFileTool
from tools.builtin.edit_file import EditTool
from tools.builtin.shell import ShellTool
from tools.builtin.list_dir import ListDirTool
from tools.builtin.glob import GlobTool
from tools.builtin.grep import GrepTool
from tools.builtin.web_fetch import WebFetchTool
from tools.builtin.web_search import WebSearchTool
from tools.builtin.memory import MemoryTool
from tools.builtin.todo import TodosTool

__all__ = [
    'ReadFileTool',
    'WriteFileTool',
    "EditTool",
    "ShellTool",
    "GrepTool",
    "GlobTool",
    "ListDirTool",
    "WebFetchTool",
    "WebSearchTool",
    "MemoryTool",
    "TodosTool"
]


def get_all_buildin_tools() -> List[Tool]:
    return [
        ReadFileTool,
        WriteFileTool,
        EditTool,
        ShellTool,
        GrepTool,
        GlobTool,
        ListDirTool,
        WebFetchTool,
        WebSearchTool,
        TodosTool,
        MemoryTool
    ]
