# BYOM AI Agents

**Bring Your Own Model** - A terminal-based AI coding agent that works with ANY LLM provider.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

## <¯ What is BYOM AI Agents?

BYOM AI Agents is a powerful, terminal-based AI coding assistant that puts YOU in control. Unlike other AI coding tools that lock you into a single provider, BYOM lets you:

- **Use Any LLM**: OpenAI, Anthropic Claude, Google Gemini, or even local models via Ollama
- **Keep Your Data Private**: Run everything locally with your own models
- **Stay Flexible**: Switch between providers without changing your workflow
- **Work Your Way**: Terminal-first interface with rich formatting and progress indicators

## ( Features

### = Universal LLM Support (BYOM!)

- **OpenAI**: GPT-4, GPT-4 Turbo, GPT-3.5
- **Anthropic**: Claude 3.5 Sonnet, Opus, Haiku
- **Google**: Gemini Pro, Gemini 1.5 Pro
- **OpenAI-Compatible**: Ollama, LM Studio, OpenRouter, and more
- **Auto-detection**: Automatic provider selection based on model name

### =à Powerful Built-in Tools

- **File Operations**: Read, write, edit files with smart diff display
- **Search & Navigation**: Grep, glob, and recursive file finding
- **Shell Integration**: Execute commands with approval workflows
- **Web Research**: Built-in web search and URL fetching
- **Task Management**: Persistent todos with status tracking
- **Memory System**: Remember user preferences across sessions
- **MCP Support**: Integrate Model Context Protocol servers

### =¡ Smart Features

- **Context Management**: Automatic conversation compression when needed
- **Loop Detection**: Prevents the agent from getting stuck
- **Approval Policies**: Control which actions require confirmation
- **Session Persistence**: Save and resume conversations
- **Checkpoints**: Create snapshots of your work
- **Rich TUI**: Beautiful terminal UI with syntax highlighting

## =æ Installation

### Using pip (Recommended)

```bash
pip install byom-ai-agents
```

### From Source

```bash
git clone https://github.com/abhishek-dev/byom-ai-agents.git
cd byom-ai-agents
pip install -e .
```

### Using uv (Development)

```bash
git clone https://github.com/abhishek-dev/byom-ai-agents.git
cd byom-ai-agents
uv sync
```

## =€ Quick Start

### First Run

When you first run BYOM, it will guide you through a setup wizard:

```bash
byom
```

The wizard will help you:
1. Choose your LLM provider
2. Configure API keys
3. Set your preferred model
4. Create config files

### Basic Usage

```bash
# Interactive mode
byom

# Single query mode
byom "What files are in this directory?"

# Specify working directory
byom --cwd /path/to/project

# Show version
byom --version
```

## ™ Configuration

BYOM uses a layered configuration system:

1. **System Config**: `~/.config/byom-ai/config.toml`
2. **Project Config**: `.byom/config.toml` in your project
3. **Environment Variables**: Override with env vars

### Example Configuration

```toml
# ~/.config/byom-ai/config.toml

[model]
name = "gpt-4-turbo"
provider = "openai"  # auto, openai, anthropic, google
temperature = 0.7
max_tokens = 4096

[api]
# Use environment variables for API keys:
# export OPENAI_API_KEY=your-key
# export ANTHROPIC_API_KEY=your-key

[behavior]
approval_policy = "auto"  # auto, on-request, auto-edit, never, yolo
max_turns = 25
auto_save = true

[hooks]
enabled = false

[mcp]
enabled = true

# Optional: MCP Server configuration
# [mcp_servers.filesystem]
# command = "npx"
# args = ["-y", "@anthropic-ai/mcp-server-filesystem", "./"]
```

## = Setting Up API Keys

### OpenAI

```bash
export OPENAI_API_KEY=sk-...
```

### Anthropic

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

### Google

```bash
export GOOGLE_API_KEY=...
```

### Local Models (Ollama)

```toml
[model]
name = "llama3"
provider = "openai"

[api]
base_url = "http://localhost:11434/v1"
api_key = "not-needed"
```

## =Ö Usage Examples

### Interactive Session

```bash
$ byom
______  ______  __  ___   ___    ____
   / __ ) \/ / __ \/  |/  /  /   |  /  _/
  / __  |\  / / / / /|_/ /  / /| |  / /
 / /_/ / / / /_/ / /  / /  / ___ |_/ /
/_____/ /_/\____/_/  /_/  /_/  |_/___/

v0.1.0

Welcome to BYOM AI Agents
  version: 0.1.0
  model: gpt-4-turbo
  cwd: /Users/you/project
  commands: /help /config /approval /model /exit

[user]> Help me add a feature to this codebase
```

### Available Commands

- `/help` - Show help information
- `/config` - Display current configuration
- `/model <name>` - Switch model
- `/approval <policy>` - Change approval policy
- `/stats` - Show session statistics
- `/tools` - List available tools
- `/mcp` - Show MCP server status
- `/save` - Save current session
- `/sessions` - List saved sessions
- `/resume <id>` - Resume a saved session
- `/checkpoint` - Create a checkpoint
- `/restore <id>` - Restore from checkpoint
- `/clear` - Clear conversation history
- `/exit` - Exit the program

## <¨ Advanced Features

### Task Management with Todos

The built-in todo system helps track multi-step tasks:

```bash
[user]> Use the todos tool to track this task
```

### Session Management

Save and resume your work:

```bash
# Save current session
[user]> /save

# List all sessions
[user]> /sessions

# Resume a previous session
[user]> /resume <session-id>
```

### Checkpoints

Create snapshots for easy rollback:

```bash
# Create checkpoint
[user]> /checkpoint

# Restore from checkpoint
[user]> /restore <checkpoint-id>
```

### MCP Integration

Add powerful MCP servers:

```toml
[mcp_servers.filesystem]
command = "npx"
args = ["-y", "@anthropic-ai/mcp-server-filesystem", "./"]

[mcp_servers.github]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-github"]
```

## =' Development

### Setup

```bash
git clone https://github.com/abhishek-dev/byom-ai-agents.git
cd byom-ai-agents
uv sync --all-extras
```

### Running Tests

```bash
uv run pytest tests/ -v --cov=src/byom
```

### Code Quality

```bash
# Linting
uv run ruff check src/

# Formatting
uv run ruff format src/

# Type checking
uv run mypy src/
```

## > Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`uv run pytest`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## =Ý License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## =O Acknowledgments

- Built with [Rich](https://github.com/Textualize/rich) for beautiful terminal UI
- Powered by [Click](https://click.palletsprojects.com/) for CLI
- Uses [Pydantic](https://pydantic-docs.helpmanual.io/) for validation
- Inspired by [Claude Code](https://claude.com/claude-code)

## = Reporting Issues

Found a bug? Have a feature request? Please open an issue on [GitHub](https://github.com/abhishek-dev/byom-ai-agents/issues).

## =ì Contact

- GitHub: [@abhishek-dev](https://github.com/abhishek-dev)
- Issues: [GitHub Issues](https://github.com/abhishek-dev/byom-ai-agents/issues)

## P Show Your Support

Give a P if this project helped you!

---

**Made with d by developers, for developers**
