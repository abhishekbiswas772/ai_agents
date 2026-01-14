from prompts.system import get_system_prompt
from dataclass import dataclass

class ContextManager:
    def __init__(self) -> None:
        self.system_prompt = get_system_prompt()
        self._messages = []