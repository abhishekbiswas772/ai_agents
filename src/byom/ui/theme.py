"""
BYOM AI Agents - Rich Theme

Claude Code-inspired terminal theme with modern aesthetics.
Enhanced for better visual hierarchy and readability.
"""

from rich.theme import Theme

# Color palette - inspired by Claude Code and modern terminals
BYOM_THEME = Theme({
    # ═══════════════════════════════════════════════════════════════
    # GENERAL STYLES
    # ═══════════════════════════════════════════════════════════════
    "info": "dodger_blue2",
    "warning": "yellow1",
    "error": "red1 bold",
    "success": "green3 bold",
    "dim": "grey50",
    "muted": "grey58",
    "border": "grey42",
    "highlight": "bold bright_cyan",
    "accent": "bright_magenta",

    # ═══════════════════════════════════════════════════════════════
    # CONVERSATION ROLES
    # ═══════════════════════════════════════════════════════════════
    "user": "bright_blue bold",
    "user.prompt": "bright_blue",
    "assistant": "bright_white",
    "assistant.header": "bright_cyan bold",
    "assistant.thinking": "grey70 italic",
    "system": "grey50 italic",

    # ═══════════════════════════════════════════════════════════════
    # TOOL STYLES
    # ═══════════════════════════════════════════════════════════════
    "tool": "magenta bold",
    "tool.name": "bright_magenta",
    "tool.running": "yellow1",
    "tool.success": "green3",
    "tool.failed": "red1",

    # Tool categories
    "tool.read": "cyan",
    "tool.write": "yellow1",
    "tool.shell": "medium_purple1",
    "tool.network": "dodger_blue1",
    "tool.memory": "green3",
    "tool.mcp": "bright_cyan",

    # ═══════════════════════════════════════════════════════════════
    # CODE AND SYNTAX
    # ═══════════════════════════════════════════════════════════════
    "code": "grey93",
    "code.keyword": "bright_magenta",
    "code.string": "bright_green",
    "code.number": "bright_cyan",
    "code.comment": "grey50 italic",
    "code.function": "bright_yellow",
    "code.class": "bright_cyan bold",

    # Diff highlighting
    "diff.add": "green3",
    "diff.remove": "red1",
    "diff.header": "bright_cyan bold",
    "diff.line_number": "grey50",

    # ═══════════════════════════════════════════════════════════════
    # STATUS AND PROGRESS
    # ═══════════════════════════════════════════════════════════════
    "status": "grey70",
    "status.running": "yellow1",
    "status.done": "green3",
    "status.failed": "red1",
    "status.model": "bright_cyan",
    "status.tokens": "grey50",
    "status.time": "grey50",
    "progress": "bright_cyan",
    "progress.bar": "bright_cyan",
    "progress.percentage": "bright_white",
    "spinner": "bright_magenta",

    # ═══════════════════════════════════════════════════════════════
    # PANELS AND BOXES
    # ═══════════════════════════════════════════════════════════════
    "panel.title": "bright_white bold",
    "panel.border": "grey35",
    "panel.accent": "bright_magenta",

    # ═══════════════════════════════════════════════════════════════
    # TODOS AND TASKS
    # ═══════════════════════════════════════════════════════════════
    "todo.pending": "bright_yellow",
    "todo.in_progress": "bright_cyan",
    "todo.completed": "grey50 strike",
    "todo.id": "grey50",

    # ═══════════════════════════════════════════════════════════════
    # STATISTICS AND METRICS
    # ═══════════════════════════════════════════════════════════════
    "stat.label": "grey58",
    "stat.value": "bright_white bold",
    "stat.positive": "green3",
    "stat.negative": "red1",
    "stat.neutral": "yellow1",

    # ═══════════════════════════════════════════════════════════════
    # SPECIAL STATES
    # ═══════════════════════════════════════════════════════════════
    "thinking": "grey62 italic",
    "processing": "bright_magenta",
    "waiting": "yellow",
    "confirmation": "bright_yellow bold",

    # ═══════════════════════════════════════════════════════════════
    # KEYBOARD AND SHORTCUTS
    # ═══════════════════════════════════════════════════════════════
    "key": "bright_white on grey23",
    "shortcut.key": "bright_cyan bold",
    "shortcut.description": "grey70",
})

# Box drawing characters for custom borders
BOX_CHARS = {
    "single": {
        "top_left": "┌",
        "top_right": "┐",
        "bottom_left": "└",
        "bottom_right": "┘",
        "horizontal": "─",
        "vertical": "│",
    },
    "double": {
        "top_left": "╔",
        "top_right": "╗",
        "bottom_left": "╚",
        "bottom_right": "╝",
        "horizontal": "═",
        "vertical": "║",
    },
    "rounded": {
        "top_left": "╭",
        "top_right": "╮",
        "bottom_left": "╰",
        "bottom_right": "╯",
        "horizontal": "─",
        "vertical": "│",
    },
}

# Status icons
ICONS = {
    "success": "✓",
    "error": "✗",
    "warning": "⚠",
    "info": "ℹ",
    "running": "⏺",
    "pending": "○",
    "completed": "●",
    "thinking": "💭",
    "tool": "🔧",
    "file": "📄",
    "folder": "📁",
    "code": "💻",
    "search": "🔍",
    "web": "🌐",
    "shell": "⌘",
    "memory": "🧠",
}
