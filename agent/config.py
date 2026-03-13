import os
from dataclasses import dataclass


@dataclass
class AgentConfig:
    codex_bin: str
    model: str = "gpt-4o"
    evermemos_url: str = "http://localhost:1995"

    @classmethod
    def from_env(cls) -> "AgentConfig":
        codex_bin = os.environ.get("CODEX_BIN")
        if not codex_bin:
            raise ValueError("CODEX_BIN environment variable is required")
        return cls(
            codex_bin=codex_bin,
            model=os.environ.get("CODEX_MODEL", "gpt-4o"),
            evermemos_url=os.environ.get("EVERMEMOS_BASE_URL", "http://localhost:1995"),
        )
