# shared/

Shared utilities used across all Spiro modules (agent, ingestion, app).

## EverMemOS API Client (`evermemos_api.py`)

Async HTTP client for the EverMemOS REST API built on **httpx**. A single `httpx.AsyncClient` instance is held for the lifetime of the client, giving automatic connection pooling and keep-alive reuse across requests.

Supports use as an async context manager (`async with`) or manual lifecycle via `close()`.

```python
from shared.evermemos_api import EverMemosClient

async with EverMemosClient(base_url="http://localhost:1995") as client:
    result = await client.store_message(content="Hello", sender="user_1")
    memories = await client.get_memories(user_id="user_1")
    hits = await client.search_memory(query="morning routine", retrieve_method="keyword")
```

### Methods

| Method | Parameters | Return | Description |
|--------|-----------|--------|-------------|
| `__init__` | `base_url: str = "http://localhost:1995"` | `None` | Create client with shared `httpx.AsyncClient` (30 s timeout). |
| `close` | -- | `None` | Close the underlying HTTP client. |
| `store_message` | `content: str, sender: str, message_id: str \| None, create_time: str \| None, sender_name: str \| None, group_id: str \| None, group_name: str \| None, role: str = "user"` | `dict` | Store a single message. Auto-generates `message_id` (UUID4) and `create_time` (UTC ISO) when omitted. |
| `create_conversation_meta` | `group_id: str, name: str, scene: str, scene_desc: dict, user_details: dict, created_at: str, default_timezone: str = "Asia/Shanghai"` | `dict` | Create or update conversation metadata for a group. |
| `search_memory` | `query: str \| None, user_id: str \| None, group_id: str \| None, retrieve_method: str = "keyword", memory_types: list[str] \| None, top_k: int = 40, start_time: str \| None, end_time: str \| None` | `dict` | Search memories by keyword or other retrieve method. Defaults to `["episodic_memory"]`. |
| `get_memories` | `user_id: str \| None, group_id: str \| None, memory_type: str = "episodic_memory", limit: int = 40, offset: int = 0, start_time: str \| None, end_time: str \| None` | `dict` | Fetch memories by type with pagination and optional time range. |
| `get_conversation_meta` | `group_id: str \| None` | `dict` | Get conversation metadata, optionally filtered by group. |
| `delete_memories` | `event_id: str \| None, user_id: str \| None, group_id: str \| None` | `dict` | Delete memories matching the given filters (AND logic). |
