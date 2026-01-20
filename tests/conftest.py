"""Pytest configuration and fixtures for DevMind AI tests."""

import pytest
from pathlib import Path
from configs.configs import Config


@pytest.fixture
def test_config():
    """Provide a test configuration."""
    return Config(
        cwd=Path.cwd(),
        provider="openai"
    )


@pytest.fixture
def temp_env_file(tmp_path):
    """Create a temporary .env file for testing."""
    env_file = tmp_path / ".env"
    env_file.write_text("""
PROVIDER=openai
API_KEY=test-key
BASE_URL=https://api.openai.com/v1
MODEL=gpt-4
""")
    return env_file
