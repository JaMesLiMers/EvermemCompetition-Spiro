# GCF Conversion Pipeline Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert competition dataset events into EverMemOS GroupChatFormat JSON files with speaker normalization, smart splitting, and metadata extraction, then ingest via the official `run_memorize.py`.

**Architecture:** A new `scripts/convert_to_gcf.py` script parses transcripts into per-fragment data structures, normalizes speakers, applies splitting rules, and outputs one GCF JSON file per group. Makefile targets wrap conversion and ingestion. Existing `transcript_parser.py` is reused for turn-level parsing; fragment-level iteration is new.

**Tech Stack:** Python 3.10+, existing `transcript_parser.py` (regex-based parsing), EverMemOS `run_memorize.py` (official ingestion tool), JSON, Makefile.

**Spec:** `docs/superpowers/specs/2026-03-14-gcf-conversion-pipeline-design.md`

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `scripts/convert_to_gcf.py` | Main conversion script: parse fragments, normalize speakers, split, output GCF JSON |
| Create | `tests/test_convert_to_gcf.py` | Tests for conversion logic |
| Modify | `Makefile` | Add `convert-gcf` and `ingest-gcf` targets |

---

## Chunk 1: Fragment-Level Parser and Speaker Normalization

### Task 1: Fragment-level parser — tests

**Files:**
- Create: `tests/test_convert_to_gcf.py`

- [ ] **Step 1: Write tests for `parse_fragments()` function**

This function splits a transcript into individual fragment dicts, each with its own title, types, time range, and raw lines. It reuses `parse_speaker_turns()` from `transcript_parser.py` internally but iterates at the fragment level.

```python
# tests/test_convert_to_gcf.py
from scripts.convert_to_gcf import parse_fragments, normalize_speaker, should_skip_speaker

# --- parse_fragments tests ---

def test_parse_fragments_single_fragment():
    transcript = """[Fragment 1: 2026-02-23 06:13 - 2026-02-23 06:20]
标题: 用户反馈讨论
类型: career, self_awareness

[00:00][Speaker A]: Hello
[00:10][Speaker B]: World"""
    frags = parse_fragments(transcript, event_start_epoch=1771827235)
    assert len(frags) == 1
    assert frags[0]["title"] == "用户反馈讨论"
    assert frags[0]["types"] == ["career", "self_awareness"]
    assert len(frags[0]["turns"]) == 2
    assert frags[0]["turns"][0]["speaker_label"] == "Speaker A"
    assert frags[0]["base_epoch"] > 0
    assert frags[0]["end_epoch"] > frags[0]["base_epoch"]


def test_parse_fragments_multi_fragment():
    transcript = """[Fragment 1: 1000000 - 1000300]
标题: First Topic
类型: career

[00:00][A]: First

[Fragment 2: 1000300 - 1000600]
标题: Second Topic
类型: social

[00:00][B]: Second"""
    frags = parse_fragments(transcript, event_start_epoch=1000000)
    assert len(frags) == 2
    assert frags[0]["title"] == "First Topic"
    assert frags[0]["types"] == ["career"]
    assert frags[1]["title"] == "Second Topic"
    assert frags[1]["types"] == ["social"]


def test_parse_fragments_no_fragment_headers():
    """Events with no Fragment headers treat entire transcript as one implicit fragment."""
    transcript = """[用户]: 你好
[朋友]: 嗨"""
    frags = parse_fragments(transcript, event_start_epoch=1000000)
    assert len(frags) == 1
    assert frags[0]["title"] is None
    assert len(frags[0]["turns"]) == 2


def test_parse_fragments_skips_passive_media():
    transcript = """[Fragment 1: 1000000 - 1000300]
标题: 收听播客
类型: interest

(被动媒体，转录内容已略过)

------------------------------------------

[Fragment 2: 1000300 - 1000600]
标题: 聊天
类型: social

[00:00][A]: Active content"""
    frags = parse_fragments(transcript, event_start_epoch=1000000)
    assert len(frags) == 1
    assert frags[0]["title"] == "聊天"


def test_parse_fragments_per_fragment_title_types():
    """Each fragment can have its own title and types."""
    transcript = """[Fragment 1: 1000000 - 1000300]
标题: Topic A
类型: career

[00:00][X]: content1

[Fragment 2: 1000300 - 1000600]
标题: Topic B
类型: social, home

[00:00][Y]: content2"""
    frags = parse_fragments(transcript, event_start_epoch=1000000)
    assert frags[0]["title"] == "Topic A"
    assert frags[0]["types"] == ["career"]
    assert frags[1]["title"] == "Topic B"
    assert frags[1]["types"] == ["social", "home"]
```

