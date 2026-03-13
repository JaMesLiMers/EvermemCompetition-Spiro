# codex_agent/runner.py
from codex_app_server import AppServerClient, AppServerConfig
from codex_app_server.generated.v2_all import ThreadStartParams

from .config import AgentConfig
from .tasks.base import BaseTask


class TaskRunner:
    def __init__(self, config: AgentConfig):
        self.config = config

    def _build_app_server_config(self) -> AppServerConfig:
        env = {
            "OPENAI_BASE_URL": self.config.base_url,
            "OPENAI_API_KEY": self.config.api_key,
        }
        # Forward CODEX_HOME if set, so Codex reads local config.toml
        import os
        codex_home = os.environ.get("CODEX_HOME")
        if codex_home:
            env["CODEX_HOME"] = codex_home
        return AppServerConfig(
            codex_bin=self.config.codex_bin,
            env=env,
        )

    def run(self, task: BaseTask) -> str:
        app_config = self._build_app_server_config()
        with AppServerClient(config=app_config) as client:
            client.initialize()
            thread = client.thread_start(ThreadStartParams(
                model=self.config.model,
                developer_instructions=task.system_prompt,
            ))
            prompt = task.build_prompt()
            # stream_text handles turn_start + delta collection + wait for completion
            chunks = []
            for delta in client.stream_text(thread.thread.id, prompt):
                chunks.append(delta.delta)
            raw = "".join(chunks)
            return task.parse_output(raw)
