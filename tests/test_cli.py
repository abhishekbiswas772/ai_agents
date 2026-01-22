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


def test_main_no_args():
    """Test main with no args (starts interactive mode)"""
    runner = CliRunner()
    # Since it's interactive, it will show the banner and exit
    result = runner.invoke(main, [], input="\n")  # Send newline to exit
    assert result.exit_code == 0
    assert "BYOM AI Agents" in result.output