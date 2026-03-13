# tests/test_cli.py
from unittest.mock import patch, MagicMock
from codex_agent.cli import main, TASK_REGISTRY


def test_task_registry_has_all_tasks():
    assert "relationships" in TASK_REGISTRY
    assert "profiling" in TASK_REGISTRY
    assert "timeline" in TASK_REGISTRY
    assert "suggestions" in TASK_REGISTRY


def test_main_calls_runner(capsys):
    with patch("codex_agent.cli.TaskRunner") as MockRunner:
        mock_runner = MagicMock()
        mock_runner.run.return_value = "Analysis result"
        MockRunner.return_value = mock_runner

        with patch("codex_agent.cli.AgentConfig.from_env") as mock_config:
            mock_config.return_value = MagicMock()
            main(["relationships", "--user-id", "user_001"])

        captured = capsys.readouterr()
        assert "Analysis result" in captured.out
