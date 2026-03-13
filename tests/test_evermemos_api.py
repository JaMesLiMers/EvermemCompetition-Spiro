from unittest.mock import MagicMock, patch

import pytest

from shared.evermemos_api import EverMemosClient


@pytest.fixture
def mock_response():
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    return resp


@pytest.mark.asyncio
async def test_store_message(mock_response):
    """Test store_message sends correct payload."""
    mock_response.json.return_value = {"status": "ok", "result": {"count": 1, "status_info": "accumulated"}}

    async def mock_post(*args, **kwargs):
        return mock_response

    client = EverMemosClient("http://localhost:1995")
    with patch.object(client._client, "post", side_effect=mock_post):
        result = await client.store_message(
            message_id="msg_001",
            create_time="2026-02-23T06:13:00+08:00",
            sender="user_001",
            content="Hello world",
            group_id="group_001",
        )
        assert result["status"] == "ok"
    await client.close()


@pytest.mark.asyncio
async def test_create_conversation_meta(mock_response):
    mock_response.json.return_value = {"status": "ok", "result": {"group_id": "g1", "scene": "group_chat"}}

    async def mock_post(*args, **kwargs):
        return mock_response

    client = EverMemosClient("http://localhost:1995")
    with patch.object(client._client, "post", side_effect=mock_post):
        result = await client.create_conversation_meta(
            group_id="g1",
            name="Test Event",
            scene="group_chat",
            scene_desc={"description": "test", "type": "career"},
            user_details={},
            created_at="2026-02-23T06:13:00+08:00",
        )
        assert result["status"] == "ok"
    await client.close()


@pytest.mark.asyncio
async def test_create_conversation_meta_no_version(mock_response):
    """Verify version field is not sent in payload."""
    captured_payload = {}
    mock_response.json.return_value = {"status": "ok", "result": {}}

    async def mock_post(url, **kwargs):
        captured_payload.update(kwargs.get("json", {}))
        return mock_response

    client = EverMemosClient("http://localhost:1995")
    with patch.object(client._client, "post", side_effect=mock_post):
        await client.create_conversation_meta(
            group_id="g1",
            name="Test",
            scene="group_chat",
            scene_desc={},
            user_details={},
            created_at="2026-01-01T00:00:00+08:00",
        )
        assert "version" not in captured_payload
    await client.close()


@pytest.mark.asyncio
async def test_search_memory(mock_response):
    mock_response.json.return_value = {"status": "ok", "result": {"memories": [], "total_count": 0}}

    async def mock_request(*args, **kwargs):
        return mock_response

    client = EverMemosClient("http://localhost:1995")
    with patch.object(client._client, "request", side_effect=mock_request):
        result = await client.search_memory(query="coffee", user_id="u1")
        assert result["status"] == "ok"
    await client.close()


@pytest.mark.asyncio
async def test_store_message_auto_generates_fields(mock_response):
    """Test that message_id and create_time are auto-generated when omitted."""
    captured_payload = {}
    mock_response.json.return_value = {"status": "ok", "result": {"count": 0}}

    async def mock_post(url, **kwargs):
        captured_payload.update(kwargs.get("json", {}))
        return mock_response

    client = EverMemosClient("http://localhost:1995")
    with patch.object(client._client, "post", side_effect=mock_post):
        await client.store_message(content="test", sender="user1")
        assert "message_id" in captured_payload
        assert "create_time" in captured_payload
        assert len(captured_payload["message_id"]) > 0
    await client.close()


@pytest.mark.asyncio
async def test_get_memories(mock_response):
    """Test get_memories sends correct query params."""
    mock_response.json.return_value = {"status": "ok", "result": {"memories": [], "total_count": 0}}

    async def mock_get(*args, **kwargs):
        return mock_response

    client = EverMemosClient("http://localhost:1995")
    with patch.object(client._client, "get", side_effect=mock_get):
        result = await client.get_memories(user_id="u1", group_id="g1")
        assert result["status"] == "ok"
    await client.close()


@pytest.mark.asyncio
async def test_get_conversation_meta(mock_response):
    """Test get_conversation_meta."""
    mock_response.json.return_value = {"status": "ok", "result": {"group_id": "g1"}}

    async def mock_get(*args, **kwargs):
        return mock_response

    client = EverMemosClient("http://localhost:1995")
    with patch.object(client._client, "get", side_effect=mock_get):
        result = await client.get_conversation_meta(group_id="g1")
        assert result["status"] == "ok"
    await client.close()


@pytest.mark.asyncio
async def test_delete_memories(mock_response):
    """Test delete_memories sends correct JSON body."""
    mock_response.json.return_value = {"status": "ok", "result": {"deleted": 1}}

    async def mock_request(*args, **kwargs):
        return mock_response

    client = EverMemosClient("http://localhost:1995")
    with patch.object(client._client, "request", side_effect=mock_request):
        result = await client.delete_memories(event_id="e1", user_id="u1")
        assert result["status"] == "ok"
    await client.close()


@pytest.mark.asyncio
async def test_client_context_manager(mock_response):
    """Test async context manager properly creates and closes client."""
    mock_response.json.return_value = {"status": "ok", "result": {}}

    async def mock_get(*args, **kwargs):
        return mock_response

    async with EverMemosClient("http://localhost:1995") as client:
        with patch.object(client._client, "get", side_effect=mock_get):
            result = await client.get_conversation_meta()
            assert result["status"] == "ok"
