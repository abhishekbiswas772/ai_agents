# Contributing to BYOM AI Agents

Thank you for considering contributing to BYOM AI Agents! This document provides guidelines and instructions for contributing.

## 🎯 Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone.

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Git

### Development Setup

1. **Fork and Clone**

```bash
git clone https://github.com/YOUR_USERNAME/byom-ai-agents.git
cd byom-ai-agents
```

2. **Install Dependencies**

```bash
uv sync --all-extras
```

Or with pip:

```bash
pip install -e ".[dev]"
```

3. **Set Up API Keys**

Create a `.env` file:

```bash
OPENAI_API_KEY=your-key
ANTHROPIC_API_KEY=your-key
```

4. **Run Tests**

```bash
uv run pytest tests/ -v
```

## 📋 How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/abhishek-dev/byom-ai-agents/issues)
2. If not, create a new issue with:
   - Clear, descriptive title
   - Steps to reproduce
   - Expected vs actual behavior
   - System information (OS, Python version, etc.)
   - Relevant logs or screenshots

### Suggesting Enhancements

1. Check if the enhancement has already been suggested
2. Create a new issue with:
   - Clear description of the feature
   - Use cases and benefits
   - Possible implementation approach
   - Any relevant examples

### Pull Requests

1. **Create a Branch**

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

2. **Make Changes**

- Follow the existing code style
- Add tests for new functionality
- Update documentation as needed
- Keep commits focused and atomic

3. **Test Your Changes**

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_providers.py -v

# Run with coverage
uv run pytest tests/ --cov=src/byom --cov-report=term-missing
```

4. **Lint and Format**

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

5. **Commit Changes**

Use clear, descriptive commit messages:

```bash
git commit -m "Add: Feature description"
git commit -m "Fix: Bug description"
git commit -m "Docs: Documentation update"
git commit -m "Test: Test description"
git commit -m "Refactor: Refactoring description"
```

6. **Push and Create PR**

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub with:
- Clear description of changes
- Link to related issues
- Screenshots/examples if applicable

## 🏗️ Project Structure

```
byom-ai-agents/
├── src/byom/              # Main package
│   ├── agent/             # Agent core logic
│   ├── client/            # LLM client implementation
│   ├── config/            # Configuration management
│   ├── context/           # Context and conversation management
│   ├── providers/         # LLM provider implementations
│   ├── prompts/           # System prompts
│   ├── tools/             # Built-in tools
│   │   ├── builtin/       # Core tools (read, write, shell, etc.)
│   │   └── mcp/           # MCP integration
│   ├── ui/                # Terminal UI
│   ├── utils/             # Utilities
│   ├── cli.py             # CLI entry point
│   └── setup.py           # First-run setup wizard
├── tests/                 # Test suite
├── examples/              # Usage examples
├── docs/                  # Documentation
├── .github/workflows/     # CI/CD
└── pyproject.toml         # Project configuration
```

## 📝 Coding Standards

### Python Style Guide

- Follow PEP 8
- Use type hints for function parameters and return values
- Maximum line length: 100 characters
- Use descriptive variable names

### Code Examples

```python
# Good
def process_message(
    message: str,
    model_name: str,
    max_tokens: int = 1000,
) -> dict[str, Any]:
    """
    Process a user message and generate a response.

    Args:
        message: The user's input message
        model_name: Name of the LLM model to use
        max_tokens: Maximum tokens in response

    Returns:
        Dictionary containing the response and metadata
    """
    # Implementation here
    pass

# Bad
def proc(msg, model, tokens=1000):
    # No docstring, no types
    pass
```

### Documentation

- Add docstrings to all public functions, classes, and modules
- Use Google-style docstring format
- Update README.md for user-facing changes
- Add code comments for complex logic

### Testing

- Write tests for all new features
- Maintain or improve code coverage
- Use descriptive test names
- Group related tests in classes

```python
# Example test
import pytest
from byom.tools.builtin.find import FindTool

class TestFindTool:
    def test_find_python_files(self, tmp_path):
        """Test finding Python files in a directory"""
        # Setup
        (tmp_path / "test.py").touch()
        (tmp_path / "test.txt").touch()

        # Execute
        tool = FindTool(config)
        result = tool.execute(
            {"path": str(tmp_path), "pattern": "*.py"},
            cwd=tmp_path
        )

        # Assert
        assert result.success
        assert "test.py" in result.output
        assert "test.txt" not in result.output
```

## 🔍 Code Review Process

All pull requests will be reviewed for:

1. **Functionality**: Does it work as intended?
2. **Tests**: Are there adequate tests?
3. **Code Quality**: Is the code clean and maintainable?
4. **Documentation**: Is it well-documented?
5. **Breaking Changes**: Are they necessary and well-communicated?

## 🎯 Areas for Contribution

### High Priority

- [ ] Additional LLM providers (Cohere, Together AI, etc.)
- [ ] Enhanced test coverage
- [ ] Performance optimizations
- [ ] Documentation improvements

### Medium Priority

- [ ] More built-in tools
- [ ] TUI enhancements
- [ ] Better error messages
- [ ] Integration examples

### Low Priority

- [ ] VS Code extension
- [ ] Web UI option
- [ ] Plugin system
- [ ] Telemetry (optional, opt-in)

## 🐛 Debugging

### Running in Debug Mode

```python
# Add to your config
[debug]
enabled = true
log_level = "DEBUG"
```

### Viewing Logs

```bash
tail -f ~/.local/share/byom-ai/logs/byom.log
```

## 📚 Resources

- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Pytest Documentation](https://docs.pytest.org/)
- [Rich Documentation](https://rich.readthedocs.io/)
- [Pydantic Documentation](https://docs.pydantic.dev/)

## 💬 Getting Help

- **Questions**: Open a [Discussion](https://github.com/abhishek-dev/byom-ai-agents/discussions)
- **Bugs**: Open an [Issue](https://github.com/abhishek-dev/byom-ai-agents/issues)
- **Security**: Email security concerns privately

## 🎉 Recognition

Contributors will be:
- Listed in README.md
- Mentioned in release notes
- Given credit in commit history

Thank you for contributing to BYOM AI Agents! 🚀