- [ ] **Step 2: Write tests for `normalize_speaker()` and `should_skip_speaker()`**

```python
# Append to tests/test_convert_to_gcf.py

# --- Speaker normalization tests ---

def test_normalize_speaker_main_user():
    assert normalize_speaker("user") == "user_main"
    assert normalize_speaker("用户") == "user_main"
    assert normalize_speaker("User") == "user_main"


def test_normalize_speaker_preserves_others():
    assert normalize_speaker("unified_001") == "unified_001"
    assert normalize_speaker("SPEAKER_01") == "SPEAKER_01"
    assert normalize_speaker("访谈主持人/用户研究员/产品经理") == "访谈主持人/用户研究员/产品经理"


def test_should_skip_speaker_background():
    assert should_skip_speaker("背景音") is True
    assert should_skip_speaker("背景声") is True
    assert should_skip_speaker("背景噪音") is True
    assert should_skip_speaker("背景音: 电子提示音") is True
    assert should_skip_speaker("视频背景音") is True


def test_should_skip_speaker_environment():
    assert should_skip_speaker("环境音") is True
    assert should_skip_speaker("路人/环境背景音/背景人声/表演者") is True


def test_should_skip_speaker_passerby():
    assert should_skip_speaker("路人/背景人声") is True
    assert should_skip_speaker("陌生人/路人/背景人声") is True


def test_should_skip_speaker_irrelevant():
    assert should_skip_speaker("无关人员/环境音来源/未知人员") is True


def test_should_skip_speaker_normal():
    assert should_skip_speaker("unified_001") is False
    assert should_skip_speaker("user_main") is False
    assert should_skip_speaker("Speaker A") is False
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd /home/jameslimer/Spiro/evermemos_competition && python -m pytest tests/test_convert_to_gcf.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.convert_to_gcf'`

---

### Task 2: Fragment-level parser and speaker normalization — implementation

**Files:**
- Create: `scripts/convert_to_gcf.py` (initial: just `parse_fragments`, `normalize_speaker`, `should_skip_speaker`)

- [ ] **Step 1: Implement `parse_fragments()`, `normalize_speaker()`, `should_skip_speaker()`**

