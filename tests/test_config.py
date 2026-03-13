import os
import pytest
from agent.config import AgentConfig


def test_from_env_all_set(monkeypatch):
    monkeypatch.setenv("CODEX_BIN", "/usr/local/bin/codex")
    monkeypatch.setenv("CODEX_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("EVERMEMOS_BASE_URL", "http://localhost:2000")
    config = AgentConfig.from_env()
    assert config.codex_bin == "/usr/local/bin/codex"
    assert config.model == "gpt-4o-mini"
    assert config.evermemos_url == "http://localhost:2000"


def test_from_env_defaults(monkeypatch):
    monkeypatch.setenv("CODEX_BIN", "/usr/local/bin/codex")
    monkeypatch.delenv("CODEX_MODEL", raising=False)
    monkeypatch.delenv("EVERMEMOS_BASE_URL", raising=False)
    config = AgentConfig.from_env()
    assert config.model == "gpt-4o"
    assert config.evermemos_url == "http://localhost:1995"


def test_from_env_missing_codex_bin(monkeypatch):
    monkeypatch.delenv("CODEX_BIN", raising=False)
    with pytest.raises(ValueError, match="CODEX_BIN"):
        AgentConfig.from_env()
