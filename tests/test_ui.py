"""Tests for UI module"""

from byom.ui.tui import TUI
from byom.config.config import Config, ApprovalPolicy, ModelConfig
from pathlib import Path


def test_tui_creation():
    """Test creating TUI instance"""
    config = Config(
        model=ModelConfig(name="test"),
        cwd=Path("/tmp"),
        approval=ApprovalPolicy.AUTO
    )
    tui = TUI(config)
    assert tui.config == config
    assert tui.cwd == Path("/tmp")


def test_ordered_args():
    """Test _ordered_args method"""
    config = Config(
        model=ModelConfig(name="test"),
        cwd=Path("/tmp"),
        approval=ApprovalPolicy.AUTO
    )
    tui = TUI(config)

    args = {"path": "/tmp", "pattern": "*.txt", "other": "value"}
    ordered = tui._ordered_args("glob", args)
    keys = [k for k, v in ordered]
    assert keys[0] == "path"  # Preferred order
    assert "pattern" in keys
    assert "other" in keys


def test_render_args_table():
    """Test _render_args_table method"""
    config = Config(
        model=ModelConfig(name="test"),
        cwd=Path("/tmp"),
        approval=ApprovalPolicy.AUTO
    )
    tui = TUI(config)

    args = {"path": "/tmp", "count": 5, "enabled": True}
    table = tui._render_args_table("test", args)
    assert table is not None
    # Since it's a Rich table, hard to test content, but ensure no error