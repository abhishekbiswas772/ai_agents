import json
from clients.llm_client import LLMClient
from configs.configs import Config
from configs.loader import get_data_dir
from context.manager import ContextManager
from tools.register_tools import create_default_registry
import uuid
from datetime import datetime
from pathlib import Path
from collections import deque


class ConversationContext:
    """Tracks recent file operations and context for pronoun resolution."""

    def __init__(self, max_history: int = 10):
        self.max_history = max_history
        self.file_history: deque = deque(maxlen=max_history)
        self.last_file_written: Path | None = None
        self.last_file_read: Path | None = None
        self.last_command: str | None = None

    def track_file_write(self, path: Path) -> None:
        """Track a file that was written or created."""
        self.last_file_written = path
        self.file_history.append({"action": "write", "path": path, "time": datetime.now()})

    def track_file_edit(self, path: Path) -> None:
        """Track a file that was edited."""
        self.last_file_written = path  # For "edit it" resolution
        self.file_history.append({"action": "edit", "path": path, "time": datetime.now()})

    def track_file_read(self, path: Path) -> None:
        """Track a file that was read."""
        self.last_file_read = path
        self.file_history.append({"action": "read", "path": path, "time": datetime.now()})

    def track_command(self, command: str) -> None:
        """Track a shell command that was executed."""
        self.last_command = command

    def get_last_modified_file(self) -> Path | None:
        """Get the most recently written or edited file."""
        return self.last_file_written

    def get_context_summary(self) -> str:
        """Generate a summary of recent operations for prompt injection."""
        if not self.file_history:
            return ""

        summary_parts = []
        if self.last_file_written:
            summary_parts.append(f"Most recently modified file: {self.last_file_written}")
        if self.last_command:
            summary_parts.append(f"Last command executed: {self.last_command}")

        return "\n".join(summary_parts)


class Session:
    def __init__(self, config: Config):
        self.config = config
        self.client = LLMClient(config=self.config)
        self.tool_registry = create_default_registry(config=self.config)
        self.context_manager = ContextManager(
            config=self.config, 
            user_memory=self._load_memory(), 
            tools=self.tool_registry.get_tools()
        )
        self.session_id = str(uuid.uuid4())
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self._turn_count = 0
        self.conversation_context = ConversationContext()

    def increment_turn(self) -> int:
        self._turn_count += 1
        self.updated_at = datetime.now()
        return self._turn_count
    
    def _load_memory(self) -> str | None:
        data_dir = get_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)
        path = data_dir / "user_memory.json"

        if not path.exists():
            return None

        try:
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
            entries = data.get("entries")
            if not entries:
                return None 
            lines = ["User preference and notes"]
            for key, value in entries.items():
                lines.append(f"- {key}: {value}")
            return "\n".join(lines)
        except Exception:
            return None
