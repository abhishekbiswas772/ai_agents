"""Tests for builtin tools"""

import tempfile
import os
import pytest
from pathlib import Path
from byom.tools.builtin.list_dir import ListDirTool
from byom.tools.builtin.read_file import ReadFileTool
from byom.tools.builtin.write_file import WriteFileTool
from byom.tools.base import ToolInvocation
from byom.config.config import Config, ApprovalPolicy


@pytest.fixture
def test_config():
    return Config(
        model_name="test",
        api_key="test",
        cwd=Path("/tmp"),
        approval_policy=ApprovalPolicy.AUTO
    )


@pytest.mark.asyncio
async def test_list_dir_tool(test_config):
    """Test list_dir tool"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        # Create some files
        (tmpdir_path / "file1.txt").touch()
        (tmpdir_path / "file2.txt").touch()
        os.mkdir(tmpdir_path / "subdir")

        tool = ListDirTool(test_config)
        invocation = ToolInvocation(params={"path": tmpdir}, cwd=tmpdir_path)
        result = await tool.execute(invocation)
        assert result.success
        assert "file1.txt" in result.output
        assert "file2.txt" in result.output
        assert "subdir/" in result.output


@pytest.mark.asyncio
async def test_read_file_tool(test_config):
    """Test read_file tool"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        test_file = tmpdir_path / "test.txt"
        test_content = "Hello, world!"
        test_file.write_text(test_content)

        tool = ReadFileTool(test_config)
        invocation = ToolInvocation(params={"path": str(test_file)}, cwd=tmpdir_path)
        result = await tool.execute(invocation)
        assert result.success
        assert test_content in result.output


@pytest.mark.asyncio
async def test_write_file_tool(test_config):
    """Test write_file tool"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        test_file = tmpdir_path / "test.txt"
        content = "New content"

        tool = WriteFileTool(test_config)
        invocation = ToolInvocation(params={"path": str(test_file), "content": content}, cwd=tmpdir_path)
        result = await tool.execute(invocation)
        assert result.success
        assert "created" in result.output.lower()

        # Check file was created
        assert test_file.exists()
        assert test_file.read_text() == content