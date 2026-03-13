# EverMemOS Data Ingestion & MCP Server Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a data ingestion script to feed 832 events into EverMemOS, and an MCP server for Claude Code to interact with EverMemOS.

**Architecture:** Two independent components — (1) a Python ingestion script that parses transcript data and feeds it to EverMemOS REST API, (2) a Python MCP server using FastMCP that wraps EverMemOS REST API as tools. Each has its own HTTP client code (the MCP server uses simple inline helpers; the ingestion script uses a dedicated client class).

**Tech Stack:** Python 3.12, httpx (async HTTP), mcp SDK (FastMCP), pytest

**Spec:** `docs/superpowers/specs/2026-03-13-evermemos-ingestion-and-mcp-design.md`

---

## File Structure

```
scripts/
├── __init__.py                 # Make scripts a package (empty file)
├── ingest_data.py              # CLI entry point for data ingestion
├── transcript_parser.py        # Parse transcripts into speaker turns
└── evermemos_api.py            # Shared EverMemOS API client

mcp_server/
├── server.py                   # MCP Server entry point + tool definitions
└── requirements.txt            # mcp, httpx

tests/
├── test_transcript_parser.py   # Unit tests for transcript parsing
└── test_evermemos_api.py       # Unit tests for API client
```

**Dependencies:** `pip install httpx mcp pytest pytest-asyncio`

---

## Chunk 1: Transcript Parser

### Task 1: Transcript Parser — Core Parsing

**Files:**
- Create: `scripts/transcript_parser.py`
- Create: `tests/test_transcript_parser.py`

- [ ] **Step 1: Write failing test for speaker turn parsing**

```python
# tests/test_transcript_parser.py
from scripts.transcript_parser import parse_speaker_turns

def test_parse_single_turn():
    line = "[00:06][受访对象/产品测试用户]: [思考停顿] [认真语气] 如果说是落实到这个图标的话"
    turns = parse_speaker_turns([line], fragment_base_epoch=1771827235)
    assert len(turns) == 1
    assert turns[0]["speaker_label"] == "受访对象/产品测试用户"
    assert turns[0]["content"] == "如果说是落实到这个图标的话"
    assert turns[0]["offset_seconds"] == 6

def test_parse_strips_multiple_annotations():
    line = "[01:30][Speaker]: [音调平稳] [专业语气] [正常语速] 具体的设计比如说这种字体"
    turns = parse_speaker_turns([line], fragment_base_epoch=1000000)
    assert turns[0]["content"] == "具体的设计比如说这种字体"

def test_parse_skips_non_turn_lines():
    lines = [
        "[Fragment 1: 2026-02-23 06:13 - 2026-02-23 06:20]",
        "标题: APP设计方案",
        "类型: career",
        "",
        "[00:00][Speaker]: Hello"
    ]
    turns = parse_speaker_turns(lines, fragment_base_epoch=1000000)
    assert len(turns) == 1

def test_parse_calculates_absolute_timestamp():
    line = "[01:30][Speaker]: content"
    turns = parse_speaker_turns([line], fragment_base_epoch=1000000)
    assert turns[0]["absolute_epoch"] == 1000090  # 1000000 + 90 seconds
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/jameslimer/Spiro/evermemos_competition && python -m pytest tests/test_transcript_parser.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement parse_speaker_turns**

```python
# scripts/transcript_parser.py
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

TURN_PATTERN = re.compile(r"^\[(\d+):(\d+)\]\[([^\]]+)\]:\s*(.+)$")
ANNOTATION_PATTERN = re.compile(r"\[[^\[\]]{1,20}\]\s*")
FRAGMENT_PATTERN = re.compile(r"^\[Fragment \d+:\s*(.+?)\s*-\s*(.+?)\]$")

TIMEZONE = ZoneInfo("Asia/Shanghai")