```python
"""Convert competition dataset events to EverMemOS GroupChatFormat JSON files.

Usage:
    python scripts/convert_to_gcf.py --input Dataset/basic_events_79ef7f17.json --output data/gcf/
"""

import re
from scripts.transcript_parser import (
    FRAGMENT_PATTERN,
    TITLE_PATTERN,
    TYPE_PATTERN,
    parse_fragment_time,
    parse_speaker_turns,
)

# Speakers that match any of these substrings are skipped
_SKIP_SPEAKER_KEYWORDS = ("背景", "环境", "路人", "无关人员", "Media_Guest")

# Main user aliases → normalized ID
_MAIN_USER_ALIASES = {"user", "用户", "User"}

PASSIVE_MEDIA_MARKER = "被动媒体，转录内容已略过"


def normalize_speaker(speaker: str) -> str:
    """Normalize main-user aliases to 'user_main'. Others unchanged."""
    return "user_main" if speaker in _MAIN_USER_ALIASES else speaker


def should_skip_speaker(speaker: str) -> bool:
    """Return True if this speaker label should be filtered out."""
    return any(kw in speaker for kw in _SKIP_SPEAKER_KEYWORDS)


def parse_fragments(transcript: str, event_start_epoch: int) -> list[dict]:
    """Parse transcript into per-fragment dicts.

    Each dict has:
      - title: str | None
      - types: list[str]
      - base_epoch: int
      - end_epoch: int
      - turns: list[dict]  (from parse_speaker_turns)
    """
    lines = transcript.split("\n")

    # Collect raw fragment boundaries and their lines
    fragments_raw: list[dict] = []
    current: dict | None = None

    for line in lines:
        stripped = line.strip()
        fm = FRAGMENT_PATTERN.match(stripped)
        if fm:
            if current is not None:
                fragments_raw.append(current)
            base = parse_fragment_time(fm.group(1), event_start_epoch)
            end = parse_fragment_time(fm.group(2), base)
            current = {
                "base_epoch": base,
                "end_epoch": end,
                "title": None,
                "types": [],
                "lines": [],
                "is_passive": False,
            }
            continue

        if current is None:
            # No Fragment header seen yet — start implicit fragment
            current = {
                "base_epoch": event_start_epoch,
                "end_epoch": event_start_epoch,
                "title": None,
                "types": [],
                "lines": [],
                "is_passive": False,
            }

        # Check for passive media
        if PASSIVE_MEDIA_MARKER in stripped:
            current["is_passive"] = True
            continue

        # Extract per-fragment title
        if current["title"] is None:
            tm = TITLE_PATTERN.match(stripped)
            if tm:
                current["title"] = tm.group(1).strip()
                continue

        # Extract per-fragment types
        if not current["types"]:
            tp = TYPE_PATTERN.match(stripped)
            if tp:
                current["types"] = [t.strip() for t in tp.group(1).split(",")]
                continue

        current["lines"].append(line)

    if current is not None:
        fragments_raw.append(current)

    # Parse turns and filter passive fragments
    result = []
    for frag in fragments_raw:
        if frag["is_passive"]:
            continue
        duration = max(0, frag["end_epoch"] - frag["base_epoch"])
        turns = parse_speaker_turns(frag["lines"], frag["base_epoch"], duration)
        if not turns:
            continue
        result.append({
            "title": frag["title"],
            "types": frag["types"],
            "base_epoch": frag["base_epoch"],
            "end_epoch": frag["end_epoch"],
            "turns": turns,
        })

    return result
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `cd /home/jameslimer/Spiro/evermemos_competition && python -m pytest tests/test_convert_to_gcf.py -v`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add scripts/convert_to_gcf.py tests/test_convert_to_gcf.py
git commit -m "feat: add fragment parser and speaker normalization for GCF conversion"
```

---

## Chunk 2: GCF Builder and Smart Splitting

### Task 3: GCF builder and splitter — tests

**Files:**
- Modify: `tests/test_convert_to_gcf.py`

- [ ] **Step 1: Write tests for `build_gcf_groups()` function**

This function takes an event dict (meta + fragments) and returns a list of GCF group dicts ready to write as JSON.

