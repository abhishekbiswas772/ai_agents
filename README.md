# BYOM AI Agents

**Bring Your Own Model** - A terminal-based AI coding agent that works with ANY LLM provider.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

## 🎯 What is BYOM AI Agents?

BYOM AI Agents is a powerful, terminal-based AI coding assistant that puts YOU in control. Unlike other AI coding tools that lock you into a single provider, BYOM lets you:

- **Use Any LLM**: OpenAI, Anthropic Claude, Google Gemini, Ollama, LM Studio, OpenRouter
- **Keep Your Data Private**: Run everything locally with Ollama or LM Studio
- **Stay Flexible**: Switch between providers without changing your workflow
- **Work Your Way**: Terminal-first interface with rich formatting and progress indicators

## ✨ Features

### 🔌 Universal LLM Support (BYOM!)

**Cloud Providers:**
- **OpenAI**: GPT-4, GPT-4 Turbo, GPT-3.5
- **Anthropic**: Claude 3.5 Sonnet, Opus, Haiku
- **Google AI**: Gemini Pro, Gemini 1.5 Pro
- **OpenRouter**: Access 200+ models through one API (GPT-4, Claude, Llama, Mistral, etc.)

**Local Providers (Privacy-First!):**
- **🏠 Ollama**: Run Llama 3, Mistral, CodeLlama, DeepSeek, and 100+ models locally
- **🏠 LM Studio**: Local models with a beautiful GUI
- **🏠 Any OpenAI-compatible server**: vLLM, LocalAI, etc.

**Smart Features:**
- ✅ **Auto-detection**: Automatic provider selection based on model name
- ✅ **Easy Setup**: Interactive wizard guides you through configuration
- ✅ **Flexible**: Switch providers anytime without changing your workflow
- ✅ **No lock-in**: Your data, your models, your choice

### 🛠️ Powerful Built-in Tools

- **File Operations**: Read, write, edit files with smart diff display
- **Search & Navigation**: Grep, glob, and recursive file finding
- **Shell Integration**: Execute commands with approval workflows
- **Web Research**: Built-in web search and URL fetching
- **Task Management**: Persistent todos with status tracking
- **Memory System**: Remember user preferences across sessions
- **MCP Support**: Integrate Model Context Protocol servers

### 💡 Smart Features

- **Context Management**: Automatic conversation compression when needed
- **Loop Detection**: Prevents the agent from getting stuck
- **Approval Policies**: Control which actions require confirmation
- **Session Persistence**: Save and resume conversations
- **Checkpoints**: Create snapshots of your work
- **Rich TUI**: Beautiful terminal UI with syntax highlighting

## 📦 Installation

### Windows

```bash
# Step 1: Install BYOM
pip install byom-ai-agents

# Step 2: Setup PATH (Windows only)
python -m byom.setup_path
```

> **⚠️ Important**: After running `setup_path`, **restart your terminal** for the `byom` command to work.

**Verify Installation:**
```bash
byom --version
```

### Linux/Mac

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

## 🚀 Quick Start

### First Run - Interactive Setup

When you first run BYOM, you'll see an interactive setup wizard:

```bash
byom
```

The wizard will help you:
1. Choose your LLM provider (Ollama, LM Studio, OpenRouter, OpenAI, Anthropic, Google)
2. Configure API keys or local server settings
3. Select your preferred model
4. Set approval policies
5. Create all necessary config files

### Provider-Specific Setup

#### 🏠 Ollama (Recommended for Local/Privacy)

```bash
# 1. Install Ollama
# Download from: https://ollama.ai

# 2. Pull a model
ollama pull llama3

# 3. Run BYOM (Ollama runs automatically on localhost:11434)
byom
```

#### 🏠 LM Studio

```bash
# 1. Download LM Studio from https://lmstudio.ai
# 2. Download and load a model in the app
# 3. Start the local server (Server tab in LM Studio)
# 4. Run BYOM
byom
```

#### ☁️ OpenRouter

```bash
# 1. Get API key from https://openrouter.ai/keys
# 2. Set environment variable
export OPENROUTER_API_KEY=your-key-here

# 3. Run BYOM
byom
```

#### ☁️ OpenAI

```bash
export OPENAI_API_KEY=your-key-here
byom
```

#### ☁️ Anthropic

```bash
export ANTHROPIC_API_KEY=your-key-here
byom
```

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

### Troubleshooting (Windows)

**"byom is not recognized as a command"**

