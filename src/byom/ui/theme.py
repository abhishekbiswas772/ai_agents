"""
BYOM AI Agents - Rich Theme

Claude Code-inspired terminal theme with modern aesthetics.
"""

from rich.theme import Theme

# Color palette - inspired by Claude Code and modern terminals
BYOM_THEME = Theme({
    # ═══════════════════════════════════════════════════════════════
    # GENERAL STYLES
    # ═══════════════════════════════════════════════════════════════
    "info": "cyan",
    "warning": "yellow",
    "error": "bright_red bold",
    "success": "bright_green",
    "dim": "grey50",
    "muted": "grey62",
    "border": "grey35",
    "highlight": "bright_cyan bold",
    "accent": "bright_magenta",
    
    # ═══════════════════════════════════════════════════════════════
    # CONVERSATION ROLES
    # ═══════════════════════════════════════════════════════════════
    "user": "bright_blue bold",
    "user.prompt": "bright_blue",
    "assistant": "bright_white",
    "assistant.thinking": "grey70 italic",
    "system": "grey50 italic",
    
    # ═══════════════════════════════════════════════════════════════
    # TOOL STYLES
    # ═══════════════════════════════════════════════════════════════
    "tool": "bright_magenta bold",
    "tool.name": "bright_magenta",
    "tool.running": "yellow",
    "tool.success": "bright_green",
    "tool.failed": "bright_red",
    
    # Tool categories
    "tool.read": "bright_cyan",
    "tool.write": "bright_yellow",
    "tool.shell": "bright_magenta",
    "tool.network": "bright_blue",
    "tool.memory": "bright_green",
    "tool.mcp": "cyan",
    
    # ═══════════════════════════════════════════════════════════════
    # CODE AND SYNTAX
    # ═══════════════════════════════════════════════════════════════
    "code": "white",
    "code.keyword": "bright_magenta",
    "code.string": "bright_green",
    "code.number": "bright_cyan",
    "code.comment": "grey50 italic",
    "code.function": "bright_yellow",
    "code.class": "bright_cyan bold",
    
    # Diff highlighting
    "diff.add": "bright_green",
    "diff.remove": "bright_red",
    "diff.header": "bright_cyan",
    "diff.line_number": "grey50",
    
    # ═══════════════════════════════════════════════════════════════
    # STATUS AND PROGRESS
    # ═══════════════════════════════════════════════════════════════
    "status": "grey70",
    "status.model": "bright_cyan",
    "status.tokens": "grey50",
    "status.time": "grey50",
    "progress": "bright_cyan",
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
    # SPECIAL STATES
    # ═══════════════════════════════════════════════════════════════
    "thinking": "grey62 italic",
    "processing": "bright_magenta",
    "waiting": "yellow",
    "confirmation": "bright_yellow bold",
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