def parse_speaker_turns(lines: list[str], fragment_base_epoch: int) -> list[dict]:
    """Parse transcript lines into speaker turns with absolute timestamps."""
    turns = []
    for line in lines:
        m = TURN_PATTERN.match(line.strip())
        if not m:
            continue
        minutes, seconds = int(m.group(1)), int(m.group(2))
        speaker_label = m.group(3)
        raw_content = m.group(4)

        # Strip annotations like [音调平稳] [思考停顿]
        content = ANNOTATION_PATTERN.sub("", raw_content).strip()
        if not content:
            continue

        offset_seconds = minutes * 60 + seconds
        absolute_epoch = fragment_base_epoch + offset_seconds

        turns.append({
            "speaker_label": speaker_label,
            "content": content,
            "offset_seconds": offset_seconds,
            "absolute_epoch": absolute_epoch,
        })
    return turns


def parse_fragment_time(time_str: str, event_start_epoch: int) -> int:
    """Parse a Fragment header time string to epoch seconds.

    Handles two formats:
    - Human-readable: '2026-02-23 06:13'
    - Epoch: '1766845585'
    """
    time_str = time_str.strip()
    if time_str.isdigit() or (len(time_str) > 5 and time_str.replace(".", "").isdigit()):
        return int(float(time_str))
    try:
        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        dt = dt.replace(tzinfo=TIMEZONE)
        return int(dt.timestamp())
    except ValueError:
        return event_start_epoch


def parse_transcript(transcript: str, event_start_epoch: int) -> list[dict]:
    """Parse a full transcript into speaker turns with absolute timestamps.

    Handles multiple Fragments, each with their own base time.
    """
    lines = transcript.split("\n")
    all_turns = []
    current_fragment_base = event_start_epoch

    for line in lines:
        # Check for Fragment header
        fm = FRAGMENT_PATTERN.match(line.strip())
        if fm:
            current_fragment_base = parse_fragment_time(fm.group(1), event_start_epoch)
            continue

        # Try to parse as speaker turn
        m = TURN_PATTERN.match(line.strip())
        if not m:
            continue

        minutes, seconds = int(m.group(1)), int(m.group(2))
        speaker_label = m.group(3)
        raw_content = m.group(4)

        content = ANNOTATION_PATTERN.sub("", raw_content).strip()
        if not content:
            continue

        offset_seconds = minutes * 60 + seconds
        absolute_epoch = current_fragment_base + offset_seconds

        all_turns.append({
            "speaker_label": speaker_label,
            "content": content,
            "offset_seconds": offset_seconds,
            "absolute_epoch": absolute_epoch,
        })

    return all_turns


def parse_speaker_analysis(speaker_analysis_json) -> list[dict]:
    """Parse the basic_speaker_analysis into a list of speaker info dicts.

    Handles both JSON string and pre-parsed list inputs.
    """
    import json
    if not speaker_analysis_json:
        return []
    if isinstance(speaker_analysis_json, list):
        return speaker_analysis_json
    try:
        return json.loads(speaker_analysis_json)
    except (json.JSONDecodeError, TypeError):
        return []


def match_speaker(speaker_label: str, speakers: list[dict]) -> dict | None:
    """Match a transcript speaker label to a speaker analysis entry.

    Uses substring matching: checks if the speaker's identity or relation_to_user
    appears in the transcript label, or vice versa.
    """
    for s in speakers:
        identity = s.get("identity", "")
        relation = s.get("relation_to_user", "")
        # Check if identity or relation is a substring of label (or vice versa)
        if identity and (identity in speaker_label or speaker_label in identity):
            return s
        if relation and (relation in speaker_label or speaker_label in relation):
            return s
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/jameslimer/Spiro/evermemos_competition && python -m pytest tests/test_transcript_parser.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Write tests for parse_transcript (multi-fragment) and speaker matching**

