import os
from dataclasses import dataclass


@dataclass
class AgentConfig:
    base_url: str
    api_key: str
    model: str = "gpt-4o"
    codex_bin: str | None = None

    @classmethod
    def from_env(cls) -> "AgentConfig":
        base_url = os.environ.get("OPENAI_BASE_URL")
        if not base_url:
            raise ValueError("OPENAI_BASE_URL environment variable is required")
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        return cls(
            base_url=base_url,
            api_key=api_key,
            model=os.environ.get("CODEX_MODEL", "gpt-4o"),
            codex_bin=os.environ.get("CODEX_BIN"),
        )
