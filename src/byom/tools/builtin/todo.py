"""
Enhanced Todo Tool - Persistent task tracking with status management

Features:
- Persistent storage (JSON file)
- Status tracking (pending, in_progress, completed)
- Timestamps for creation and completion
- Rich formatted output with strikethrough for completed items
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field

from byom.config.config import Config
from byom.config.loader import get_data_dir
from byom.tools.base import Tool, ToolInvocation, ToolKind, ToolResult


class TodoItem(BaseModel):
    """A single todo item with metadata"""

    id: str
    content: str
    status: str  # pending, in_progress, completed
    created_at: str
    updated_at: str
    completed_at: str | None = None


class TodosParams(BaseModel):
    """Parameters for the todos tool"""

    action: str = Field(
        ...,
        description="Action: 'add', 'update', 'complete', 'list', 'clear', 'delete'",
    )
    id: str | None = Field(None, description="Todo ID (for update/complete/delete)")
    content: str | None = Field(None, description="Todo content (for add/update)")
    status: str | None = Field(
        None, description="Status: 'pending', 'in_progress', 'completed' (for update)"
    )


class TodosTool(Tool):
    """
    Manage a persistent task list with status tracking.

    Use this to track progress on multi-step tasks. Todos are saved to disk
    and persist across sessions.
    """

    name = "todos"
    description = (
        "Manage a persistent task list. Track progress on multi-step tasks with "
        "status tracking (pending, in_progress, completed). "
        "Actions: add, update, complete, list, clear, delete"
    )
    kind = ToolKind.MEMORY
    schema = TodosParams

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self._todos_file = get_data_dir() / "todos.json"
        self._todos: dict[str, TodoItem] = {}
        self._load_todos()

    def _load_todos(self) -> None:
        """Load todos from persistent storage"""
        if self._todos_file.exists():
            try:
                with open(self._todos_file, "r") as f:
                    data = json.load(f)
                    self._todos = {
                        todo_id: TodoItem(**todo_data)
                        for todo_id, todo_data in data.items()
                    }
            except (json.JSONDecodeError, Exception) as e:
                # If file is corrupted, start fresh
                self._todos = {}

    def _save_todos(self) -> None:
        """Save todos to persistent storage"""
        self._todos_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._todos_file, "w") as f:
            data = {todo_id: todo.model_dump() for todo_id, todo in self._todos.items()}
            json.dump(data, f, indent=2)

    def _format_timestamp(self, timestamp: str) -> str:
        """Format timestamp for display"""
        try:
            dt = datetime.fromisoformat(timestamp)
            return dt.strftime("%Y-%m-%d %H:%M")
        except:
            return timestamp

    def _format_todo_list(self, show_completed: bool = True) -> str:
        """Format todos for display with Rich markup"""
        if not self._todos:
            return "No todos"

        lines = []

        # Group by status
        pending = [t for t in self._todos.values() if t.status == "pending"]
        in_progress = [t for t in self._todos.values() if t.status == "in_progress"]
        completed = [t for t in self._todos.values() if t.status == "completed"]

        # Show in progress
        if in_progress:
            lines.append("🔄 IN PROGRESS:")
            for todo in in_progress:
                lines.append(
                    f"  [{todo.id}] {todo.content} "
                    f"(started: {self._format_timestamp(todo.updated_at)})"
                )
            lines.append("")

        # Show pending
        if pending:
            lines.append("📋 PENDING:")
            for todo in pending:
                lines.append(
                    f"  [{todo.id}] {todo.content} "
                    f"(created: {self._format_timestamp(todo.created_at)})"
                )
            lines.append("")

        # Show completed (with strikethrough)
        if completed and show_completed:
            lines.append("✅ COMPLETED:")
            for todo in completed:
                completed_time = (
                    self._format_timestamp(todo.completed_at)
                    if todo.completed_at
                    else "unknown"
                )
                # Note: Strikethrough will be rendered by the TUI
                lines.append(
                    f"  [{todo.id}] ~~{todo.content}~~ (completed: {completed_time})"
                )

        return "\n".join(lines) if lines else "No todos"

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute todo action"""
        try:
            params = TodosParams(**invocation.params)
        except Exception as e:
            return ToolResult.error_result(f"Invalid parameters: {e}")

        now = datetime.now().isoformat()

        # ADD action
        if params.action.lower() == "add":
            if not params.content:
                return ToolResult.error_result("`content` required for 'add' action")

            todo_id = str(uuid.uuid4())[:8]
            todo = TodoItem(
                id=todo_id,
                content=params.content,
                status="pending",
                created_at=now,
                updated_at=now,
            )
            self._todos[todo_id] = todo
            self._save_todos()

            return ToolResult.success_result(
                f"✅ Added todo [{todo_id}]: {params.content}",
                metadata={"todo_id": todo_id, "status": "pending"},
            )

        # UPDATE action
        elif params.action.lower() == "update":
            if not params.id:
                return ToolResult.error_result("`id` required for 'update' action")
            if params.id not in self._todos:
                return ToolResult.error_result(f"Todo not found: {params.id}")

            todo = self._todos[params.id]

            if params.content:
                todo.content = params.content
            if params.status:
                if params.status not in ["pending", "in_progress", "completed"]:
                    return ToolResult.error_result(
                        f"Invalid status: {params.status}. "
                        "Must be: pending, in_progress, or completed"
                    )
                todo.status = params.status
                if params.status == "completed" and not todo.completed_at:
                    todo.completed_at = now

            todo.updated_at = now
            self._save_todos()

            return ToolResult.success_result(
                f"✏️ Updated todo [{todo.id}]: {todo.content} (status: {todo.status})",
                metadata={"todo_id": todo.id, "status": todo.status},
            )

        # COMPLETE action
        elif params.action.lower() == "complete":
            if not params.id:
                return ToolResult.error_result("`id` required for 'complete' action")
            if params.id not in self._todos:
                return ToolResult.error_result(f"Todo not found: {params.id}")

            todo = self._todos[params.id]
            todo.status = "completed"
            todo.completed_at = now
            todo.updated_at = now
            self._save_todos()

            return ToolResult.success_result(
                f"✅ Completed todo [{todo.id}]: ~~{todo.content}~~",
                metadata={"todo_id": todo.id, "status": "completed"},
            )

        # DELETE action
        elif params.action.lower() == "delete":
            if not params.id:
                return ToolResult.error_result("`id` required for 'delete' action")
            if params.id not in self._todos:
                return ToolResult.error_result(f"Todo not found: {params.id}")

            todo = self._todos.pop(params.id)
            self._save_todos()

            return ToolResult.success_result(
                f"🗑️ Deleted todo [{todo.id}]: {todo.content}"
            )

        # LIST action
        elif params.action.lower() == "list":
            output = self._format_todo_list()
            total = len(self._todos)
            completed = sum(1 for t in self._todos.values() if t.status == "completed")
            in_progress = sum(
                1 for t in self._todos.values() if t.status == "in_progress"
            )
            pending = sum(1 for t in self._todos.values() if t.status == "pending")

            return ToolResult.success_result(
                output,
                metadata={
                    "total": total,
                    "completed": completed,
                    "in_progress": in_progress,
                    "pending": pending,
                },
            )

        # CLEAR action
        elif params.action.lower() == "clear":
            count = len(self._todos)
            self._todos.clear()
            self._save_todos()

            return ToolResult.success_result(f"🧹 Cleared {count} todos")

        else:
            return ToolResult.error_result(
                f"Unknown action: {params.action}. "
                "Valid actions: add, update, complete, list, clear, delete"
            )
