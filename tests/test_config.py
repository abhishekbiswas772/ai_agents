"""Tests for config module"""

import tempfile
import os
from pathlib import Path
from byom.config.config import Config, ApprovalPolicy, ModelConfig
from byom.config.loader import load_config, is_first_run


def test_config_creation():
    """Test creating a Config instance"""
    config = Config(
        model=ModelConfig(name="test-model"),
        cwd=Path("/tmp"),
        approval=ApprovalPolicy.AUTO
    )
    assert config.model.name == "test-model"
    assert config.cwd == Path("/tmp")
    assert config.approval == ApprovalPolicy.AUTO


def test_config_validate(monkeypatch):
    """Test config validation"""
    monkeypatch.setenv("API_KEY", "test-key")
    # Use a temporary directory that exists on all platforms
    with tempfile.TemporaryDirectory() as tmpdir:
        config = Config(
            model=ModelConfig(name="test-model"),
            cwd=Path(tmpdir),
            approval=ApprovalPolicy.AUTO
        )
        errors = config.validate_config()
        assert len(errors) == 0  # Should be valid


def test_config_invalid(monkeypatch):
    """Test config with invalid data"""
    monkeypatch.setenv("API_KEY", "test-key")
    config = Config(
        model=ModelConfig(name=""),  # Invalid empty name, but validate_config doesn't check this
        cwd=Path("/nonexistent"),  # This will always fail validation
        approval=ApprovalPolicy.AUTO
    )
    errors = config.validate_config()
    assert len(errors) > 0  # Should have cwd error


def test_load_config():
    """Test loading config from environment"""
    # Test loading config with a specific cwd without changing the actual working directory
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        config = load_config(cwd=tmpdir_path)
        assert config is not None
        assert isinstance(config, Config)
        # cwd gets resolved to canonical path, so compare resolved paths
        assert config.cwd == tmpdir_path.resolve()