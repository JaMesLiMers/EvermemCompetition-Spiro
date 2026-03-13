import pytest

from agent.config import AgentConfig


def test_from_env_all_set(monkeypatch):
    monkeypatch.setenv("AGENT_BIN", "/usr/local/bin/opencode")
    monkeypatch.setenv("AGENT_MODEL", "opencode/gpt-5-nano")
    monkeypatch.setenv("EVERMEMOS_BASE_URL", "http://localhost:2000")
    config = AgentConfig.from_env()
    assert config.agent_bin == "/usr/local/bin/opencode"
    assert config.model == "opencode/gpt-5-nano"
    assert config.evermemos_url == "http://localhost:2000"


def test_from_env_defaults(monkeypatch):
    monkeypatch.setenv("AGENT_BIN", "/usr/local/bin/opencode")
    monkeypatch.delenv("AGENT_MODEL", raising=False)
    monkeypatch.delenv("EVERMEMOS_BASE_URL", raising=False)
    config = AgentConfig.from_env()
    assert config.model == "opencode/gpt-5-nano"
    assert config.evermemos_url == "http://localhost:1995"


def test_from_env_auto_detect(monkeypatch):
    monkeypatch.delenv("AGENT_BIN", raising=False)
    # Should auto-detect opencode from PATH via shutil.which
    # If opencode is not on PATH, this will raise ValueError
    import shutil

    if shutil.which("opencode"):
        config = AgentConfig.from_env()
        assert "opencode" in config.agent_bin
    else:
        with pytest.raises(ValueError, match="AGENT_BIN"):
            AgentConfig.from_env()
