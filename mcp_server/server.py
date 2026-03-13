"""EverMemOS MCP Server — wraps EverMemOS REST API as MCP tools for Claude Code."""

import os
import json
from mcp.server.fastmcp import FastMCP

from shared.evermemos_api import EverMemosClient

BASE_URL = os.environ.get("EVERMEMOS_BASE_URL", "http://localhost:1995")

mcp = FastMCP("evermemos")
_client = EverMemosClient(BASE_URL)


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
    result = await _client.search_memory(
        query=query,
        user_id=user_id,
        group_id=group_id,
        retrieve_method=retrieve_method,
        memory_types=memory_types,
        top_k=top_k,
        start_time=start_time,
        end_time=end_time,
    )
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
    result = await _client.get_memories(
        user_id=user_id,
        group_id=group_id,
        memory_type=memory_type,
        limit=limit,
        offset=offset,
        start_time=start_time,
        end_time=end_time,
    )
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
    result = await _client.store_message(
        content=content,
        sender=sender,
        message_id=message_id,
        create_time=create_time,
        sender_name=sender_name,
        group_id=group_id,
        group_name=group_name,
        role=role,
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def get_conversation_meta(group_id: str | None = None) -> str:
    """Get conversation metadata from EverMemOS."""
    result = await _client.get_conversation_meta(group_id=group_id)
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
    result = await _client.delete_memories(
        event_id=event_id,
        user_id=user_id,
        group_id=group_id,
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run()
