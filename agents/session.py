from clients.llm_client import LLMClient
from configs.configs import Config
from context.manager import ContextManager
from tools.register_tools import create_default_registry
import uuid
from datetime import datetime


class Session:
    def __init__(self, config: Config):
        self.config = config
        self.client = LLMClient(config=self.config)
        self.context_manager = ContextManager(config=self.config)
        self.tool_registry = create_default_registry()
        self.session_id = str(uuid.uuid4())
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self._turn_count = 0

    def increment_turn(self) -> int:
        self._turn_count += 1
        self.updated_at = datetime.now()
        return self._turn_count