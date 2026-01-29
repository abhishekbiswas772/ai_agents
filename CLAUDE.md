# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**BYOM AI Agents** (Bring Your Own Model) is a terminal-based AI coding agent framework that supports multiple LLM providers including OpenAI, Anthropic, Google, Ollama, LM Studio, and OpenRouter. The project enables users to run AI coding assistants locally or via cloud providers with a unified interface.

## Development Commands

### Setup and Dependencies
```bash
# Install dependencies (development)
uv sync

# Install package in editable mode
pip install -e .

# Install with dev dependencies
pip install -e ".[dev]"
```

### Testing
```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_providers.py -v

# Run with coverage
uv run pytest tests/ --cov=src/byom --cov-report=term-missing

# Run single test
uv run pytest tests/test_config.py::TestConfig::test_load_config -v
```

### Linting and Formatting
```bash
# Check linting
uv run ruff check src/

# Auto-fix linting issues
uv run ruff check --fix src/

# Format code
uv run ruff format src/

# Type checking
uv run mypy src/
```

### Running the CLI
```bash
# Interactive mode
python -m byom.cli

# Or if installed
byom

# Single query mode
byom "What files are in this directory?"

# Specify working directory
byom --cwd /path/to/project

# Show version
byom --version

# Reset configuration
byom --reset
```

### Building and Publishing
```bash
# Build package
python -m build

# Install locally from dist
pip install dist/byom_ai_agents-0.1.8-py3-none-any.whl
```

## Architecture

### Core Components

1. **Agent System** (`src/byom/agent/`)
   - `agent.py`: Main agentic loop implementing turn-based conversation flow with tool execution
   - `session.py`: Session management including tool registry, context manager, MCP manager, and hook system initialization
   - `events.py`: Event types for agent lifecycle (text deltas, tool calls, errors)
   - `persistence.py`: Session saving/loading and checkpoint management

2. **LLM Client** (`src/byom/client/`)
   - `llm_client.py`: Unified client using OpenAI SDK format for all providers
   - `response.py`: Streaming event parsing and tool call handling
   - Supports retry logic for rate limits and API errors

3. **Provider System** (`src/byom/providers/`)
   - `registry.py`: Auto-detection of providers based on model names
   - `openai_provider.py`, `anthropic_provider.py`: Provider implementations
   - `presets.py`: Pre-configured model settings and defaults
   - All providers use OpenAI-compatible interface via `AsyncOpenAI` client

4. **Context Management** (`src/byom/context/`)
   - `manager.py`: Message history, token tracking, and automatic pruning of old tool outputs
   - `compaction.py`: Automatic conversation compression when context limit reached (80% threshold)
   - `loop_detector.py`: Detects and prevents infinite loops in agent behavior

5. **Tool System** (`src/byom/tools/`)
   - `registry.py`: Tool registration and invocation with approval checking
   - `builtin/`: 12 built-in tools (read_file, write_file, edit_file, shell, grep, glob, find, list_dir, web_search, web_fetch, todo, memory)
   - `mcp/`: Model Context Protocol integration for external tool servers
   - `discovery.py`: Auto-discovery of custom tools from `.ai-agent/tools/` directory
   - `subagents.py`: Specialized sub-agents for complex tasks

6. **Configuration** (`src/byom/config/`)
   - `config.py`: Pydantic models for all configuration options
   - `loader.py`: Layered config loading (system → project → env vars)
   - System config: `~/.config/byom-ai/config.toml`
   - Project config: `.byom/config.toml` (or legacy `.ai-agent/config.toml`)
   - Supports AGENT.md files for project-specific developer instructions

7. **Safety System** (`src/byom/safety/`)
   - `approval.py`: Multi-policy approval system (on-request, auto, auto-edit, never, yolo)
   - Validates dangerous operations before execution
   - Hook integration for custom approval workflows