```python
# Append to tests/test_transcript_parser.py
from scripts.transcript_parser import parse_transcript, parse_speaker_analysis, match_speaker

def test_parse_transcript_multi_fragment():
    transcript = """[Fragment 1: 2026-02-23 06:13 - 2026-02-23 06:20]
标题: Test
类型: career

[00:00][Speaker A]: Hello
[00:10][Speaker B]: World

[Fragment 2: 1771828000 - 1771829000]

[00:00][Speaker A]: Second fragment
[00:05][Speaker B]: More content"""

    turns = parse_transcript(transcript, event_start_epoch=1771827235)
    assert len(turns) == 4
    # Fragment 1: 2026-02-23 06:13 in Asia/Shanghai
    assert turns[0]["speaker_label"] == "Speaker A"
    assert turns[1]["speaker_label"] == "Speaker B"
    # Fragment 2: base at 1771828000
    assert turns[2]["absolute_epoch"] == 1771828000
    assert turns[3]["absolute_epoch"] == 1771828005

def test_parse_speaker_analysis():
    json_str = '[{"unified_speaker_id": "unified_000", "is_user": true, "identity": "", "relation_to_user": "用户本人"}]'
    speakers = parse_speaker_analysis(json_str)
    assert len(speakers) == 1
    assert speakers[0]["is_user"] is True

def test_parse_speaker_analysis_empty():
    assert parse_speaker_analysis("") == []
    assert parse_speaker_analysis(None) == []

def test_match_speaker_by_relation():
    speakers = [
        {"unified_speaker_id": "u0", "identity": "", "relation_to_user": "用户本人"},
        {"unified_speaker_id": "u1", "identity": "用户研究员/产品经理", "relation_to_user": "访谈主持人"},
    ]
    result = match_speaker("访谈主持人/用户研究员/产品经理", speakers)
    assert result["unified_speaker_id"] == "u1"

def test_match_speaker_no_match():
    speakers = [{"unified_speaker_id": "u0", "identity": "Alice", "relation_to_user": "Friend"}]
    result = match_speaker("CompletelyDifferent", speakers)
    assert result is None
```

- [ ] **Step 6: Run all tests**

Run: `cd /home/jameslimer/Spiro/evermemos_competition && python -m pytest tests/test_transcript_parser.py -v`
Expected: All 9 tests PASS

- [ ] **Step 7: Commit**

```bash
git add scripts/transcript_parser.py tests/test_transcript_parser.py
git commit -m "feat: add transcript parser with speaker turn extraction and matching"
```

---

## Chunk 2: EverMemOS API Client

### Task 2: Shared API Client

**Files:**
- Create: `scripts/evermemos_api.py`
- Create: `tests/test_evermemos_api.py`

- [ ] **Step 1: Write failing test for API client**

```python
# tests/test_evermemos_api.py
import pytest
import json
from unittest.mock import AsyncMock, patch
from scripts.evermemos_api import EverMemosClient

@pytest.mark.asyncio
async def test_store_message():
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok", "result": {"count": 1, "status_info": "accumulated"}}

    with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
        client = EverMemosClient("http://localhost:1995")
        result = await client.store_message(
            message_id="msg_001",
            create_time="2026-02-23T06:13:00+08:00",
            sender="user_001",
            content="Hello world",
            group_id="group_001",
        )
        assert result["status"] == "ok"
        mock_post.assert_called_once()

@pytest.mark.asyncio
async def test_create_conversation_meta():
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok", "result": {"group_id": "g1", "scene": "assistant"}}

    with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
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
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok", "result": {"memories": [], "total_count": 0}}

    with patch("httpx.AsyncClient.request", return_value=mock_response) as mock_req:
        client = EverMemosClient("http://localhost:1995")
        result = await client.search_memory(query="coffee", user_id="u1")
        assert result["status"] == "ok"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/jameslimer/Spiro/evermemos_competition && python -m pytest tests/test_evermemos_api.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement EverMemosClient**

```python
# scripts/evermemos_api.py
import httpx
import uuid
from datetime import datetime, timezone


