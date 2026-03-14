import os
import shutil
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv() -> None:
    """Load .env file from project root if environment vars are not set."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip()
            if key and key not in os.environ:
                os.environ[key] = value


@dataclass
class AgentConfig:
    agent_bin: str
    model: str = "anthropic/claude-sonnet-4-6"
    evermemos_url: str = "http://localhost:1995"

    @classmethod
    def from_env(cls) -> "AgentConfig":
        _load_dotenv()
        agent_bin = os.environ.get("AGENT_BIN") or shutil.which("opencode")
        if not agent_bin:
            raise ValueError("AGENT_BIN environment variable is required or opencode must be on PATH")
        return cls(
            agent_bin=agent_bin,
            model=os.environ.get("AGENT_MODEL", "anthropic/claude-sonnet-4-6"),
            evermemos_url=os.environ.get("EVERMEMOS_BASE_URL", "http://localhost:1995"),
        )
