from typing import List
from tools.base import Tool
from tools.builtin.read_file import ReadFileTool

__all__ = [
    'ReadFileTool'
]


def get_all_buildin_tools() -> List[Tool]:
    return [
        ReadFileTool
    ]