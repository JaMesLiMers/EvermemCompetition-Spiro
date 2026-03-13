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

### Speaker Turn Formats

The dataset contains two speaker turn formats:

**Format A (timestamped):**
```
[MM:SS][speaker_label]: [annotations] actual content
```

**Format B (no timestamp):**
```
[speaker_label]: actual content
```

Both formats must be parsed. The parser tries Format A first, then falls back to Format B.

### Fragment Structure

```
[Fragment N: start - end]
标题: ...
类型: ...

[speaker turns...]
```

Two time formats in Fragment headers:
- Date: `[Fragment 1: 2026-02-23 06:13 - 2026-02-23 06:20]`
- Epoch: `[Fragment 1: 1766845585 - 1766845945]`

### Parsing Steps

1. Split transcript by Fragment headers using regex `\[Fragment \d+: (.+?) - (.+?)\]`
2. Extract Fragment start time (parse date or epoch)
3. Parse each line:
   - Try Format A: `\[(\d{2}:\d{2})\]\[(.+?)\]: (.+)` → (offset, speaker, content)
   - Fallback Format B: `\[(.+?)\]: (.+)` → (speaker, content), no time offset
4. Strip audio annotations using a whitelist of known annotation keywords: 音调, 语速, 语气, 停顿, 音量, 说明, 理解, 引导, 列举, 表示, 肯定, 犹豫, 思考, 认真, 专业, 正常, 平稳, 较快, 稍快, 平缓, 上扬, 降低, 恢复. Only `[...]` brackets containing these keywords are stripped; other brackets (e.g., `[APP名称]`) are preserved.
5. Calculate absolute time:
   - Format A: Fragment start + MM:SS offset
   - Format B: Interpolate evenly across Fragment duration based on turn index within that Fragment
6. Map sender:
   - Use the speaker label string directly as both sender and sender_name
   - No speaker_analysis mapping (field not present in dataset)

### Special Speaker Labels

- `Media_Playback` and similar media labels (e.g., `被动媒体内容/[Media]...`) — include as regular turns, they represent ambient context that EverMemOS can use for memory extraction

### Skip Rules

- Empty transcript → skip entire event
- Events where transcript has content but yields zero parsed speaker turns → skip, log warning
- Lines that don't match either speaker turn format → skip line

## Message Construction

Each parsed speaker turn becomes one message:

```json
{
  "message_id": "{event_id}_{turn_idx}",
  "create_time": "2026-02-23T06:13:30+08:00",
  "sender": "speaker_label",
  "sender_name": "speaker_label",
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
  "scene": "group_chat",
  "scene_desc": {"description": "生活记录对话"},
  "name": "{first_fragment_title}",
  "group_id": "{basic_event_id}",
  "created_at": "ISO8601 of basic_start_time in Asia/Shanghai",
  "default_timezone": "Asia/Shanghai",
  "user_details": {
    "Speaker A": {"full_name": "Speaker A", "role": "user"},
    "Speaker B": {"full_name": "Speaker B", "role": "user"}
  }
}
```

- `scene` must be `"group_chat"` or `"assistant"` (enum constraint)
- `name` sourced from first Fragment's `标题:` line
- `user_details` dynamically built per event from all speaker labels found in that event's transcript

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
│   → Parse Fragments and speaker turns (both formats), return message list
├── build_conversation_meta(event, speakers, fragment_title)
│   → Build conversation-meta request body
├── send_messages(messages, session)
│   → Send messages with retry and rate limiting (synchronous)
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
- `httpx` (HTTP client, synchronous mode)
- Standard library: `json`, `re`, `datetime`, `zoneinfo`, `argparse`, `pathlib`, `time`
