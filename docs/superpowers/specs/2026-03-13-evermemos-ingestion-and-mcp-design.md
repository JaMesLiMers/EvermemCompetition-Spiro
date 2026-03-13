# EverMemOS Data Ingestion & MCP Server Design

## Overview

Build two components to make EverMemOS usable with the competition dataset:

1. **Data Ingestion Script** — Parse `Dataset/basic_events_79ef7f17.json` (832 events, 20.5MB) and batch-feed raw transcript turns into EverMemOS via its REST API.
2. **MCP Server** — Thin wrapper around EverMemOS REST API, enabling Claude Code to store, search, and retrieve memories directly.

### Target Use Cases

- **A) Q&A** — Answer questions about past events using memory search
- **B) Profiling** — Build and query user profiles/insights from extracted memories
- **C) Proactive Suggestions** — Use foresight memories to surface relevant context and recommendations

## Component 1: Data Ingestion Script

### Purpose

Transform the competition dataset's event data into EverMemOS-compatible messages and feed them via the `/api/v1/memories` API.

### Data Format

Each event in the dataset contains:

- **meta**: `user_id`, `basic_event_id`, `basic_start_time`, `basic_end_time`, timestamps
- **object**: `basic_transcript`, `basic_summary`, `basic_speaker_analysis`, `basic_type`, `basic_scene`, etc.

**User ID**: `79ef7f17-9d24-4a85-a6fe-de7d060bc090` (single user across all events)

### Transcript Format

Transcripts contain Fragment headers and speaker turns:

```
[Fragment 1: 2026-02-23 06:13 - 2026-02-23 06:20]
标题: APP设计方案的用户反馈
类型: career, self_awareness

[00:00][访谈主持人/用户研究员/产品经理]: [音调平稳] 具体的设计，比如说...
[00:06][受访对象/产品测试用户]: [思考停顿] 如果说是落实到...
```

Speaker turn format: `[MM:SS][SpeakerLabel]: [annotations] content`

### Speaker Analysis Format

JSON array in `basic_speaker_analysis`:
```json
[
  {
    "unified_speaker_id": "unified_000",
    "is_user": true,
    "identity": "",
    "relation_to_user": "用户本人",
    "gender": "unknown"
  },
  {
    "unified_speaker_id": "unified_001",
    "is_user": false,
    "identity": "用户研究员/产品经理",
    "relation_to_user": "访谈主持人",
    "gender": "female"
  }
]
```

### Parsing Logic

1. **Parse speaker analysis** — Build a mapping from speaker label (in transcript) to speaker info (identity, is_user, relation). Match by checking if the transcript speaker label contains the speaker analysis `identity` or `relation_to_user` as a substring (e.g., transcript label `访谈主持人/用户研究员/产品经理` matches speaker with `relation_to_user: "访谈主持人"` and `identity: "用户研究员/产品经理"`). If no match found, assign to a fallback "unknown" speaker.
2. **Parse transcript** — Split by lines, identify Fragment headers (`[Fragment N: start - end]`) and speaker turns (`[MM:SS][Speaker]: content`).
3. **Calculate absolute timestamps** — For each Fragment, use the Fragment's start time as base. Add the `MM:SS` offset to compute absolute `create_time` for each turn.
4. **Strip annotations** — Remove `[音调平稳]`, `[思考停顿]` etc. from content, keeping only the actual speech text.

### Ingestion Flow

For each event:

