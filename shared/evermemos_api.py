import httpx
import uuid
from datetime import datetime, timezone


class EverMemosClient:
    """Async HTTP client for EverMemOS REST API.

    Uses a shared httpx.AsyncClient for connection reuse. Use as async context manager
    or call close() explicitly.
    """

    def __init__(self, base_url: str = "http://localhost:1995"):
        self.base_url = base_url.rstrip("/")
        self.api_prefix = f"{self.base_url}/api/v1/memories"
        self._client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self.close()

    async def store_message(
        self,
        content: str,
        sender: str,
        message_id: str | None = None,
        create_time: str | None = None,
        sender_name: str | None = None,
        group_id: str | None = None,
        group_name: str | None = None,
        role: str = "user",
    ) -> dict:
        """Store a single message. Auto-generates message_id and create_time if omitted."""
        payload = {
            "message_id": message_id or str(uuid.uuid4()),
            "create_time": create_time or datetime.now(timezone.utc).isoformat(),
            "sender": sender,
            "sender_name": sender_name or sender,
            "content": content,
            "role": role,
        }
        if group_id:
            payload["group_id"] = group_id
        if group_name:
            payload["group_name"] = group_name

        resp = await self._client.post(
            self.api_prefix,
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()

    async def create_conversation_meta(
        self,
        group_id: str,
        name: str,
        scene: str,
        scene_desc: dict,
        user_details: dict,
        created_at: str,
        default_timezone: str = "Asia/Shanghai",
    ) -> dict:
        """Create or update conversation metadata."""
        payload = {
            "scene": scene,
            "scene_desc": scene_desc,
            "name": name,
            "group_id": group_id,
            "created_at": created_at,
            "default_timezone": default_timezone,
            "user_details": user_details,
            "tags": [],
        }
        resp = await self._client.post(
            f"{self.api_prefix}/conversation-meta",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()

    async def search_memory(
        self,
        query: str | None = None,
        user_id: str | None = None,
        group_id: str | None = None,
        retrieve_method: str = "keyword",
        memory_types: list[str] | None = None,
        top_k: int = 40,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> dict:
        """Search memories."""
        payload = {
            "retrieve_method": retrieve_method,
            "top_k": top_k,
            "memory_types": memory_types or ["episodic_memory"],
        }
        if query:
            payload["query"] = query
        if user_id:
            payload["user_id"] = user_id
        if group_id:
            payload["group_id"] = group_id
        if start_time:
            payload["start_time"] = start_time
        if end_time:
            payload["end_time"] = end_time

        resp = await self._client.request(
            "GET",
            f"{self.api_prefix}/search",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()

    async def get_memories(
        self,
        user_id: str | None = None,
        group_id: str | None = None,
        memory_type: str = "episodic_memory",
        limit: int = 40,
        offset: int = 0,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> dict:
        """Fetch memories by type."""
        params = {
            "memory_type": memory_type,
            "limit": limit,
            "offset": offset,
        }
        if user_id:
            params["user_id"] = user_id
        if group_id:
            params["group_id"] = group_id
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time

        resp = await self._client.get(self.api_prefix, params=params)
        resp.raise_for_status()
        return resp.json()

    async def get_conversation_meta(self, group_id: str | None = None) -> dict:
        """Get conversation metadata."""
        params = {}
        if group_id:
            params["group_id"] = group_id
        resp = await self._client.get(
            f"{self.api_prefix}/conversation-meta", params=params
        )
        resp.raise_for_status()
        return resp.json()

    async def delete_memories(
        self,
        event_id: str | None = None,
        user_id: str | None = None,
        group_id: str | None = None,
    ) -> dict:
        """Delete memories by filter (AND logic)."""
        payload = {}
        if event_id:
            payload["event_id"] = event_id
        if user_id:
            payload["user_id"] = user_id
        if group_id:
            payload["group_id"] = group_id

        resp = await self._client.request(
            "DELETE",
            self.api_prefix,
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()
