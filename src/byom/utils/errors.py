from typing import Any


class AgentError(Exception):
    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.cause = cause

    def __str__(self) -> str:
        base = self.message
        if self.details:
            detail_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            base = f"{base} ({detail_str})"
        if self.cause:
            base = f"{base} [caused by: {self.cause}]"
        return base

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
            "cause": str(self.cause) if self.cause else None,
        }


class ConfigError(AgentError):
    """Raised when there's a configuration-related error."""

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        config_file: str | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {}) or {}
        if config_key:
            details["config_key"] = config_key
        if config_file:
            details["config_file"] = config_file
        super().__init__(message, details=details, **kwargs)
        self.config_key = config_key
        self.config_file = config_file


class ToolError(AgentError):
    """Raised when a tool execution fails."""

    def __init__(
        self,
        message: str,
        tool_name: str | None = None,
        tool_args: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {}) or {}
        if tool_name:
            details["tool_name"] = tool_name
        if tool_args:
            details["tool_args"] = str(tool_args)
        super().__init__(message, details=details, **kwargs)
        self.tool_name = tool_name
        self.tool_args = tool_args


class ValidationError(AgentError):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str,
        field_name: str | None = None,
        expected_type: str | None = None,
        actual_value: Any = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {}) or {}
        if field_name:
            details["field"] = field_name
        if expected_type:
            details["expected"] = expected_type
        if actual_value is not None:
            details["actual"] = str(actual_value)
        super().__init__(message, details=details, **kwargs)
        self.field_name = field_name
        self.expected_type = expected_type
        self.actual_value = actual_value


class ModelError(AgentError):
    """Raised when there's an error with the LLM model."""

    def __init__(
        self,
        message: str,
        model_name: str | None = None,
        provider: str | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {}) or {}
        if model_name:
            details["model"] = model_name
        if provider:
            details["provider"] = provider
        super().__init__(message, details=details, **kwargs)
        self.model_name = model_name
        self.provider = provider


class NetworkError(AgentError):
    """Raised when there's a network-related error."""

    def __init__(
        self,
        message: str,
        url: str | None = None,
        status_code: int | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {}) or {}
        if url:
            details["url"] = url
        if status_code:
            details["status_code"] = status_code
        super().__init__(message, details=details, **kwargs)
        self.url = url
        self.status_code = status_code


class FileOperationError(AgentError):
    """Raised when a file operation fails."""

    def __init__(
        self,
        message: str,
        file_path: str | None = None,
        operation: str | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {}) or {}
        if file_path:
            details["file_path"] = file_path
        if operation:
            details["operation"] = operation
        super().__init__(message, details=details, **kwargs)
        self.file_path = file_path
        self.operation = operation


class SessionError(AgentError):
    """Raised when there's a session-related error."""

    def __init__(
        self,
        message: str,
        session_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {}) or {}
        if session_id:
            details["session_id"] = session_id
        super().__init__(message, details=details, **kwargs)
        self.session_id = session_id


class ContextError(AgentError):
    """Raised when there's a context management error."""

    def __init__(
        self,
        message: str,
        context_size: int | None = None,
        max_size: int | None = None,
        **kwargs: Any,
    ) -> None:
        details = kwargs.pop("details", {}) or {}
        if context_size is not None:
            details["context_size"] = context_size
        if max_size is not None:
            details["max_size"] = max_size
        super().__init__(message, details=details, **kwargs)
        self.context_size = context_size
        self.max_size = max_size
