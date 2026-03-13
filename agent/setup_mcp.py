"""Helper to verify opencode MCP configuration for EverMemOS."""

import json
from pathlib import Path

OPENCODE_CONFIG_PATH = Path("opencode.json")

REQUIRED_CONFIG = """
# Add opencode.json to your project root:

{
  "mcpServers": {
    "evermemos": {
      "command": "python",
      "args": ["-m", "mcp_server.server"]
    }
  }
}
""".strip()


def check_config() -> bool:
    if not OPENCODE_CONFIG_PATH.exists():
        print(f"opencode config not found at {OPENCODE_CONFIG_PATH}")
        print(REQUIRED_CONFIG)
        return False
    content = json.loads(OPENCODE_CONFIG_PATH.read_text())
    mcp = content.get("mcpServers", {})
    if "evermemos" not in mcp:
        print("EverMemOS MCP server not configured in opencode config.")
        print(REQUIRED_CONFIG)
        return False
    print("EverMemOS MCP server is configured in opencode.")
    return True


if __name__ == "__main__":
    check_config()