8. **UI/CLI** (`src/byom/ui/`, `src/byom/cli.py`)
   - `cli.py`: Entry point with prompt_toolkit-based interactive session
   - `tui.py`: Rich-based terminal UI with streaming output
   - File path completion with `@` trigger (via FileIndexer)
   - Command completion with `/` trigger
   - First-run setup wizard integration

9. **Commands** (`src/byom/commands/`)
   - `registry.py`: Command system for slash commands like `/help`, `/config`, `/model`
   - `core.py`: Built-in commands implementation
   - Extensible for custom commands

### Key Architectural Patterns

- **Agentic Loop**: Agent runs turns until no tool calls or max turns reached (agent.py:37-165)
- **Event Streaming**: All agent actions emit events for UI updates (AgentEventType)
- **Tool Approval**: Tools go through approval manager before execution (registry.py:104-129)
- **Context Compression**: Automatic summarization when 80% of context window used (manager.py:131-135)
- **MCP Integration**: External tools via stdio or HTTP/SSE transports (mcp_manager.py)
- **Hook System**: Custom scripts triggered on agent/tool events (hooks/hook_system.py)
- **Provider Abstraction**: Unified provider interface in providers/base.py with specific implementations for each LLM provider
- **Provider Auto-detection**: Model names automatically select appropriate provider (providers/registry.py)
- **Tool Call Parser**: Robust JSON parsing with fallback strategies for malformed tool calls (tools/tool_call_parser.py)
- **Provider Bridge**: Converts provider-specific events to client events for backward compatibility (client/provider_bridge.py)

### Configuration Hierarchy

Configuration is loaded in this order (later overrides earlier):
1. Built-in defaults
2. System config: `~/.config/byom-ai/config.toml`
3. Project config: `.byom/config.toml` or `.ai-agent/config.toml`
4. Environment variables (API keys, base URLs)
5. AGENT.md file content → `developer_instructions` field

### Data Storage

- User data: `~/.local/share/byom-ai/` (or platform-specific)
- Sessions: `~/.local/share/byom-ai/sessions/`
- Todos: `~/.local/share/byom-ai/todos.json`
- User memory: `~/.local/share/byom-ai/user_memory.json`
- File index: `.byom-ai/file_index.json` (workspace-specific)

### Tool Discovery

Custom tools are auto-discovered from:
1. Project directory: `.ai-agent/tools/*.py`
2. User config directory: `~/.config/byom-ai/.ai-agent/tools/*.py`

Tool classes must inherit from `Tool` base class (tools/base.py).

### Important Implementation Notes

- **Provider System**: Each provider (OpenAI, Anthropic, Google) has a native implementation extending providers/base.py:LLMProvider
- **Provider Bridge**: client/provider_bridge.py converts provider events to client events for backward compatibility
- **Tool Call Parsing**: Enhanced JSON repair in tools/tool_call_parser.py handles malformed tool calls with 4 fallback strategies:
  1. Direct JSON parse
  2. Repair and retry (fixes quotes, commas, truncation)
  3. Extract embedded JSON from text
  4. Heuristic key-value extraction
- **Error Handling**: Providers have built-in retry logic with exponential backoff for rate limits and connection errors
- Tool outputs are automatically pruned when >40k tokens accumulated (manager.py:193-226)
- Loop detection tracks repeated tool calls and responses (loop_detector.py)
- Shell tool has environment variable filtering for security (config.py:53-59)
- MCP tools are namespaced as `{server_name}__{tool_name}` (mcp_manager.py:58)
- UI has specialized tool renderers in ui/tool_renderer.py for intelligent output formatting

### Testing Philosophy

- Tests in `tests/` directory mirror `src/byom/` structure
- Use pytest with async support (`pytest-asyncio`)
- Mock external API calls to LLM providers
- Focus on integration tests for agent behavior

## Security Considerations

When working on this codebase, follow the Snyk security rules:
- Always run snyk_code_scan tool for new Python code
- Fix security issues found by Snyk before proceeding
- Rescan after fixes to verify resolution
- Repeat until no new issues are found
