"""Tests for utils modules"""

from byom.utils.text import count_tokens, estimate_tokens, truncate_text
from byom.utils.paths import resolve_path
from pathlib import Path


def test_count_tokens():
    """Test token counting"""
    text = "Hello world"
    tokens = count_tokens(text)
    assert isinstance(tokens, int)
    assert tokens > 0


def test_estimate_tokens():
    """Test token estimation"""
    text = "This is a test string"
    tokens = estimate_tokens(text)
    assert tokens == max(1, len(text) // 4)


def test_truncate_text():
    """Test text truncation"""
    text = "This is a long text that should be truncated"
    truncated = truncate_text(text, "gpt-4", 5)
    assert len(truncated) < len(text)
    assert "[truncated]" in truncated


def test_resolve_path():
    """Test path resolution"""
    import platform
    cwd = Path("/tmp")
    path = resolve_path(cwd, "test.txt")
    assert path.is_absolute()
    if platform.system() == "Darwin":  # macOS
        assert str(path) == "/private/tmp/test.txt"
    elif platform.system() == "Linux":
        assert str(path) == "/tmp/test.txt"
    elif platform.system() == "Windows":
        # On Windows, /tmp gets resolved to something like C:\tmp\test.txt
        assert str(path).endswith("tmp\\test.txt") or str(path).endswith("tmp/test.txt")
        assert path.is_absolute()