# tests/test_runner.py
from unittest.mock import MagicMock, patch
from codex_agent.config import AgentConfig
from codex_agent.runner import TaskRunner
from codex_agent.tasks.base import BaseTask


def _make_config():
    return AgentConfig(
        base_url="https://uniapi.example.com/v1",
        api_key="sk-test",
        model="gpt-4o",
        codex_bin="/usr/local/bin/codex",
    )


def _make_task():
    return BaseTask(
        name="test",
        system_prompt="You are a test agent.",
        user_prompt_template="Analyze user {user_id}.",
        user_id="user_001",
    )


def test_runner_creates_app_server_config():
    """TaskRunner should build AppServerConfig with correct env and codex_bin."""
    config = _make_config()
    runner = TaskRunner(config)
    app_config = runner._build_app_server_config()
    assert app_config.env["OPENAI_BASE_URL"] == "https://uniapi.example.com/v1"
    assert app_config.env["OPENAI_API_KEY"] == "sk-test"
    assert app_config.codex_bin == "/usr/local/bin/codex"


def test_runner_run_calls_sdk_lifecycle():
    """TaskRunner.run() should call initialize, thread_start, turn_start, and collect deltas."""
    config = _make_config()
    runner = TaskRunner(config)
    task = _make_task()

    # Mock the SDK client
    mock_client = MagicMock()
    mock_thread_resp = MagicMock()
    mock_thread_resp.thread.id = "thread_123"
    mock_client.thread_start.return_value = mock_thread_resp

    mock_turn_resp = MagicMock()
    mock_turn_resp.turn.id = "turn_456"
    mock_client.turn_start.return_value = mock_turn_resp

    # Mock stream_text to yield delta notifications
    mock_delta1 = MagicMock()
    mock_delta1.delta = "Hello "
    mock_delta2 = MagicMock()
    mock_delta2.delta = "World"
    mock_client.stream_text.return_value = iter([mock_delta1, mock_delta2])

    with patch("codex_agent.runner.AppServerClient") as MockClientClass:
        MockClientClass.return_value.__enter__ = MagicMock(return_value=mock_client)
        MockClientClass.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.run(task)

    assert result == "Hello World"
    mock_client.initialize.assert_called_once()
    mock_client.thread_start.assert_called_once()