```python
# Append to tests/test_convert_to_gcf.py
from scripts.convert_to_gcf import build_gcf_groups

def _make_turns(n, speaker="A", base_epoch=1000000):
    """Helper: generate n dummy turns."""
    return [
        {"speaker_label": speaker, "content": f"msg {i}", "offset_seconds": i, "absolute_epoch": base_epoch + i}
        for i in range(n)
    ]


def test_build_gcf_single_group_no_split():
    """Event with few fragments → single GCF group."""
    fragments = [
        {"title": "Topic", "types": ["career"], "base_epoch": 1000000, "end_epoch": 1000300, "turns": _make_turns(5)},
    ]
    groups = build_gcf_groups(
        event_id="evt-001",
        event_start_epoch=1000000,
        fragments=fragments,
        split_frag_threshold=8,
        split_turn_threshold=100,
    )
    assert len(groups) == 1
    gcf = groups[0]
    assert gcf["version"] == "1.0.0"
    assert gcf["conversation_meta"]["group_id"] == "evt-001"
    assert gcf["conversation_meta"]["name"] == "Topic"
    assert gcf["conversation_meta"]["tags"] == ["career"]
    assert gcf["conversation_meta"]["scene"] == "group_chat"
    assert len(gcf["conversation_list"]) == 5
    # Check message format
    msg = gcf["conversation_list"][0]
    assert "message_id" in msg
    assert msg["type"] == "text"
    assert msg["role"] == "user"
    assert "refer_list" in msg


def test_build_gcf_splits_many_fragments():
    """Event with >threshold fragments → split by fragment."""
    fragments = [
        {"title": f"Topic {i}", "types": ["social"], "base_epoch": 1000000 + i * 300, "end_epoch": 1000000 + (i+1) * 300, "turns": _make_turns(3, base_epoch=1000000 + i * 300)}
        for i in range(10)
    ]
    groups = build_gcf_groups(
        event_id="evt-002",
        event_start_epoch=1000000,
        fragments=fragments,
        split_frag_threshold=8,
        split_turn_threshold=100,
    )
    assert len(groups) == 10
    assert groups[0]["conversation_meta"]["group_id"] == "evt-002_part0"
    assert groups[9]["conversation_meta"]["group_id"] == "evt-002_part9"
    assert groups[0]["conversation_meta"]["name"] == "Topic 0"
    assert groups[5]["conversation_meta"]["name"] == "Topic 5"


def test_build_gcf_splits_many_turns():
    """Event with >threshold total turns → split by fragment."""
    fragments = [
        {"title": "Big1", "types": ["career"], "base_epoch": 1000000, "end_epoch": 1000300, "turns": _make_turns(60)},
        {"title": "Big2", "types": ["career"], "base_epoch": 1000300, "end_epoch": 1000600, "turns": _make_turns(60, base_epoch=1000300)},
    ]
    groups = build_gcf_groups(
        event_id="evt-003",
        event_start_epoch=1000000,
        fragments=fragments,
        split_frag_threshold=8,
        split_turn_threshold=100,
    )
    assert len(groups) == 2  # 120 turns > 100 threshold → split


def test_build_gcf_single_fragment_large_turns_windowed():
    """Single fragment with >200 turns → split by 100-turn windows."""
    fragments = [
        {"title": "Long Chat", "types": ["social"], "base_epoch": 1000000, "end_epoch": 1000600, "turns": _make_turns(250)},
    ]
    groups = build_gcf_groups(
        event_id="evt-004",
        event_start_epoch=1000000,
        fragments=fragments,
        split_frag_threshold=8,
        split_turn_threshold=100,
    )
    assert len(groups) == 3  # 250 turns → windows of 100, 100, 50
    assert groups[0]["conversation_meta"]["group_id"] == "evt-004_part0"
    assert len(groups[0]["conversation_list"]) == 100
    assert len(groups[2]["conversation_list"]) == 50


def test_build_gcf_speaker_normalization():
    """user/用户/User speakers are normalized to user_main in output."""
    turns = [
        {"speaker_label": "user", "content": "hi", "offset_seconds": 0, "absolute_epoch": 1000000},
        {"speaker_label": "用户", "content": "hello", "offset_seconds": 1, "absolute_epoch": 1000001},
    ]
    fragments = [{"title": "Test", "types": [], "base_epoch": 1000000, "end_epoch": 1000300, "turns": turns}]
    groups = build_gcf_groups("evt-005", 1000000, fragments, 8, 100)
    msgs = groups[0]["conversation_list"]
    assert msgs[0]["sender"] == "user_main"
    assert msgs[0]["sender_name"] == "user"
    assert msgs[1]["sender"] == "user_main"
    assert msgs[1]["sender_name"] == "用户"


def test_build_gcf_filters_background_speakers():
    """Turns from background/environment speakers are excluded."""
    turns = [
        {"speaker_label": "unified_001", "content": "real", "offset_seconds": 0, "absolute_epoch": 1000000},
        {"speaker_label": "背景音", "content": "noise", "offset_seconds": 1, "absolute_epoch": 1000001},
        {"speaker_label": "环境音", "content": "ambient", "offset_seconds": 2, "absolute_epoch": 1000002},
    ]
    fragments = [{"title": "Test", "types": [], "base_epoch": 1000000, "end_epoch": 1000300, "turns": turns}]
    groups = build_gcf_groups("evt-006", 1000000, fragments, 8, 100)
    msgs = groups[0]["conversation_list"]
    assert len(msgs) == 1
    assert msgs[0]["sender"] == "unified_001"


def test_build_gcf_user_details():
    """user_details includes all normalized speakers with correct structure."""
    turns = [
        {"speaker_label": "user", "content": "hi", "offset_seconds": 0, "absolute_epoch": 1000000},
        {"speaker_label": "unified_001", "content": "hey", "offset_seconds": 1, "absolute_epoch": 1000001},
    ]
    fragments = [{"title": "T", "types": [], "base_epoch": 1000000, "end_epoch": 1000300, "turns": turns}]
    groups = build_gcf_groups("evt-007", 1000000, fragments, 8, 100)
    ud = groups[0]["conversation_meta"]["user_details"]
    assert "user_main" in ud
    assert ud["user_main"]["full_name"] == "主用户"
    assert ud["user_main"]["custom_role"] == "记录者"
    assert "unified_001" in ud
    assert ud["unified_001"]["role"] == "user"


def test_build_gcf_message_id_format():
    """Message IDs use correct format for split vs non-split events."""
    fragments = [{"title": "T", "types": [], "base_epoch": 1000000, "end_epoch": 1000300, "turns": _make_turns(2)}]
    # Non-split
    groups = build_gcf_groups("evt-008", 1000000, fragments, 8, 100)
    assert groups[0]["conversation_list"][0]["message_id"] == "evt-008_0"
    assert groups[0]["conversation_list"][1]["message_id"] == "evt-008_1"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/jameslimer/Spiro/evermemos_competition && python -m pytest tests/test_convert_to_gcf.py::test_build_gcf_single_group_no_split -v`
