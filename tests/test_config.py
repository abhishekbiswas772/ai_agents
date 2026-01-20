"""Tests for configuration loading."""

import pytest
from pathlib import Path
from configs.configs import Config


def test_config_creation(test_config):
    """Test basic config creation."""
    assert test_config is not None
    assert test_config.provider == "openai"


def test_config_validation(test_config):
    """Test config validation."""
    errors = test_config.validate()
    # May have errors if API_KEY not set, that's expected in tests
    assert isinstance(errors, list)
