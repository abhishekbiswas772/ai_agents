from typing import Any, Dict, List
from configs.configs import Config
from prompts.system import get_system_prompt
from dataclasses import dataclass, field
from utils.text import count_token

@dataclass
class MessageItem:
    role : str
    content : str
    token_count : int | None = None
    tool_call_id : str | None = None
    tool_calls : List[Dict[str, Any]] = field(default_factory=list)


    def to_dict(self) -> Dict[str, Any]:
        result : Dict[str, Any] = {
            "role" : self.role,
        }
        if self.role == "tool":
            result['content'] = self.content
        elif self.content:  # Only include if not empty
            result['content'] = self.content

        if self.tool_call_id:
            result['tool_call_id'] = self.tool_call_id

        if self.tool_calls:
            result['tool_calls'] = self.tool_calls
        return result

class ContextManager:
    def __init__(self, config: Config) -> None:
        self.config = config
        base_prompt = get_system_prompt(config=self.config)
        tool_prompt = """

# IMPORTANT: Tool Usage

You have access to tools that you MUST use to complete tasks. When a user asks you to read a file, search code, or perform any action, you MUST call the appropriate tool.

Available tools:
- read_file: Read file contents. Use this whenever the user asks to read, view, or explain a file.

EXAMPLES:
User: "read main.py and explain it"
Assistant: [calls read_file tool with path="main.py", then explains the content]

User: "what's in config.json?"
Assistant: [calls read_file tool with path="config.json", then describes it]

CRITICAL: Do NOT respond with just text when you should be calling a tool. Always use the tools available to you."""
        self._system_prompt = base_prompt + tool_prompt
        self._messages : list[MessageItem] = []
        self._model_name = self.config.model_name


    def add_user_message(self, content: str) -> None:
        item = MessageItem(
            role='user',
            content=content,
            token_count = count_token(
                text = content, 
                model= self._model_name
            )
        )
        self._messages.append(item)
        
    def add_assistant_message(self, content: str | None, tool_calls: List[Dict[str, Any]] | None = None) -> None:
        item = MessageItem(
            role='assistant',
            content=content or "",
            token_count = count_token(
                text = content or "",
                model= self._model_name
            ) if content else 0,
            tool_calls=tool_calls or []
        )
        self._messages.append(item)


    def get_messages(self) ->  List[Dict[str, Any]]:
        messages = []
        if self._system_prompt:
            messages.append(
                {
                    'role' : 'system',
                    'content' : self._system_prompt
                }
            )

        for item in self._messages:
            messages.append(item.to_dict())
        return messages
    
    def add_tool_call_result(self, tool_call_id : str, content : str) -> None:
        item = MessageItem(
            role="tool",
            content=content,
            tool_call_id=tool_call_id,
            token_count=count_token(content, self._model_name)
        )
        self._messages.append(item)
    
    
