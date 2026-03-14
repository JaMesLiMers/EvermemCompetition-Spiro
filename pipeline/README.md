# Pipeline: Data Preprocessing for EverMemOS

## Overview

Data preprocessing pipeline that transforms raw audio events into structured memories for EverMemOS. Part of the **Spiro** project — a context-native empathic AI wearable band built for the EverMemOS competition.

The pipeline takes 832 raw conversation events (transcribed audio recordings from daily life), enriches them with LLM-inferred speaker roles, converts them to GroupChatFormat (GCF), and batch-ingests them into a running EverMemOS instance.

## Pipeline Flow

```
                         ┌──────────────────────┐
                         │   Raw Audio Files     │
                         │   (.mp3, .wav, .m4a)  │
                         └──────────┬───────────┘
                                    │
                         extract_transcript.py
                         (Gemini 3 Pro via uni-api)
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  Raw Events JSON (832 events) │
                    │  meta: event_id, timestamps   │
                    │  object: basic_transcript     │
                    └───────────────┬───────────────┘
                                    │
                    generate_speaker_mapping.py
                    (GPT-4o-mini, async, 10 concurrent)
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  Speaker Mappings JSON         │
                    │  event_id → {labels, source}   │
                    └───────────────┬───────────────┘
                                    │
                         convert_to_gcf.py
                      (transcript_parser.py)
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  GCF JSON (merged array)       │
                    │  conversation_meta + messages   │
                    └───────────────┬───────────────┘
                                    │
                          ingest_gcf.py
                       (async, 5 concurrent)
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │       EverMemOS Instance       │
                    │   http://localhost:1995        │
                    └───────────────────────────────┘
```

## Scripts

### 1. `extract_transcript.py`

Extracts structured transcripts from raw audio files using Gemini 3 Pro.

- **What it does:** Sends audio to Gemini 3 Pro via uni-api, receives a structured transcript with Fragment segmentation, speaker identification, and emotion/tone annotations.
- **Key features:**
  - Supports MP3, WAV, M4A, OGG, FLAC, and WebM audio formats
  - Outputs JSON matching the EverMemOS `basic_events` dataset format
  - Automatically parses Fragment timestamps to compute event start/end times
  - Falls back to current time if no Fragment headers are found
- **Input:** Audio file (any supported format)
- **Output:** Event JSON with `meta` (user_id, event_id, timestamps) and `object` (basic_transcript)

**CLI arguments:**

| Argument | Required | Default | Description |
|---|---|---|---|
| `audio_file` | Yes | — | Path to the audio file |
| `-o, --output` | No | stdout | Output JSON file path |
| `--user-id` | No | `79ef7f17-9d24-4a85-a6fe-de7d060bc090` | User ID for the event |

**Environment:** Requires `LLM_API_KEY` in `pipeline/.env`.

---

### 2. `generate_speaker_mapping.py`

Batch-generates speaker role mappings for all events using an LLM.

- **What it does:** Sends each event's transcript (with title/type context) to GPT-4o-mini to infer concrete speaker roles (e.g., "product manager", "wife", "interviewer") from generic labels like "Speaker 1" or "Speaker 2/female".
- **Key features:**
  - Async concurrent processing with configurable concurrency (default: 10)
  - Resumable — skips events with existing mappings unless `--force` is used
  - Dry-run mode to preview what would be processed
  - Truncates long transcripts to 4000 chars (60% beginning, 40% end) for context
  - Retries failed LLM calls up to 3 times with exponential backoff
  - Skips events with no transcript, only main-user speakers, or only background/environment labels
  - Progress bar via tqdm
- **Input:** Dataset JSON file (array of events)
- **Output:** Speaker mappings JSON — `{event_id: {labels: {raw_label: role}, source: "llm"|"empty"|"user_only"|"error"}}`

**CLI arguments:**

