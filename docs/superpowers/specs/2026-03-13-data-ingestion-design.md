# EverMemOS Data Ingestion Design

## Overview

Ingest 832 events from `Dataset/basic_events_79ef7f17.json` into EverMemOS by parsing transcripts into individual speaker turns and sending them as messages via the REST API. This approach leverages EverMemOS's built-in boundary detection and memory extraction pipeline.

## Data Format

Each event contains:
- `meta.user_id` — constant: `79ef7f17-9d24-4a85-a6fe-de7d060bc090`
- `meta.basic_event_id` — UUID, used as `group_id`
- `meta.basic_start_time` / `basic_end_time` — epoch seconds
- `object.basic_transcript` — multi-fragment transcript with speaker turns

## Transcript Parsing

### Fragment Structure

```
[Fragment N: start - end]
标题: ...
类型: ...

[MM:SS][speaker_label]: [annotations] actual content
```

Two time formats in Fragment headers:
- Date: `[Fragment 1: 2026-02-23 06:13 - 2026-02-23 06:20]`
- Epoch: `[Fragment 1: 1766845585 - 1766845945]`

### Parsing Steps

1. Split transcript by Fragment headers using regex `\[Fragment \d+: (.+?) - (.+?)\]`
2. Extract Fragment start time (parse date or epoch)
3. Parse each line matching `\[(\d{2}:\d{2})\]\[(.+?)\]: (.+)` into (offset, speaker, content)
4. Strip audio annotations: remove `[音调平稳]`, `[语速:较快]`, `[思考停顿]` etc. (pattern: `\[[\u4e00-\u9fff/a-zA-Z:：]+?\]` within content)
5. Calculate absolute time: Fragment start + MM:SS offset
6. Map sender: `[user]` → user_id `79ef7f17-9d24-4a85-a6fe-de7d060bc090`; all others → use label as-is

### Skip Rules

- Empty transcript → skip entire event
- Lines that don't match speaker turn pattern → skip line

## Message Construction

Each parsed speaker turn becomes one message:

```json
{
  "message_id": "{event_id}_{fragment_idx}_{turn_idx}",
  "create_time": "2026-02-23T06:13:30+08:00",
  "sender": "unified_001",
  "sender_name": "unified_001",
  "content": "cleaned text without annotations",
  "group_id": "{basic_event_id}",
  "role": "user"
}
```

- All roles are `"user"` (no AI in this dataset)
- `sender` for `[user]` tag maps to the constant user_id
- `sender_name` preserves the original transcript label
- Timezone: `Asia/Shanghai` (UTC+8)

## Conversation Metadata

Before sending messages for each event, create conversation metadata:

```json
{
  "version": "1.0",
  "scene": "group_chat",
  "scene_desc": {"description": "生活记录对话"},
  "name": "{first_fragment_title}",
  "group_id": "{basic_event_id}",
  "created_at": "ISO8601 of basic_start_time in Asia/Shanghai",
  "default_timezone": "Asia/Shanghai",
  "user_details": {
    "79ef7f17-9d24-4a85-a6fe-de7d060bc090": {"full_name": "user", "role": "user"},
    "unified_001": {"full_name": "unified_001", "role": "user"}
  }
}
```

- `name` sourced from first Fragment's `标题:` line
- `user_details` collected from all speaker labels found in transcript

## Sending Strategy

- Sort 832 events by `basic_start_time` (chronological order)
- For each event: create conversation-meta first, then send messages in order
- Rate limit: 0.1s delay between messages
- Error handling:
  - 4xx → log warning, skip message
  - 5xx → retry up to 3 times with exponential backoff (1s, 2s, 4s)
  - Network timeout: 30s per request, retry once then skip

## Resumability

Progress tracked in `ingestion_progress.json`:

```json
{
  "completed_events": ["event_id_1", "event_id_2", ...],
  "total_messages_sent": 3847,
  "skipped_events": 2,
  "failed_messages": 0
}
```

On restart, skip events already in `completed_events`.

## Script Structure

Single file: `scripts/ingest_data.py`

```
ingest_data.py
├── parse_transcript(transcript, start_time, end_time)
│   → Parse Fragments and speaker turns, return message list
├── build_conversation_meta(event, speakers, fragment_title)
│   → Build conversation-meta request body
├── send_messages(messages, session)
│   → Send messages with retry and rate limiting
├── load_progress() / save_progress()
│   → Resumability support
└── main()
    → Load data → sort by time → iterate events → parse → send
```

### Usage

```bash
python scripts/ingest_data.py --data Dataset/basic_events_79ef7f17.json --base-url http://localhost:1995
```

### Output

- Terminal progress: `[142/832] 已发送 3847 条消息，跳过 2 个空事件`
- Summary on completion: total events, messages sent, skipped, failed

### Dependencies

- Python 3.10+
- `httpx` (async HTTP client)
- Standard library: `json`, `re`, `datetime`, `zoneinfo`, `argparse`, `pathlib`, `time`
