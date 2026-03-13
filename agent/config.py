import os
import shutil
from dataclasses import dataclass


@dataclass
class AgentConfig:
    agent_bin: str
    model: str = "opencode/gpt-5-nano"
    evermemos_url: str = "http://localhost:1995"

    @classmethod
    def from_env(cls) -> "AgentConfig":
        agent_bin = os.environ.get("AGENT_BIN") or shutil.which("opencode")
        if not agent_bin:
            raise ValueError("AGENT_BIN environment variable is required or opencode must be on PATH")
        return cls(
            agent_bin=agent_bin,
            model=os.environ.get("AGENT_MODEL", "opencode/gpt-5-nano"),
            evermemos_url=os.environ.get("EVERMEMOS_BASE_URL", "http://localhost:1995"),
        )