| Argument | Required | Default | Description |
|---|---|---|---|
| `--input` | Yes | — | Path to dataset JSON file |
| `--output` | No | `data/speaker_mappings.json` | Output mapping file |
| `--api-base` | No | `https://api.uniapi.me/v1` | OpenAI-compatible API base URL |
| `--api-key` | No | `$OPENCODE_API_KEY` env | API key for LLM calls |
| `--model` | No | `gpt-4o-mini` | Model to use for inference |
| `--concurrency` | No | `10` | Max concurrent LLM calls |
| `--dry-run` | No | false | Preview without calling LLM |
| `--force` | No | false | Regenerate all (ignore existing) |

---

### 3. `convert_to_gcf.py`

Converts the competition dataset events into EverMemOS GroupChatFormat (GCF) JSON.

- **What it does:** Parses each event's transcript into fragments and speaker turns, applies speaker mappings (both embedded in the event and from the transcript's mapping table), normalizes speakers, filters out background/environment noise, and builds GCF group structures.
- **Key features:**
  - Smart splitting: events with >8 fragments or >100 turns are split into per-fragment groups
  - Windowed splitting: single fragments with >200 turns are split into windows of 100 turns
  - Speaker enrichment from embedded `speaker_mapping` field and in-transcript mapping tables
  - Filters out background, environment, and media speakers
  - Normalizes main-user aliases ("user", "User", "用户") to `user_main`
  - Skips passive media fragments (content marked as omitted)
  - Interpolates timestamps for Format B turns (no inline timestamps) across fragment duration
  - Outputs all groups as a single merged JSON array
- **Input:** Dataset JSON file (array of events)
- **Output:** Single GCF JSON file (array of group objects)

**CLI arguments:**

| Argument | Required | Default | Description |
|---|---|---|---|
| `--input` | Yes | — | Path to dataset JSON file |
| `--output` | No | `data/gcf_all.json` | Output JSON file path |
| `--split-threshold-fragments` | No | `8` | Split events with more fragments than this |
| `--split-threshold-turns` | No | `100` | Split events with more total turns than this |
| `--limit` | No | `0` (all) | Process only N events |

---

### 4. `transcript_parser.py`

Shared transcript parsing library used by `convert_to_gcf.py`.

- **What it does:** Parses raw transcript text into structured speaker turns with absolute timestamps, handling multiple transcript formats and Fragment boundaries.
- **Key features:**
  - Two transcript formats:
    - **Format A** (legacy): `[MM:SS][speaker]: text` — timestamps are directly parsed
    - **Format B** (primary): `[speaker]: text` — timestamps are interpolated across fragment duration
  - Parses Fragment headers with flexible time formats: `YYYY-MM-DD HH:MM`, epoch seconds, or `HH:MM` offsets
  - Strips annotation keywords (tone, speed, emotion markers like `[思考停顿]`, `[语速加快]`)
  - Extracts per-fragment title and type metadata
  - Handles implicit fragments (content before any Fragment header)
- **Input:** Raw transcript string + event start epoch
- **Output:** List of turn dicts with `speaker_label`, `content`, `offset_seconds`, `absolute_epoch`

This module is not invoked directly — it is imported by `convert_to_gcf.py`.

---

### 5. `ingest_gcf.py`

Batch-ingests GCF JSON into a running EverMemOS instance via its REST API.

- **What it does:** Reads the merged GCF file and ingests all groups with async concurrent requests. For each group, it first saves conversation metadata, then posts messages sequentially (order matters for EverMemOS memory boundary detection).
- **Key features:**
  - Async concurrent group ingestion (default: 5 concurrent groups)
  - Sequential message posting within each group to preserve conversation order
  - Dual progress bars (groups + messages) via tqdm
  - Reports throughput (messages/second) on completion
  - 300-second HTTP timeout for slow responses
- **Input:** Merged GCF JSON file (array of groups)
- **Output:** Messages ingested into EverMemOS via REST API

**CLI arguments:**

| Argument | Required | Default | Description |
|---|---|---|---|
| `--input` | No | `data/gcf_all.json` | Merged GCF JSON file |
| `--api-url` | No | `http://localhost:1995/api/v1/memories` | EverMemOS API URL |
| `--scene` | No | `group_chat` | Scene type |
| `--concurrency` | No | `5` | Max concurrent group ingestions |

