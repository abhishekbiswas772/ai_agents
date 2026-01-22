from byom.tools.builtin.edit_file import EditTool
from byom.tools.builtin.find import FindTool
from byom.tools.builtin.glob import GlobTool
from byom.tools.builtin.grep import GrepTool
from byom.tools.builtin.list_dir import ListDirTool
from byom.tools.builtin.memory import MemoryTool
from byom.tools.builtin.read_file import ReadFileTool
from byom.tools.builtin.shell import ShellTool
from byom.tools.builtin.todo import TodosTool
from byom.tools.builtin.web_fetch import WebFetchTool
from byom.tools.builtin.web_search import WebSearchTool
from byom.tools.builtin.write_file import WriteFileTool

__all__ = [
    "ReadFileTool",
    "WriteFileTool",
    "EditTool",
    "ShellTool",
    "ListDirTool",
    "GrepTool",
    "GlobTool",
    "FindTool",
    "WebSearchTool",
    "WebFetchTool",
    "TodosTool",
    "MemoryTool",
]


def get_all_builtin_tools() -> list[type]:
    return [
        ReadFileTool,
        WriteFileTool,
        EditTool,
        ShellTool,
        ListDirTool,
        GrepTool,
        GlobTool,
        FindTool,
        WebSearchTool,
        WebFetchTool,
        TodosTool,
        MemoryTool,
    ]
