"""Helper to verify Codex MCP configuration for EverMemOS."""
from pathlib import Path

CODEX_CONFIG_PATH = Path.home() / ".codex" / "config.toml"

REQUIRED_CONFIG = """
# Add this to ~/.codex/config.toml:

[mcp_servers.evermemos]
command = "python"
args = ["-m", "mcp_server.server"]
""".strip()


def check_config() -> bool:
    if not CODEX_CONFIG_PATH.exists():
        print(f"Codex config not found at {CODEX_CONFIG_PATH}")
        print(REQUIRED_CONFIG)
        return False
    content = CODEX_CONFIG_PATH.read_text()
    if "mcp_servers" not in content or "evermemos" not in content:
        print("EverMemOS MCP server not configured in Codex config.")
        print(REQUIRED_CONFIG)
        return False
    print("EverMemOS MCP server is configured in Codex.")
    return True


if __name__ == "__main__":
    check_config()
