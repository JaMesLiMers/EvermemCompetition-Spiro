import os
import pytest
from unittest.mock import patch
from codex_agent.config import AgentConfig


def test_from_env_reads_all_vars():
    env = {
        "OPENAI_BASE_URL": "https://uniapi.example.com/v1",
        "OPENAI_API_KEY": "sk-test-key",
        "CODEX_MODEL": "gpt-4o",
        "CODEX_BIN": "/usr/local/bin/codex",
    }
    with patch.dict(os.environ, env, clear=False):
        config = AgentConfig.from_env()
        assert config.base_url == "https://uniapi.example.com/v1"
        assert config.api_key == "sk-test-key"
        assert config.model == "gpt-4o"
        assert config.codex_bin == "/usr/local/bin/codex"


def test_from_env_defaults():
    env = {
        "OPENAI_BASE_URL": "https://uniapi.example.com/v1",
        "OPENAI_API_KEY": "sk-test-key",
    }
    with patch.dict(os.environ, env, clear=True):
        config = AgentConfig.from_env()
        assert config.model == "gpt-4o"  # default
        assert config.codex_bin is None


def test_from_env_missing_required():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="OPENAI_BASE_URL"):
            AgentConfig.from_env()