Expected: FAIL — `ImportError: cannot import name 'build_gcf_groups'`

---

### Task 4: GCF builder and splitter — implementation

**Files:**
- Modify: `scripts/convert_to_gcf.py`

- [ ] **Step 1: Implement `build_gcf_groups()`**

Append to `scripts/convert_to_gcf.py`:

```python
from datetime import datetime
from zoneinfo import ZoneInfo

TIMEZONE = ZoneInfo("Asia/Shanghai")

_TURN_WINDOW_SIZE = 100  # For windowed splitting of single large fragments


def _epoch_to_iso(epoch: int) -> str:
    """Convert epoch seconds to ISO 8601 with Asia/Shanghai timezone."""
    return datetime.fromtimestamp(epoch, tz=TIMEZONE).isoformat()


def _build_user_details(speakers: set[str]) -> dict:
    """Build GCF user_details from a set of normalized speaker IDs."""
    details = {}
    for s in sorted(speakers):
        if s == "user_main":
            details[s] = {"full_name": "主用户", "role": "user", "custom_role": "记录者"}
        else:
            details[s] = {"full_name": s, "role": "user"}
    return details


def _build_conversation_list(
    turns: list[dict], group_id: str, is_split: bool, part_index: int
) -> list[dict]:
    """Convert parsed turns into GCF conversation_list messages."""
    messages = []
    msg_idx = 0
    for turn in turns:
        speaker = turn["speaker_label"]
        if should_skip_speaker(speaker):
            continue
        normalized = normalize_speaker(speaker)
        msg_id = f"{group_id}_{msg_idx}"
        messages.append({
            "message_id": msg_id,
            "create_time": _epoch_to_iso(turn["absolute_epoch"]),
            "sender": normalized,
            "sender_name": speaker,
            "role": "user",
            "type": "text",
            "content": turn["content"],
            "refer_list": [],
        })
        msg_idx += 1
    return messages


def _build_single_gcf(
    group_id: str,
    title: str | None,
    types: list[str],
    base_epoch: int,
    messages: list[dict],
) -> dict:
    """Build a complete GCF dict from components."""
    speakers = {m["sender"] for m in messages}
    return {
        "version": "1.0.0",
        "conversation_meta": {
            "group_id": group_id,
            "name": title or "Untitled",
            "description": title or "",
            "scene": "group_chat",
            "scene_desc": {
                "description": title or "",
                "type": types[0] if types else "unknown",
            },
            "created_at": _epoch_to_iso(base_epoch),
            "default_timezone": "Asia/Shanghai",
            "user_details": _build_user_details(speakers),
            "tags": types,
        },
        "conversation_list": messages,
    }


def build_gcf_groups(
    event_id: str,
    event_start_epoch: int,
    fragments: list[dict],
    split_frag_threshold: int = 8,
    split_turn_threshold: int = 100,
) -> list[dict]:
    """Build GCF group dicts from parsed fragments with smart splitting.

    Returns a list of GCF dicts (each is a complete GroupChatFormat JSON structure).
    """
    total_turns = sum(len(f["turns"]) for f in fragments)
    needs_split = len(fragments) > split_frag_threshold or total_turns > split_turn_threshold

    # Special case: single fragment with lots of turns → window split
    if len(fragments) == 1 and total_turns > 200:
        frag = fragments[0]
        groups = []
        turns = frag["turns"]
        for part_idx in range(0, len(turns), _TURN_WINDOW_SIZE):
            window = turns[part_idx : part_idx + _TURN_WINDOW_SIZE]
            gid = f"{event_id}_part{part_idx // _TURN_WINDOW_SIZE}"
            msgs = _build_conversation_list(window, gid, is_split=True, part_index=part_idx // _TURN_WINDOW_SIZE)
            if msgs:
                groups.append(_build_single_gcf(gid, frag["title"], frag["types"], frag["base_epoch"], msgs))
        return groups

    if not needs_split:
        # Merge all fragments into one group
        all_turns = []
        for f in fragments:
            all_turns.extend(f["turns"])
        msgs = _build_conversation_list(all_turns, event_id, is_split=False, part_index=0)
        if not msgs:
            return []
        title = fragments[0]["title"] if fragments else None
        types = fragments[0]["types"] if fragments else []
        base = fragments[0]["base_epoch"] if fragments else event_start_epoch
        return [_build_single_gcf(event_id, title, types, base, msgs)]

    # Split: one group per fragment
    groups = []
    for part_idx, frag in enumerate(fragments):
        gid = f"{event_id}_part{part_idx}"
        msgs = _build_conversation_list(frag["turns"], gid, is_split=True, part_index=part_idx)
        if msgs:
            groups.append(_build_single_gcf(gid, frag["title"], frag["types"], frag["base_epoch"], msgs))
    return groups
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `cd /home/jameslimer/Spiro/evermemos_competition && python -m pytest tests/test_convert_to_gcf.py -v`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add scripts/convert_to_gcf.py tests/test_convert_to_gcf.py
git commit -m "feat: add GCF group builder with smart splitting"
```

