from typing import List
from tools.base import Tool
from tools.builtin.read_file import ReadFileTool
from tools.builtin.write_file import WriteFileTool
from tools.builtin.edit_file import EditTool
from tools.builtin.shell import ShellTool

__all__ = [
    'ReadFileTool',
    'WriteFileTool',
    "EditTool",
    "ShellTool"
]


def get_all_buildin_tools() -> List[Tool]:
    return [
        ReadFileTool,
        WriteFileTool,
        EditTool,
        ShellTool
    ]