class EverMemosClient:
    """Async HTTP client for EverMemOS REST API."""

    def __init__(self, base_url: str = "http://localhost:1995"):
        self.base_url = base_url.rstrip("/")
        self.api_prefix = f"{self.base_url}/api/v1/memories"

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

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
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
        version: str = "1.0",
        default_timezone: str = "Asia/Shanghai",
    ) -> dict:
        """Create or update conversation metadata."""
        payload = {
            "version": version,
            "scene": scene,
            "scene_desc": scene_desc,
            "name": name,
            "group_id": group_id,
            "created_at": created_at,
            "default_timezone": default_timezone,
            "user_details": user_details,
            "tags": [],
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
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

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.request(
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

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(self.api_prefix, params=params)
            resp.raise_for_status()
            return resp.json()

    async def get_conversation_meta(self, group_id: str | None = None) -> dict:
        """Get conversation metadata."""
        params = {}
        if group_id:
            params["group_id"] = group_id
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{self.api_prefix}/conversation-meta", params=params)
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

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.request(
                "DELETE",
                self.api_prefix,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            return resp.json()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/jameslimer/Spiro/evermemos_competition && python -m pytest tests/test_evermemos_api.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/evermemos_api.py tests/test_evermemos_api.py
git commit -m "feat: add EverMemOS async API client with store, search, fetch, delete"
```

---

## Chunk 3: Data Ingestion Script

### Task 3: Ingestion CLI

**Files:**
- Create: `scripts/ingest_data.py`

- [ ] **Step 1: Implement ingest_data.py**

```python
# scripts/ingest_data.py
"""
Batch ingest Dataset events into EverMemOS.

Usage:
    python scripts/ingest_data.py --input Dataset/basic_events_79ef7f17.json
    python scripts/ingest_data.py --input Dataset/basic_events_79ef7f17.json --resume
    python scripts/ingest_data.py --input Dataset/basic_events_79ef7f17.json --limit 10
"""

import argparse
import asyncio
import json
import sys
import time
import httpx
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from scripts.transcript_parser import (
    parse_transcript,
    parse_speaker_analysis,
    match_speaker,
)
from scripts.evermemos_api import EverMemosClient

TIMEZONE = ZoneInfo("Asia/Shanghai")
PROGRESS_FILE = Path("scripts/ingestion_progress.json")


def epoch_to_iso(epoch: int) -> str:
    """Convert epoch seconds to ISO 8601 with Asia/Shanghai timezone."""
    return datetime.fromtimestamp(epoch, tz=TIMEZONE).isoformat()


def build_user_details(speakers: list[dict], transcript_labels: list[str]) -> dict:
    """Build user_details dict for conversation-meta from speaker analysis.

    Args:
        speakers: parsed speaker analysis list
        transcript_labels: unique speaker labels extracted from transcript turns
    """
    details = {}
    for s in speakers:
        sid = s.get("unified_speaker_id", "unknown")
        identity = s.get("identity", "")
        relation = s.get("relation_to_user", "")
        # Find the transcript label that matches this speaker
        label = None
        for tl in transcript_labels:
            if identity and (identity in tl or tl in identity):
                label = tl
                break
            if relation and (relation in tl or tl in relation):
                label = tl
                break
        name = label or identity or relation or sid
        details[sid] = {
            "full_name": name,
            "role": "user",  # all speakers are human
            "custom_role": identity,
            "extra": {
                "is_user": s.get("is_user", False),
                "gender": s.get("gender", "unknown"),
                "relation_to_user": relation,
            },
        }
    return details


def load_progress() -> dict:
    """Load ingestion progress from file."""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    return {"completed": [], "failed": {}}


def save_progress(progress: dict):
    """Save ingestion progress to file."""
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)


async def ingest_event(
    client: EverMemosClient, event: dict, progress: dict
) -> bool:
    """Ingest a single event into EverMemOS. Returns True on success."""
    meta = event["meta"]
    obj = event["object"]
    event_id = meta["basic_event_id"]

    # Skip empty transcripts
    transcript = obj.get("basic_transcript", "")
    if not transcript or not transcript.strip():
        print(f"  SKIP (empty transcript): {event_id}")
        return True

    # Parse speakers
    speakers = parse_speaker_analysis(obj.get("basic_speaker_analysis", ""))

    # Parse transcript into turns
    turns = parse_transcript(transcript, meta["basic_start_time"])
    if not turns:
        print(f"  SKIP (no valid turns): {event_id}")
        return True

    # Step 1: Create conversation-meta
    basic_types = obj.get("basic_type", [])
    scene_desc = {
        "description": obj.get("basic_scene", ""),
        "type": basic_types[0] if basic_types else "unknown",
    }

    user_details = build_user_details(speakers, list({t["speaker_label"] for t in turns}))

    try:
        await client.create_conversation_meta(
            group_id=event_id,
            name=obj.get("basic_title", "Untitled"),
            scene="assistant",
            scene_desc=scene_desc,
            user_details=user_details,
            created_at=epoch_to_iso(meta["basic_start_time"]),
        )
    except Exception as e:
        print(f"  ERROR (conversation-meta): {e}")
        return False

    # Step 2: Send each turn as a message
    failed_turns = []
    for idx, turn in enumerate(turns):
        speaker_info = match_speaker(turn["speaker_label"], speakers)
        sender = speaker_info["unified_speaker_id"] if speaker_info else turn["speaker_label"]
        sender_name = turn["speaker_label"]

        try:
            await client.store_message(
                message_id=f"{event_id}_{idx}",
                create_time=epoch_to_iso(turn["absolute_epoch"]),
                sender=sender,
                sender_name=sender_name,
                content=turn["content"],
                group_id=event_id,
                group_name=obj.get("basic_title", "Untitled"),
                role="user",
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code >= 500:
                # 5xx: retry up to 3 times with exponential backoff
                success = False
                for attempt, delay in enumerate([1, 2, 4]):
                    await asyncio.sleep(delay)
                    try:
                        await client.store_message(
                            message_id=f"{event_id}_{idx}",
                            create_time=epoch_to_iso(turn["absolute_epoch"]),
                            sender=sender, sender_name=sender_name,
                            content=turn["content"], group_id=event_id,
                            group_name=obj.get("basic_title", "Untitled"), role="user",
                        )
                        success = True
                        break
                    except Exception:
                        continue
                if not success:
                    print(f"  ERROR (turn {idx}, 5xx after 3 retries): {e}")
                    failed_turns.append(idx)
            else:
                # 4xx: log and skip
                print(f"  ERROR (turn {idx}, {e.response.status_code}): {e}")
                failed_turns.append(idx)
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            # Network error: retry once
            await asyncio.sleep(1)
            try:
                await client.store_message(
                    message_id=f"{event_id}_{idx}",
                    create_time=epoch_to_iso(turn["absolute_epoch"]),
                    sender=sender, sender_name=sender_name,
                    content=turn["content"], group_id=event_id,
                    group_name=obj.get("basic_title", "Untitled"), role="user",
                )
            except Exception:
                print(f"  ERROR (turn {idx}, network): {e}")
                failed_turns.append(idx)
        except Exception as e:
            print(f"  ERROR (turn {idx}): {e}")
            failed_turns.append(idx)

        await asyncio.sleep(0.1)  # Rate limiting

    if failed_turns:
        progress["failed"][event_id] = failed_turns
        return False

    return True


async def main():
    parser = argparse.ArgumentParser(description="Ingest dataset into EverMemOS")
    parser.add_argument("--input", required=True, help="Path to dataset JSON file")
    parser.add_argument("--api-url", default="http://localhost:1995", help="EverMemOS base URL")
    parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint")
    parser.add_argument("--limit", type=int, default=0, help="Process only N events (0 = all)")
    args = parser.parse_args()

    # Load data
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        events = json.load(f)

    print(f"Loaded {len(events)} events from {input_path}")

    # Load progress
    progress = load_progress() if args.resume else {"completed": [], "failed": {}}
    completed_set = set(progress["completed"])

    client = EverMemosClient(args.api_url)

    # Process events
    total = len(events)
    if args.limit > 0:
        events = events[:args.limit]
        total = len(events)

    success_count = 0
    skip_count = 0
    fail_count = 0

    for i, event in enumerate(events):
        event_id = event["meta"]["basic_event_id"]

        if event_id in completed_set:
            skip_count += 1
            continue

        title = event["object"].get("basic_title", "Untitled")
        print(f"[{i+1}/{total}] {title[:50]}...")

        ok = await ingest_event(client, event, progress)
        if ok:
            success_count += 1
            progress["completed"].append(event_id)
        else:
            fail_count += 1

        # Save progress every 10 events
        if (i + 1) % 10 == 0:
            save_progress(progress)

    # Final save
    save_progress(progress)

    print(f"\nDone: {success_count} succeeded, {fail_count} failed, {skip_count} skipped (already done)")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Test with a small batch against live EverMemOS**

Run: `cd /home/jameslimer/Spiro/evermemos_competition && python scripts/ingest_data.py --input Dataset/basic_events_79ef7f17.json --limit 3`
Expected: 3 events processed, conversation-meta created, messages sent. Check output for errors.

- [ ] **Step 3: Verify data landed in EverMemOS**

Run: `curl -s "http://localhost:1995/api/v1/memories?user_id=79ef7f17-9d24-4a85-a6fe-de7d060bc090&memory_type=episodic_memory&limit=5" | python -m json.tool | head -30`
Expected: Some memories returned (may need to wait a few seconds for EverMemOS background processing)

- [ ] **Step 4: Commit**

```bash
git add scripts/ingest_data.py
git commit -m "feat: add data ingestion script with resume support and rate limiting"
```

---

## Chunk 4: MCP Server

### Task 4: MCP Server Implementation

**Files:**
- Create: `mcp_server/server.py`
- Create: `mcp_server/requirements.txt`

- [ ] **Step 1: Create requirements.txt**

```
# mcp_server/requirements.txt
mcp>=1.0
httpx>=0.27
```

- [ ] **Step 2: Install dependencies**

Run: `pip install mcp httpx`

- [ ] **Step 3: Implement MCP Server**

```python
# mcp_server/server.py
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
```

- [ ] **Step 4: Test MCP server starts without errors**

Run: `cd /home/jameslimer/Spiro/evermemos_competition && timeout 3 python mcp_server/server.py 2>&1 || true`
Expected: Server starts (may block on stdin for MCP transport). No import errors.

- [ ] **Step 5: Commit**

```bash
git add mcp_server/server.py mcp_server/requirements.txt
git commit -m "feat: add MCP server wrapping EverMemOS API with 5 tools"
```

---

## Chunk 5: Claude Code Integration

### Task 5: Register MCP Server in Claude Code

**Files:**
- Create or modify: `.claude/settings.json`

- [ ] **Step 1: Create Claude Code settings with MCP server config**

Create `.claude/settings.json` (or merge into existing):

```json
{
  "mcpServers": {
    "evermemos": {
      "command": "python",
      "args": ["mcp_server/server.py"],
      "env": {
        "EVERMEMOS_BASE_URL": "http://localhost:1995"
      }
    }
  }
}
```

- [ ] **Step 2: Restart Claude Code to pick up MCP server**

The user needs to restart Claude Code (or run `/mcp` to check) so it connects to the new MCP server.

- [ ] **Step 3: Verify MCP tools are available**

In Claude Code, ask: "Use the search_memory tool to search for any memories with user_id 79ef7f17-9d24-4a85-a6fe-de7d060bc090"

Expected: The tool should be available and return results (or empty results if data hasn't been ingested yet).

- [ ] **Step 4: Commit**

```bash
git add .claude/settings.json
git commit -m "feat: register EverMemOS MCP server in Claude Code settings"
```

---

## Chunk 6: Full Data Ingestion Run

### Task 6: Ingest All 832 Events

This is an operational task, not a coding task.

- [ ] **Step 1: Run full ingestion**

Run: `cd /home/jameslimer/Spiro/evermemos_competition && python scripts/ingest_data.py --input Dataset/basic_events_79ef7f17.json`

Expected: All 832 events processed. This will take a while due to rate limiting and EverMemOS processing.

- [ ] **Step 2: Verify ingestion results**

Run: `curl -s "http://localhost:1995/api/v1/memories?user_id=79ef7f17-9d24-4a85-a6fe-de7d060bc090&memory_type=episodic_memory&limit=5" | python -m json.tool | head -50`

- [ ] **Step 3: Test end-to-end with Claude Code MCP**

In Claude Code, use the search_memory tool to verify the ingested data is searchable.

---

## Execution Order

Tasks 1-2 are independent and can be parallelized.
Task 3 depends on Tasks 1 and 2.
Task 4 depends on Task 2 (shares the API client pattern).
Task 5 depends on Task 4.
Task 6 depends on Tasks 3 and 5.