---

## Chunk 3: CLI Entry Point, Makefile, and End-to-End Validation

### Task 5: CLI entry point — tests

**Files:**
- Modify: `tests/test_convert_to_gcf.py`

- [ ] **Step 1: Write integration test for full event conversion**

```python
# Append to tests/test_convert_to_gcf.py
from scripts.convert_to_gcf import convert_event

def test_convert_event_full_pipeline():
    """Integration test: raw event dict → list of GCF dicts."""
    event = {
        "meta": {
            "user_id": "79ef7f17",
            "basic_event_id": "test-event-001",
            "basic_start_time": 1000000,
            "basic_end_time": 1000600,
        },
        "object": {
            "basic_transcript": """[Fragment 1: 1000000 - 1000300]
标题: Morning Chat
类型: social

[00:00][user]: 早上好
[00:05][unified_001]: 你好啊
[00:10][背景音]: 鸟叫声

[Fragment 2: 1000300 - 1000600]
标题: Work Discussion
类型: career

[00:00][User]: 今天的任务是什么
[00:05][unified_001]: 写代码""",
        },
    }
    groups = convert_event(event, split_frag_threshold=8, split_turn_threshold=100)
    assert len(groups) == 1  # 2 frags < 8, 4 valid turns < 100
    gcf = groups[0]
    assert gcf["conversation_meta"]["group_id"] == "test-event-001"
    assert gcf["conversation_meta"]["tags"] == ["social"]  # from first fragment
    # Background speaker filtered out
    assert len(gcf["conversation_list"]) == 4
    # user and User both normalized
    senders = [m["sender"] for m in gcf["conversation_list"]]
    assert senders.count("user_main") == 2
    assert senders.count("unified_001") == 2


def test_convert_event_empty_transcript():
    """Events with empty transcripts return empty list."""
    event = {
        "meta": {"user_id": "x", "basic_event_id": "empty-001", "basic_start_time": 0, "basic_end_time": 0},
        "object": {"basic_transcript": ""},
    }
    groups = convert_event(event)
    assert groups == []


def test_convert_event_passive_only():
    """Events with only passive media fragments return empty list."""
    event = {
        "meta": {"user_id": "x", "basic_event_id": "passive-001", "basic_start_time": 0, "basic_end_time": 0},
        "object": {"basic_transcript": """[Fragment 1: 1000000 - 1000300]
标题: 收听播客
类型: interest

(被动媒体，转录内容已略过)"""},
    }
    groups = convert_event(event)
    assert groups == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/jameslimer/Spiro/evermemos_competition && python -m pytest tests/test_convert_to_gcf.py::test_convert_event_full_pipeline -v`
