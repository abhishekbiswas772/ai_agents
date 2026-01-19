from typing import List
from tools.base import Tool
from tools.builtin.read_file import ReadFileTool
from tools.builtin.write_file import WriteFileTool

__all__ = [
    'ReadFileTool',
    'WriteFileTool'
]


def get_all_buildin_tools() -> List[Tool]:
    return [
        ReadFileTool,
        WriteFileTool
    ]