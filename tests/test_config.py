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
    config = Config(
        model=ModelConfig(name="test-model"),
        cwd=Path("/tmp"),
        approval=ApprovalPolicy.AUTO
    )
    errors = config.validate_config()
    assert len(errors) == 0  # Should be valid


def test_config_invalid(monkeypatch):
    """Test config with invalid data"""
    monkeypatch.setenv("API_KEY", "test-key")
    config = Config(
        model=ModelConfig(name=""),  # Invalid empty name, but validate_config doesn't check this
        cwd=Path("/nonexistent"),
        approval=ApprovalPolicy.AUTO
    )
    errors = config.validate_config()
    assert len(errors) > 0  # Should have cwd error


def test_load_config():
    """Test loading config from environment"""
    # This might require setting env vars, but for basic test, assume default
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        config = load_config(cwd=Path(tmpdir))
        assert config is not None
        assert isinstance(config, Config)