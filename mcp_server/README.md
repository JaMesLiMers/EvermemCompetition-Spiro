# MCP Server — EverMemOS Bridge

MCP (Model Context Protocol) server that exposes the EverMemOS REST API as tools consumable by AI agents. Part of the **Spiro** project — a context-native empathic AI wearable band (EverMemOS competition submission).

## Architecture

```
EverMemOS REST API  ←──HTTP──→  MCP Server  ←──MCP Protocol──→  Agent (opencode CLI)
  (localhost:1995)               (FastMCP)                        (Claude Sonnet)
```

The server wraps every EverMemOS endpoint in an async MCP tool via `FastMCP`. The agent (running inside opencode) calls these tools transparently — no manual HTTP needed.

## Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `search_memory` | Search memories using keyword, vector, hybrid, rrf, or agentic retrieval. At least one of `user_id` or `group_id` required. | `query: str\|None`, `user_id: str\|None`, `group_id: str\|None`, `retrieve_method: str = "keyword"`, `memory_types: list[str]\|None` (episodic_memory, foresight, event_log), `top_k: int = 40`, `start_time: str\|None`, `end_time: str\|None` |
| `get_memories` | Fetch memories by type (profile, episodic_memory, foresight, event_log). At least one of `user_id` or `group_id` required. | `user_id: str\|None`, `group_id: str\|None`, `memory_type: str = "episodic_memory"`, `limit: int = 40`, `offset: int = 0`, `start_time: str\|None`, `end_time: str\|None` |
| `store_message` | Store a message into EverMemOS memory. `message_id` and `create_time` are auto-generated if omitted. | `content: str`, `sender: str`, `message_id: str\|None`, `create_time: str\|None`, `sender_name: str\|None`, `group_id: str\|None`, `group_name: str\|None`, `role: str = "user"` |
| `get_conversation_meta` | Get conversation metadata from EverMemOS. | `group_id: str\|None` |
| `delete_memories` | Delete memories by filter criteria (AND logic). At least one filter required. | `event_id: str\|None`, `user_id: str\|None`, `group_id: str\|None` |

## Configuration

The server is registered in `opencode.json` under the `mcp` key:

```json
{
  "mcp": {
    "evermemos": {
      "type": "local",
      "command": ["python", "-m", "mcp_server.server"]
    }
  }
}
```

The EverMemOS base URL defaults to `http://localhost:1995` and can be overridden with the `EVERMEMOS_BASE_URL` environment variable.

## Dependencies

Listed in `mcp_server/requirements.txt`:

```
mcp>=1.0
httpx>=0.27
```

Install:

```bash
pip install -r mcp_server/requirements.txt
```

The server also imports `shared.evermemos_api.EverMemosClient` from the project's shared module.

## Running Standalone

```bash
python -m mcp_server.server
```

In normal usage the opencode CLI launches the server automatically based on the config above.