## Usage

All pipeline steps have corresponding Make targets. Run from the project root.

### Step 1: Extract transcript from audio (optional — for new recordings)

```bash
# Transcribe an audio file to event JSON
python -m pipeline.extract_transcript recording.mp3 -o data/new_event.json

# With custom user ID
python -m pipeline.extract_transcript recording.m4a -o data/new_event.json --user-id my-user-id
```

### Step 2: Generate speaker mappings

```bash
# Generate mappings (resumes from existing file)
make generate-speaker-mappings INPUT=data/basic_events_79ef7f17.json

# Preview without calling LLM
make generate-speaker-mappings INPUT=data/basic_events_79ef7f17.json DRY_RUN=1

# Force regeneration with a different model
make generate-speaker-mappings INPUT=data/basic_events_79ef7f17.json MODEL=gpt-4o CONCURRENCY=20
```

### Step 3: Convert to GCF

```bash
# Convert all events
make convert-gcf INPUT=data/basic_events_79ef7f17.json

# Convert with custom thresholds
make convert-gcf INPUT=data/basic_events_79ef7f17.json SPLIT_FRAGS=5 SPLIT_TURNS=50

# Convert only first 10 events (for testing)
make convert-gcf INPUT=data/basic_events_79ef7f17.json LIMIT=10
```

### Step 4: Ingest into EverMemOS

```bash
# Ingest with defaults (reads data/gcf_all.json, localhost:1995)
make ingest-gcf

# Custom input and concurrency
make ingest-gcf INPUT=data/gcf_all.json CONCURRENCY=8

# Custom API URL
make ingest-gcf API_URL=http://remote-host:1995/api/v1/memories
```

### Full pipeline (all steps)

```bash
make generate-speaker-mappings INPUT=data/basic_events_79ef7f17.json
make convert-gcf INPUT=data/basic_events_79ef7f17.json
make ingest-gcf
```

## Data Formats

### Input: Raw Event

Each event in the dataset JSON array has:

```json
{
  "meta": {
    "user_id": "79ef7f17-...",
    "basic_event_id": "abc123-...",
    "basic_start_time": 1766845585,
    "basic_end_time": 1766847385
  },
  "object": {
    "basic_transcript": "[Fragment 1: 2026-02-23 06:13 - 2026-02-23 06:43]\n标题: ...\n类型: career\n\n[用户]: ...\n[说话人1/女]: ...",
    "speaker_mapping": {
      "说话人1/女": "产品经理"
    }
  }
}
```

### Speaker Mapping

Per-event mapping from raw speaker labels to inferred roles:

```json
{
  "abc123-...": {
    "labels": {
      "说话人1/女": "产品经理",
      "说话人2": "前端工程师"
    },
    "source": "llm"
  }
}
```

`source` values: `"llm"` (inferred by model), `"empty"` (no transcript), `"user_only"` (only main user speaks), `"error"` (LLM call failed).

### GCF Output

Each group in the output JSON array:

```json
{
  "version": "1.0.0",
  "conversation_meta": {
    "group_id": "abc123-...",
    "name": "关于产品设计方案的讨论",
    "description": "关于产品设计方案的讨论",
    "scene": "group_chat",
    "scene_desc": {
      "description": "关于产品设计方案的讨论",
      "type": "career"
    },
    "created_at": "2026-02-23T06:13:05+08:00",
    "default_timezone": "Asia/Shanghai",
    "user_details": {
      "user_main": {"full_name": "主用户", "role": "user", "custom_role": "记录者"},
      "产品经理": {"full_name": "产品经理", "role": "user"}
    },
    "tags": ["career"]
  },
  "conversation_list": [
    {
      "message_id": "abc123-..._0",
      "create_time": "2026-02-23T06:13:05+08:00",
      "sender": "user_main",
      "sender_name": "用户",
      "role": "user",
      "type": "text",
      "content": "我们来看一下这个方案。",
      "refer_list": []
    }
  ]
}
```
