# DevMind AI 🤖

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![PyPI](https://img.shields.io/pypi/v/devmind-ai.svg)

**DevMind AI** is an intelligent coding agent that brings the power of AI directly to your terminal. It provides interactive, context-aware development assistance using OpenAI, Claude, Gemini, or local models through LM Studio and Ollama.

## ✨ Features

- 🎯 **Multi-Provider Support**: Works with OpenAI, Claude (Anthropic), Gemini (Google), LM Studio, and Ollama
- 🖥️ **Terminal-First Design**: Beautiful CLI interface with rich formatting
- 🔧 **Interactive Setup Wizard**: Easy configuration with ASCII art banner
- 🛠️ **Code Operations**: Read, write, edit files with context awareness
- 🔄 **Conversation Context**: Remembers recent operations for pronoun resolution
- 📝 **Multi-Step Instructions**: Parse and execute compound tasks
- 🎨 **Rich TUI**: Syntax highlighting, progress indicators, and formatted output
- ⚡ **Fast & Efficient**: Async operations with streaming responses

## 🚀 Quick Start

### Installation

#### From PyPI (Recommended)

```bash
pip install devmind-ai
```

#### From Source

```bash
git clone https://github.com/yourusername/devmind-ai.git
cd devmind-ai
pip install -e .
```

### First Run

Simply run:

```bash
devmind
```

On first run, DevMind will launch an interactive setup wizard that will:
1. Display a welcome banner with ASCII art
2. Ask you to select your AI provider
3. Configure your API keys and endpoints
4. Save the configuration to `.env`

### Manual Setup

If you prefer to configure manually or reconfigure later:

```bash
devmind --setup
```

## 📖 Usage

### Interactive Mode

Start an interactive session:

```bash
devmind
```

### Single Prompt Mode

Execute a single task and exit:

```bash
devmind "create a Python script that sorts an array"
```

### Options

```bash
devmind --help              # Show help message
devmind --version           # Show version
devmind --setup             # Run configuration wizard
devmind --cwd /path/to/dir  # Set working directory
```

## 🔧 Configuration

### Provider Configuration

DevMind supports multiple AI providers:

#### OpenAI
```env
PROVIDER=openai
API_KEY=sk-...
BASE_URL=https://api.openai.com/v1
MODEL=gpt-4
```

#### Claude (Anthropic)
```env
PROVIDER=claude
API_KEY=sk-ant-...
BASE_URL=https://api.anthropic.com
MODEL=claude-3-5-sonnet-20241022
```

#### Gemini (Google)
```env
PROVIDER=gemini
API_KEY=...
BASE_URL=https://generativelanguage.googleapis.com
MODEL=gemini-pro
```

#### LM Studio (Local)
```env
PROVIDER=lmstudio
API_KEY=dummy
BASE_URL=http://localhost:1234/v1
MODEL=your-local-model
```

#### Ollama (Local)
```env
PROVIDER=ollama
API_KEY=dummy
BASE_URL=http://localhost:11434/v1
MODEL=codellama
```

### Manual Configuration

You can also manually edit the `.env` file in your project root or copy `.env.example`:

```bash
cp .env.example .env
# Edit .env with your settings
```

## 🎨 Features in Detail

### Context Awareness

DevMind tracks your recent file operations, enabling natural language references:

```
You: write a hello world script in Python
DevMind: [creates hello.py]

You: now edit it and add a docstring
DevMind: [edits hello.py with edit_file tool]

You: run it
DevMind: [executes python hello.py]
```

### Multi-Step Instructions

Parse complex instructions automatically:

```
You: write binary search in C++, compile it, and run it
DevMind:
  1. Creates binary_search.cpp
  2. Compiles with g++
  3. Runs the executable
```

### Available Tools

- `read_file`: Read file contents
- `write_file`: Create new files
- `edit_file`: Modify existing files
- `shell`: Execute shell commands
- And more...

## 📦 Development

### Setup Development Environment

```bash
git clone https://github.com/yourusername/devmind-ai.git
cd devmind-ai
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest tests/
```

### Code Quality

```bash
# Format code
black .

# Lint
ruff check .

# Type check
mypy .
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [OpenAI](https://openai.com/), [Anthropic Claude](https://www.anthropic.com/), and [Google Gemini](https://deepmind.google/technologies/gemini/)
- UI powered by [Rich](https://github.com/Textualize/rich)
- CLI powered by [Click](https://click.palletsprojects.com/)
- ASCII art by [pyfiglet](https://github.com/pwaller/pyfiglet)

## 📬 Contact

- GitHub: [@yourusername](https://github.com/yourusername)
- Issues: [GitHub Issues](https://github.com/yourusername/devmind-ai/issues)

---

Made with ❤️ by developers, for developers