Expected: FAIL — `ImportError: cannot import name 'convert_event'`

---

### Task 6: CLI entry point — implementation

**Files:**
- Modify: `scripts/convert_to_gcf.py`

- [ ] **Step 1: Implement `convert_event()` and `main()` CLI**

Append to `scripts/convert_to_gcf.py`:

```python
import argparse
import json
import sys
from pathlib import Path


def convert_event(
    event: dict,
    split_frag_threshold: int = 8,
    split_turn_threshold: int = 100,
) -> list[dict]:
    """Convert a single dataset event to a list of GCF group dicts.

    Returns empty list if the event should be skipped (empty/passive).
    """
    transcript = event["object"].get("basic_transcript", "")
    if not transcript or not transcript.strip():
        return []

    event_id = event["meta"]["basic_event_id"]
    start_epoch = event["meta"]["basic_start_time"]

    fragments = parse_fragments(transcript, start_epoch)
    if not fragments:
        return []

    return build_gcf_groups(event_id, start_epoch, fragments, split_frag_threshold, split_turn_threshold)


def main():
    parser = argparse.ArgumentParser(description="Convert dataset to GroupChatFormat JSON files")
    parser.add_argument("--input", required=True, help="Path to dataset JSON file")
    parser.add_argument("--output", required=True, help="Output directory for GCF files")
    parser.add_argument("--split-threshold-fragments", type=int, default=8, help="Split events with more fragments than this")
    parser.add_argument("--split-threshold-turns", type=int, default=100, help="Split events with more total turns than this")
    parser.add_argument("--limit", type=int, default=0, help="Process only N events (0 = all)")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(input_path, "r", encoding="utf-8") as f:
        events = json.load(f)

    events.sort(key=lambda e: e["meta"]["basic_start_time"])
    if args.limit > 0:
        events = events[: args.limit]

    total = len(events)
    skipped = 0
    split_count = 0
    total_groups = 0
    total_messages = 0

    for i, event in enumerate(events):
        event_id = event["meta"]["basic_event_id"]
        groups = convert_event(event, args.split_threshold_fragments, args.split_threshold_turns)

        if not groups:
            skipped += 1
            continue

        if len(groups) > 1:
            split_count += 1

        for gcf in groups:
            gid = gcf["conversation_meta"]["group_id"]
            out_path = output_dir / f"{gid}.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(gcf, f, ensure_ascii=False, indent=2)
            total_groups += 1
            total_messages += len(gcf["conversation_list"])

        if (i + 1) % 50 == 0:
            print(f"  [{i+1}/{total}] processed...")

    print(f"\nConversion complete:")
    print(f"  Events processed: {total}")
    print(f"  Events skipped:   {skipped}")
    print(f"  Events split:     {split_count}")
    print(f"  GCF files output: {total_groups}")
    print(f"  Total messages:   {total_messages}")
    print(f"  Output directory: {output_dir}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run all tests**

Run: `cd /home/jameslimer/Spiro/evermemos_competition && python -m pytest tests/test_convert_to_gcf.py -v`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add scripts/convert_to_gcf.py tests/test_convert_to_gcf.py
git commit -m "feat: add CLI entry point for GCF conversion"
```

