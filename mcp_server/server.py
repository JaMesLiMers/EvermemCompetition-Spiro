"""EverMemOS MCP Server — wraps EverMemOS REST API as MCP tools for Claude Code."""

import os
import json
import uuid
import httpx
from datetime import datetime, timezone
from mcp.server.fastmcp import FastMCP

BASE_URL = os.environ.get("EVERMEMOS_BASE_URL", "http://localhost:1995")
API_PREFIX = f"{BASE_URL}/api/v1/memories"

mcp = FastMCP("evermemos")


async def _post(url: str, payload: dict, timeout: float = 30.0) -> dict:
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=payload, headers={"Content-Type": "application/json"})
        resp.raise_for_status()
        return resp.json()


async def _get(url: str, params: dict | None = None, timeout: float = 30.0) -> dict:
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()


async def _get_with_body(url: str, payload: dict, timeout: float = 60.0) -> dict:
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.request("GET", url, json=payload, headers={"Content-Type": "application/json"})
        resp.raise_for_status()
        return resp.json()


async def _delete(url: str, payload: dict, timeout: float = 30.0) -> dict:
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.request("DELETE", url, json=payload, headers={"Content-Type": "application/json"})
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
async def search_memory(
    query: str | None = None,
    user_id: str | None = None,
    group_id: str | None = None,
    retrieve_method: str = "keyword",
    memory_types: list[str] | None = None,
    top_k: int = 40,
    start_time: str | None = None,
    end_time: str | None = None,
) -> str:
    """Search EverMemOS memories using keyword, vector, hybrid, rrf, or agentic retrieval.

    At least one of user_id or group_id must be provided.
    memory_types can include: episodic_memory, foresight, event_log.
    """
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

    result = await _get_with_body(f"{API_PREFIX}/search", payload)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def get_memories(
    user_id: str | None = None,
    group_id: str | None = None,
    memory_type: str = "episodic_memory",
    limit: int = 40,
    offset: int = 0,
    start_time: str | None = None,
    end_time: str | None = None,
) -> str:
    """Fetch EverMemOS memories by type (profile, episodic_memory, foresight, event_log).

    At least one of user_id or group_id must be provided.
    """
    params = {"memory_type": memory_type, "limit": limit, "offset": offset}
    if user_id:
        params["user_id"] = user_id
    if group_id:
        params["group_id"] = group_id
    if start_time:
        params["start_time"] = start_time
    if end_time:
        params["end_time"] = end_time

    result = await _get(API_PREFIX, params)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def store_message(
    content: str,
    sender: str,
    message_id: str | None = None,
    create_time: str | None = None,
    sender_name: str | None = None,
    group_id: str | None = None,
    group_name: str | None = None,
    role: str = "user",
) -> str:
    """Store a message into EverMemOS memory.

    message_id and create_time are auto-generated if omitted.
    """
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

    result = await _post(API_PREFIX, payload)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def get_conversation_meta(group_id: str | None = None) -> str:
    """Get conversation metadata from EverMemOS."""
    params = {}
    if group_id:
        params["group_id"] = group_id
    result = await _get(f"{API_PREFIX}/conversation-meta", params)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def delete_memories(
    event_id: str | None = None,
    user_id: str | None = None,
    group_id: str | None = None,
) -> str:
    """Delete EverMemOS memories by filter criteria (AND logic).

    At least one filter must be provided.
    """
    payload = {}
    if event_id:
        payload["event_id"] = event_id
    if user_id:
        payload["user_id"] = user_id
    if group_id:
        payload["group_id"] = group_id

    result = await _delete(API_PREFIX, payload)
    return json.dumps(result, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run()