1. **Create conversation-meta** — `POST /api/v1/memories/conversation-meta` with:
   - `version`: `"1.0"`
   - `group_id`: `basic_event_id`
   - `scene`: `"assistant"` (single user's life recording device)
   - `scene_desc`: `{"description": basic_scene, "type": basic_type[0]}` (wrap the string into the required object format)
   - `name`: `basic_title`
   - `user_details`: keyed by `unified_speaker_id`, with `full_name` from transcript label, `role: "user"` for all speakers, `custom_role` from `identity` field
   - `created_at`: from `basic_start_time` (converted to ISO 8601 with Asia/Shanghai timezone, see Timezone section)

2. **Send messages** — For each parsed speaker turn, `POST /api/v1/memories` with:
   - `message_id`: `{basic_event_id}_{turn_index}`
   - `create_time`: absolute timestamp (ISO 8601 with Asia/Shanghai timezone)
   - `sender`: `unified_speaker_id` from speaker analysis
   - `sender_name`: speaker label from transcript
   - `content`: cleaned speech text
   - `group_id`: `basic_event_id`
   - `group_name`: `basic_title`
   - `role`: `"user"` (all speakers are human — this is a life recording device, no AI participants)

3. **Rate limiting** — Small delay between messages (0.1s) to avoid overwhelming the API.

### Timezone Handling

All timestamps are converted using **Asia/Shanghai (UTC+8)**. This is based on the dataset's Fragment headers showing local times (e.g., `2026-02-23 06:13`) that map to the epoch seconds assuming UTC+8.

- `basic_start_time` / `basic_end_time` (epoch seconds) → `datetime.fromtimestamp(ts, tz=ZoneInfo("Asia/Shanghai")).isoformat()`
- Fragment-relative `MM:SS` offsets → added to Fragment start time, output as ISO 8601 with `+08:00`

### Empty Event Handling

Some events (~24) have empty `basic_transcript` or empty `basic_speaker_analysis`. Handling:

- **Empty transcript**: Skip the event entirely (no messages to send), log a warning with the event ID
- **Empty speaker analysis**: Still parse and send transcript turns, but use the raw transcript speaker label as both `sender` and `sender_name`, with `is_user: false` as default

### Error Handling

- **API 4xx errors**: Log the error and skip the message, continue with the next one. Record failed message IDs in the progress file.
- **API 5xx errors**: Retry up to 3 times with exponential backoff (1s, 2s, 4s). If still failing, skip and log.
- **Malformed transcripts**: If transcript parsing fails (no valid speaker turns found), log a warning and skip the event.
- **Network timeouts**: 30s timeout per request. On timeout, retry once, then skip.
- **Partial event failures**: If conversation-meta succeeds but some messages fail, record the event as partially processed. On resume, re-send only failed messages.

### Resumability

- Maintain a progress file (`ingestion_progress.json`) tracking processed event IDs
- On restart, skip already-processed events
- Log success/failure counts per event

### Script Structure

```
scripts/
├── ingest_data.py         # Main ingestion script
└── ingestion_progress.json # Auto-generated progress tracking
```

### CLI Interface

```bash
python scripts/ingest_data.py \
  --input Dataset/basic_events_79ef7f17.json \
  --api-url http://localhost:1995/api/v1/memories \
  --resume  # optional: resume from last checkpoint
```

## Component 2: MCP Server

### Purpose

Wrap EverMemOS REST API as MCP tools so Claude Code can interact with the memory system directly.

### Technology

- Python with `mcp` SDK
- `httpx` for async HTTP calls to EverMemOS
- Configured via environment variable `EVERMEMOS_BASE_URL` (default: `http://localhost:1995`)

### Tools

#### `search_memory`

Search memories using various retrieval methods.

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | no | - | Search query text (at least one of query, user_id, or group_id required) |
| `user_id` | string | no | - | User ID filter |
| `group_id` | string | no | - | Group ID filter |
| `retrieve_method` | string | no | `"keyword"` | One of: keyword, vector, hybrid, rrf, agentic |
| `memory_types` | list[string] | no | `["episodic_memory"]` | Types: episodic_memory, foresight, event_log |
| `top_k` | int | no | 40 | Max results (max: 100) |
| `start_time` | string | no | - | ISO 8601 start filter |
| `end_time` | string | no | - | ISO 8601 end filter |

**Maps to:** `GET /api/v1/memories/search`

**Note:** The search endpoint uses GET with a JSON request body. The httpx client must explicitly send the body with a GET request.

#### `get_memories`

Fetch memories by type with pagination.

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `user_id` | string | no | - | User ID |
| `group_id` | string | no | - | Group ID |
| `memory_type` | string | no | `"episodic_memory"` | One of: profile, episodic_memory, foresight, event_log |
| `limit` | int | no | 40 | Max results |
| `offset` | int | no | 0 | Pagination offset |
| `start_time` | string | no | - | ISO 8601 start filter |
| `end_time` | string | no | - | ISO 8601 end filter |

**Maps to:** `GET /api/v1/memories`

#### `store_message`

Store a new message into EverMemOS memory.

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `content` | string | yes | - | Message content |
| `sender` | string | yes | - | Sender ID |
| `message_id` | string | no | auto-generated UUID | Unique message ID (MCP server generates if omitted) |
| `create_time` | string | no | current time ISO 8601 | Timestamp (MCP server generates if omitted) |
| `sender_name` | string | no | sender | Display name |
| `group_id` | string | no | - | Group ID |
| `group_name` | string | no | - | Group name |
| `role` | string | no | `"user"` | user or assistant |

**Maps to:** `POST /api/v1/memories`

#### `get_conversation_meta`

Get conversation metadata.

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `group_id` | string | no | - | Group ID |

**Maps to:** `GET /api/v1/memories/conversation-meta`

#### `delete_memories`

Delete memories by filter criteria. Filters use AND logic — providing both `user_id` and `group_id` deletes only memories matching both.

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `event_id` | string | no | - | Event ID filter |
| `user_id` | string | no | - | User ID filter |
| `group_id` | string | no | - | Group ID filter |

**Maps to:** `DELETE /api/v1/memories`

### Project Structure

```
mcp_server/
├── server.py              # MCP Server entry point + tool definitions
├── evermemos_client.py    # Async HTTP client wrapping EverMemOS API
└── requirements.txt       # mcp, httpx
```

### Claude Code Configuration

`.claude/settings.json`:
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

## Implementation Order

1. **Data Ingestion Script** — Must run first to populate EverMemOS with data
2. **MCP Server** — Can be developed in parallel, but useful only after data is ingested
3. **Integration Testing** — Verify Claude Code can search and retrieve memories via MCP

## Key Constants

- **User ID**: `79ef7f17-9d24-4a85-a6fe-de7d060bc090`
- **Total Events**: 832
- **EverMemOS Base URL**: `http://localhost:1995`
- **API Prefix**: `/api/v1/memories`