---

### Task 7: Makefile integration

**Files:**
- Modify: `Makefile`

- [ ] **Step 1: Add `convert-gcf` and `ingest-gcf` targets to Makefile**

Add before the `clean:` target:

```makefile
convert-gcf: ## 转换数据集为 GroupChatFormat (INPUT=path/to/data.json [LIMIT=N])
	@if [ -z "$(INPUT)" ]; then \
		echo "用法: make convert-gcf INPUT=Dataset/basic_events_79ef7f17.json"; \
		echo "可选: LIMIT=10"; \
		exit 1; \
	fi
	@mkdir -p data/gcf
	python scripts/convert_to_gcf.py --input $(INPUT) --output data/gcf/ \
		$(if $(LIMIT),--limit $(LIMIT))

ingest-gcf: ## 通过官方工具灌入所有 GCF 文件
	@if [ ! -d data/gcf ] || [ -z "$$(ls data/gcf/*.json 2>/dev/null)" ]; then \
		echo "错误: data/gcf/ 中没有 JSON 文件，请先运行 make convert-gcf"; \
		exit 1; \
	fi
	@total=$$(ls data/gcf/*.json | wc -l); count=0; \
	for f in $$(realpath data/gcf/*.json); do \
		count=$$((count + 1)); \
		echo "[$$count/$$total] Ingesting $$(basename $$f) ..."; \
		(cd EverMemOS && uv run python src/bootstrap.py src/run_memorize.py \
			--input "$$f" --scene group_chat \
			--api-url $(EVERMEMOS_URL)/api/v1/memories) || true; \
	done; \
	echo "✓ 灌入完成: $$total files"
```

Also update the `.PHONY` line to include the new targets:

```makefile
.PHONY: help init init-env deploy stop status add-memory ingest-data run-task clean codex-bin codex-config convert-gcf ingest-gcf
```

Also add `data/gcf/` to the `clean:` target by appending `rm -rf data/gcf` before the `find` command.

- [ ] **Step 2: Verify Makefile syntax**

Run: `cd /home/jameslimer/Spiro/evermemos_competition && make help`
Expected: `convert-gcf` and `ingest-gcf` appear in the help output

- [ ] **Step 3: Commit**

```bash
git add Makefile
git commit -m "feat: add convert-gcf and ingest-gcf Makefile targets"
```

---

### Task 8: End-to-end smoke test

- [ ] **Step 1: Run conversion on first 5 events**

Run: `cd /home/jameslimer/Spiro/evermemos_competition && python scripts/convert_to_gcf.py --input Dataset/basic_events_79ef7f17.json --output data/gcf/ --limit 5`
Expected: Summary output showing events processed, skipped, GCF files created.

- [ ] **Step 2: Validate one output file manually**

Run: `cd /home/jameslimer/Spiro/evermemos_competition && python -c "import json; d=json.load(open('data/gcf/' + __import__('os').listdir('data/gcf')[0])); print(json.dumps(d['conversation_meta'], indent=2, ensure_ascii=False)); print(f'Messages: {len(d[\"conversation_list\"])}')" `
Expected: Valid GCF structure with `version`, `conversation_meta` (group_id, name, scene, user_details, tags), `conversation_list`.

- [ ] **Step 3: Validate with EverMemOS validator (if services running)**

Run: `cd /home/jameslimer/Spiro/evermemos_competition && f=$(ls data/gcf/*.json | head -1) && (cd EverMemOS && uv run python src/bootstrap.py src/run_memorize.py --input "$(realpath ../$f)" --scene group_chat --validate-only)`
Expected: "Format validation passed"

- [ ] **Step 4: Clean up test output**

Run: `rm -rf data/gcf/`

- [ ] **Step 5: Run full test suite**

Run: `cd /home/jameslimer/Spiro/evermemos_competition && python -m pytest tests/ -v`
Expected: All tests pass (existing + new)
