"""Basic tests for BYOM AI Agents"""

def test_import_cli():
    """Test that cli module can be imported"""
    import byom.cli
    assert byom.cli is not None

def test_import_agent():
    """Test that agent module can be imported"""
    import byom.agent.agent
    assert byom.agent.agent is not None

def test_version():
    """Test that version is defined"""
    from byom import __version__
    assert __version__ is not None
    assert isinstance(__version__, str)