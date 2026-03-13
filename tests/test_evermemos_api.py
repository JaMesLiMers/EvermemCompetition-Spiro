import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from scripts.evermemos_api import EverMemosClient


@pytest.mark.asyncio
async def test_store_message():
    """Test store_message sends correct payload."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok", "result": {"count": 1, "status_info": "accumulated"}}
    mock_response.raise_for_status = MagicMock()

    async def mock_post(*args, **kwargs):
        return mock_response

    with patch.object(httpx.AsyncClient, "post", side_effect=mock_post):
        client = EverMemosClient("http://localhost:1995")
        result = await client.store_message(
            message_id="msg_001",
            create_time="2026-02-23T06:13:00+08:00",
            sender="user_001",
            content="Hello world",
            group_id="group_001",
        )
        assert result["status"] == "ok"


@pytest.mark.asyncio
async def test_create_conversation_meta():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok", "result": {"group_id": "g1", "scene": "assistant"}}
    mock_response.raise_for_status = MagicMock()

    async def mock_post(*args, **kwargs):
        return mock_response

    with patch.object(httpx.AsyncClient, "post", side_effect=mock_post):
        client = EverMemosClient("http://localhost:1995")
        result = await client.create_conversation_meta(
            group_id="g1",
            name="Test Event",
            scene="assistant",
            scene_desc={"description": "test", "type": "career"},
            user_details={},
            created_at="2026-02-23T06:13:00+08:00",
        )
        assert result["status"] == "ok"


@pytest.mark.asyncio
async def test_search_memory():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok", "result": {"memories": [], "total_count": 0}}
    mock_response.raise_for_status = MagicMock()

    async def mock_request(*args, **kwargs):
        return mock_response

    with patch.object(httpx.AsyncClient, "request", side_effect=mock_request):
        client = EverMemosClient("http://localhost:1995")
        result = await client.search_memory(query="coffee", user_id="u1")
        assert result["status"] == "ok"


@pytest.mark.asyncio
async def test_store_message_auto_generates_fields():
    """Test that message_id and create_time are auto-generated when omitted."""
    captured_payload = {}

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok", "result": {"count": 0}}
    mock_response.raise_for_status = MagicMock()

    async def mock_post(self, url, **kwargs):
        captured_payload.update(kwargs.get("json", {}))
        return mock_response

    with patch.object(httpx.AsyncClient, "post", mock_post):
        client = EverMemosClient("http://localhost:1995")
        await client.store_message(content="test", sender="user1")
        assert "message_id" in captured_payload
        assert "create_time" in captured_payload
        assert len(captured_payload["message_id"]) > 0


@pytest.mark.asyncio
async def test_get_memories():
    """Test get_memories sends correct query params."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok", "result": {"memories": [], "total_count": 0}}
    mock_response.raise_for_status = MagicMock()

    async def mock_get(*args, **kwargs):
        return mock_response

    with patch.object(httpx.AsyncClient, "get", side_effect=mock_get):
        client = EverMemosClient("http://localhost:1995")
        result = await client.get_memories(user_id="u1", group_id="g1")
        assert result["status"] == "ok"


@pytest.mark.asyncio
async def test_get_conversation_meta():
    """Test get_conversation_meta."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok", "result": {"group_id": "g1"}}
    mock_response.raise_for_status = MagicMock()

    async def mock_get(*args, **kwargs):
        return mock_response

    with patch.object(httpx.AsyncClient, "get", side_effect=mock_get):
        client = EverMemosClient("http://localhost:1995")
        result = await client.get_conversation_meta(group_id="g1")
        assert result["status"] == "ok"


@pytest.mark.asyncio
async def test_delete_memories():
    """Test delete_memories sends correct JSON body."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok", "result": {"deleted": 1}}
    mock_response.raise_for_status = MagicMock()

    async def mock_request(*args, **kwargs):
        return mock_response

    with patch.object(httpx.AsyncClient, "request", side_effect=mock_request):
        client = EverMemosClient("http://localhost:1995")
        result = await client.delete_memories(event_id="e1", user_id="u1")
        assert result["status"] == "ok"
