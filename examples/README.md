# BYOM AI Agents - Examples

This directory contains usage examples for BYOM AI Agents.

## Examples

### Basic Usage (`basic_usage.py`)

Demonstrates basic programmatic usage of BYOM:
- Creating a config
- Running an agent
- Processing events

```bash
python examples/basic_usage.py
```

### Custom Provider (`custom_provider.py`)

Shows how to use different LLM providers:
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Ollama (Local models)

```bash
# Make sure you have API keys set
export OPENAI_API_KEY=your-key
export ANTHROPIC_API_KEY=your-key

python examples/custom_provider.py
```

## CLI Examples

### Interactive Mode

Start an interactive session:

```bash
byom
```

### Single Query

Run a single query:

```bash
byom "Create a simple Python script that prints Hello World"
```

### Project-Specific

Run in a specific project directory:

```bash
byom --cwd /path/to/your/project "Analyze this codebase"
```

## Configuration Examples

### Minimal Config

```toml
# ~/.config/byom-ai/config.toml
[model]
name = "gpt-4-turbo"

[api]
# Set via environment: export OPENAI_API_KEY=your-key
```

### Full Config

```toml
# ~/.config/byom-ai/config.toml
[model]
name = "gpt-4-turbo"
provider = "openai"
temperature = 0.7
max_tokens = 4096

[api]
# Use environment variables for API keys

[behavior]
approval_policy = "auto"
max_turns = 25
auto_save = true

[hooks]
enabled = false

[mcp]
enabled = true

[mcp_servers.filesystem]
command = "npx"
args = ["-y", "@anthropic-ai/mcp-server-filesystem", "./"]
```

### Project Config

Create `.byom/config.toml` in your project:

```toml
# .byom/config.toml
[model]
# Override system config for this project
name = "gpt-3.5-turbo"
temperature = 0.5

[behavior]
# Require approval for file operations in this project
approval_policy = "on-request"
```

## Advanced Usage

### Using Tools

```python
from byom import Agent, Config
from byom.agent.events import AgentEventType

async def use_tools_example():
    config = Config(model_name="gpt-4-turbo", cwd=Path.cwd())

    async with Agent(config) as agent:
        async for event in agent.run("Search for TODO comments in all Python files"):
            if event.type == AgentEventType.TOOL_CALL_START:
                tool = event.data.get("name")
                args = event.data.get("arguments")
                print(f"Using: {tool} with {args}")
```

### Session Persistence

```python
# Save session
await persistence_manager.save_session(session_snapshot)

# Load session
snapshot = await persistence_manager.load_session(session_id)
```

## Tips

1. **API Keys**: Always use environment variables for API keys, never hardcode them
2. **Testing**: Use cheaper models like GPT-3.5 for testing
3. **Approval**: Set `approval_policy = "on-request"` when learning
4. **Logs**: Check `~/.local/share/byom-ai/logs/` for debugging

## More Information

- [Main README](../README.md)
- [Configuration Guide](../docs/configuration.md)
- [Contributing](../CONTRIBUTING.md)
