"""Tests for CLI module"""

import pytest
from click.testing import CliRunner
from byom.cli import main


def test_main_version():
    """Test --version flag"""
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "Version: 0.1.0" in result.output


def test_main_no_args(monkeypatch):
    """Test main with no args (starts interactive mode with valid config)"""
    # Set API_KEY environment variable - this is the key fix for GitHub Actions
    monkeypatch.setenv("API_KEY", "test-key")
    
    # Also set the default api_key_env variable to ensure compatibility
    monkeypatch.setenv("API_KEY", "test-key")
    
    # Mock the first run check to avoid setup wizard
    import byom.cli
    original_is_first_run = byom.cli.is_first_run
    byom.cli.is_first_run = lambda: False
    
    # Mock the config validation to ensure it passes in CI environments
    from byom.config.config import Config
    original_validate = Config.validate_config
    
    def mock_validate(self):
        # Ensure validation passes by returning empty errors list
        return []
    
    Config.validate_config = mock_validate
    
    try:
        runner = CliRunner()
        result = runner.invoke(main, [])
        # Should start interactive mode successfully
        assert result.exit_code == 0
        # Check for the figlet banner which is shown in the output
        assert "v0.1.0" in result.output
    finally:
        # Restore original functions
        Config.validate_config = original_validate
        byom.cli.is_first_run = original_is_first_run