If you installed with pip and didn't run the setup script:

```bash
# Run the PATH setup script
python -m byom.setup_path

# Then restart your terminal
```

**Alternative: Run without PATH setup**

You can always run BYOM without adding to PATH:

```bash
python -m byom.cli
```

## ⚙️ Configuration

BYOM uses a layered configuration system:

1. **System Config**: `~/.config/byom-ai/config.toml`
2. **Project Config**: `.byom/config.toml` in your project
3. **Environment Variables**: Override with env vars

### Example Configurations

#### Ollama (Local)

```toml
# ~/.config/byom-ai/config.toml

[model]
name = "llama3"
provider = "openai"  # Ollama uses OpenAI-compatible API
temperature = 0.7

[api]
base_url = "http://localhost:11434/v1"
# No API key needed for local!

[behavior]
approval_policy = "auto"
max_turns = 25
```

#### LM Studio (Local)

```toml
[model]
name = "local-model"  # Whatever you've loaded
provider = "openai"

[api]
base_url = "http://localhost:1234/v1"
# No API key needed!

[behavior]
approval_policy = "auto"
```

#### OpenRouter

```toml
[model]
name = "anthropic/claude-3.5-sonnet"
provider = "openai"

[api]
base_url = "https://openrouter.ai/api/v1"
# Set via env: export OPENROUTER_API_KEY=your-key

[behavior]
approval_policy = "auto"
```

#### OpenAI

```toml
[model]
name = "gpt-4-turbo"
provider = "openai"

# API key via environment variable:
# export OPENAI_API_KEY=your-key

[behavior]
approval_policy = "auto"
```

## 🔑 Environment Variables

All providers support environment variables for API keys:

```bash
# OpenAI
export OPENAI_API_KEY=sk-...

# Anthropic
export ANTHROPIC_API_KEY=sk-ant-...

# Google
export GOOGLE_API_KEY=...

# OpenRouter
export OPENROUTER_API_KEY=sk-or-...

# Local providers (Ollama, LM Studio) don't need API keys!
```

## 📚 Available Models

### Ollama (Local)
- `llama3`, `llama3:70b` - Meta's Llama 3
- `codellama`, `codellama:34b` - Code-specialized Llama
- `mistral`, `mixtral` - Mistral AI models
- `deepseek-coder` - DeepSeek's coding model
- `qwen2.5-coder` - Qwen coding model
- `phi3` - Microsoft's Phi-3
- And 100+ more at https://ollama.ai/library

### OpenRouter (Cloud)
- `anthropic/claude-3.5-sonnet` - Claude 3.5 Sonnet
- `openai/gpt-4-turbo` - GPT-4 Turbo
- `google/gemini-pro-1.5` - Gemini 1.5 Pro
- `meta-llama/llama-3-70b-instruct` - Llama 3 70B
- `mistralai/mixtral-8x7b-instruct` - Mixtral 8x7B
- `deepseek/deepseek-coder` - DeepSeek Coder
- Browse all 200+ models at https://openrouter.ai/models

### OpenAI
- `gpt-4-turbo`, `gpt-4`, `gpt-3.5-turbo`

### Anthropic
- `claude-3-5-sonnet-20241022`, `claude-3-opus-20240229`, `claude-3-haiku-20240307`

### Google AI
- `gemini-pro`, `gemini-1.5-pro`, `gemini-1.5-flash`

## 📖 Usage Examples

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
  model: llama3 (via Ollama)
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

## 💰 Cost Comparison

| Provider | Type | Cost | Privacy | Models |
|----------|------|------|---------|--------|
| **Ollama** | 🏠 Local | FREE | ⭐⭐⭐⭐⭐ | 100+ |
| **LM Studio** | 🏠 Local | FREE | ⭐⭐⭐⭐⭐ | Any GGUF |
| **OpenRouter** | ☁️ Cloud | Pay-as-you-go | ⭐⭐⭐ | 200+ |
| **OpenAI** | ☁️ Cloud | $$$ | ⭐⭐ | GPT models |
| **Anthropic** | ☁️ Cloud | $$$ | ⭐⭐ | Claude models |

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🐛 Reporting Issues

Found a bug? Have a feature request? Please open an issue on [GitHub](https://github.com/abhishek-dev/byom-ai-agents/issues).

## ⭐ Show Your Support

Give a ⭐️ if this project helped you!

---

**Made with ❤️ by developers, for developers**
