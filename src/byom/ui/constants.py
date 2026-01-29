"""
UI Constants and Configuration

Centralized constants for UI elements, icons, and magic strings.
"""

# ═══════════════════════════════════════════════════════════════
# ICONS AND EMOJIS
# ═══════════════════════════════════════════════════════════════

ICONS = {
    # Status
    "success": "✅",
    "error": "❌",
    "warning": "⚠️",
    "info": "ℹ️",
    "running": "⏳",
    "pending": "⏺",
    "completed": "✓",
    "failed": "✗",

    # Roles
    "user": "💬",
    "assistant": "🤖",
    "system": "⚙️",

    # Tools
    "tool": "🔧",
    "read": "📖",
    "write": "✏️",
    "shell": "⚡",
    "network": "🌐",
    "memory": "💾",
    "mcp": "🔌",
    "search": "🔍",

    # Files and Folders
    "file": "📄",
    "folder": "📂",
    "code": "💻",

    # Actions
    "thinking": "💭",
    "processing": "⚙️",
    "config": "⚙️",
    "stats": "📊",
    "help": "❓",
    "exit": "👋",
    "save": "💾",
    "load": "📂",

    # Features
    "model": "🤖",
    "version": "📦",
    "cwd": "📂",
    "commands": "⌨️",
    "token": "💰",
    "time": "⏱️",
    "welcome": "✨",
}

# ═══════════════════════════════════════════════════════════════
# UI MESSAGES
# ═══════════════════════════════════════════════════════════════

MESSAGES = {
    "goodbye": "👋 Goodbye! Thanks for using BYOM AI Agents.",
    "interrupt_hint": "💡 Tip: Use /exit to quit",
    "no_output": "(no output)",
    "no_args": "(no args)",
    "truncated": "⚠️  Output was truncated",
    "approval_required": "⚠️  Approval Required",
    "approval_hint": "y = approve, n = reject",
}

# ═══════════════════════════════════════════════════════════════
# FORMATTING
# ═══════════════════════════════════════════════════════════════

MAX_BLOCK_TOKENS = 2500
MAX_DISPLAY_LENGTH = 10000
TRUNCATION_MESSAGE = "\n... (truncated) ..."

# ═══════════════════════════════════════════════════════════════
# SYNTAX HIGHLIGHTING
# ═══════════════════════════════════════════════════════════════

SYNTAX_THEME = "monokai"

LANGUAGE_MAP = {
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
    ".rb": "ruby",
    ".php": "php",
    ".scala": "scala",
    ".r": "r",
    ".dart": "dart",
    ".lua": "lua",
    ".vim": "vim",
}

# ═══════════════════════════════════════════════════════════════
# TOOL ARGUMENT DISPLAY ORDER
# ═══════════════════════════════════════════════════════════════

TOOL_ARG_ORDER = {
    "read_file": ["path", "offset", "limit"],
    "write_file": ["path", "create_directories", "content"],
    "edit": ["path", "replace_all", "old_string", "new_string"],
    "shell": ["command", "timeout", "cwd"],
    "list_dir": ["path", "include_hidden"],
    "grep": ["path", "case_insensitive", "pattern"],
    "glob": ["path", "pattern"],
    "todos": ["id", "action", "content"],
    "memory": ["action", "key", "value"],
    "web_search": ["query", "num_results"],
    "web_fetch": ["url"],
}

# ═══════════════════════════════════════════════════════════════
# KEYBOARD SHORTCUTS
# ═══════════════════════════════════════════════════════════════

SHORTCUTS = {
    "Ctrl+C": "Interrupt current operation",
    "Ctrl+D": "Exit (EOF)",
    "Enter": "Submit message",
    "Tab": "Autocomplete",
    "Shift+Tab": "Previous completion",
    "↑/↓": "Navigate completions",
}

# ═══════════════════════════════════════════════════════════════
# PROGRESS INDICATORS
# ═══════════════════════════════════════════════════════════════

SPINNERS = {
    "default": ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"],
    "dots": ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"],
    "line": ["-", "\\", "|", "/"],
    "arrow": ["←", "↖", "↑", "↗", "→", "↘", "↓", "↙"],
    "pulse": ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"],
}
