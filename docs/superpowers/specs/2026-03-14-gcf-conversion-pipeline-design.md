# Dataset → GroupChatFormat Conversion Pipeline Design

**Date:** 2026-03-14
**Status:** Draft

## Problem Statement

The current `ingest_data.py` script sends raw transcript turns directly to the EverMemOS REST API. This bypasses the official GroupChatFormat (GCF) pipeline and has several issues:

1. **Lost metadata** — transcript-embedded titles, types, and scene info are underutilized
2. **No speaker normalization** — `user`, `用户`, `User` all refer to the same person but are stored as separate senders
3. **Granularity mismatch** — a single event can span 43 fragments and hundreds of turns, potentially exceeding EverMemOS boundary detection's optimal range
4. **Non-standard format** — not using EverMemOS's validated GroupChatFormat, missing potential internal optimizations in `run_memorize.py`

## Solution Overview

Build a conversion script (`pipeline/convert_to_gcf.py`) that transforms competition dataset events into GroupChatFormat JSON files, then ingest via EverMemOS's official `run_memorize.py`.

```
Dataset JSON (832 events)
    ↓
pipeline/convert_to_gcf.py
    ├── Parse transcript (title, types, fragments, speaker turns)
    ├── Normalize speakers (user/用户/User → user_main)
    ├── Smart split (large events → multiple groups)
    ├── Extract types → tags
    └── Output GroupChatFormat JSON files → data/gcf/
    ↓
EverMemOS run_memorize.py (official tool)
    ├── Validate format
    ├── Create conversation-meta
    ├── POST messages one by one
    └── Automatic boundary detection → episodic_memory extraction
```

## Source Data Schema

Each event in `data/basic_events_79ef7f17.json` has this structure:

```
event["meta"]["user_id"]              # "79ef7f17-..." (single user across all events)
event["meta"]["basic_event_id"]       # UUID, unique per event
event["meta"]["basic_start_time"]     # epoch seconds (int)
event["meta"]["basic_end_time"]       # epoch seconds (int)
event["object"]["basic_transcript"]   # multi-fragment transcript string (only populated field)
```

All other `object` fields (`basic_title`, `basic_summary`, `basic_speaker_analysis`, `basic_type`, `basic_scene`) are **empty** in this dataset. Metadata (title, types) is embedded inside the transcript text itself.

## Design Details

### 1. Smart Splitting Strategy

**Goal:** Keep groups at a size where EverMemOS boundary detection works well, while preserving topic coherence.

**Rules:**
- Default: 1 event = 1 group (group_id = `basic_event_id`)
- Split when: fragment count > 8 **OR** total turn count > 100
- Split granularity: by fragment boundaries (each fragment has a clear time range and usually a distinct topic/title)
- Split naming: `{event_id}_part{n}` (0-indexed)
- Each split group inherits the event-level metadata but uses its own fragment's title and types if available

**Rationale:** Fragment boundaries are natural topic boundaries in this dataset. Each fragment has its own `标题:` and `类型:` lines. Splitting at these boundaries preserves semantic coherence.

**Edge cases:**
- Events with 0 fragments but non-empty transcript (~26 events): treat entire transcript as a single implicit fragment
- Events with empty transcript (~24 events): skip entirely
- Events with only passive media fragments ("被动媒体，转录内容已略过"): skip entirely
- Single-fragment events with >200 turns: split by 100-turn windows within the fragment

### 2. Speaker Normalization

**Main user aliases** (all map to `user_main`):
- `user`
- `用户`
- `User`

**Preserved as-is:**
- `unified_XXX` (e.g., `unified_001`, `unified_000/男`)
- `SPEAKER_XX` (e.g., `SPEAKER_01`)
- Named speakers (e.g., `访谈主持人/用户研究员/产品经理`)

**Filtered out (turns skipped):**
- Speaker labels containing `背景` (covers `背景音`, `背景声`, `背景噪音`, `背景媒体声`, `背景环境`, `背景音: 电子提示音`, etc.)
- Speaker labels containing `环境` (covers `环境音`, `路人/环境背景音/背景人声/表演者`, etc.)
- Speaker labels containing `路人` (covers `路人/背景人声`, `陌生人/路人/背景人声`, etc.)
- Speaker labels containing `无关人员`
- Speaker labels containing `Media_Guest` in passive-media fragments

**user_details mapping:**

```json
{
  "user_main": {
    "full_name": "主用户",
    "role": "user",
    "custom_role": "记录者"
  },
  "unified_001": {
    "full_name": "unified_001",
    "role": "user"
  }
}
```

### 3. Metadata Extraction

From each fragment's header and content lines:

| Source | → GCF Field |
|--------|-------------|
| `标题: <text>` | `conversation_meta.name` (first fragment's title, or event-level fallback) |
| `类型: career, social` | `conversation_meta.tags` (e.g., `["career", "social"]`) |
| Fragment time range | `conversation_meta.created_at` (ISO 8601, Asia/Shanghai) |
| All unique normalized speakers | `conversation_meta.user_details` |
| `"group_chat"` | `conversation_meta.scene` |
| Fragment title as description | `conversation_meta.description` |
| Fragment title | `conversation_meta.scene_desc.description` |
| First type as scene type | `conversation_meta.scene_desc.type` |

### 4. Message Format

Each speaker turn becomes a GCF message. Note: `type` is **required** by the EverMemOS GroupChatFormat validator.

```json
{
  "message_id": "{event_id}_{turn_index}",
  "create_time": "2026-02-23T06:13:00+08:00",
  "sender": "user_main",
  "sender_name": "用户",
  "role": "user",
  "type": "text",
  "content": "具体的设计，比如说这种字体啊，还有这些图标呢？",
  "refer_list": []
}
```

**Message ID for split events:** Use `{event_id}_part{n}_{turn_index}` to prevent collisions.
```

**Content processing:**
- Strip annotation brackets: `[音调平稳]`, `[思考停顿]`, `[专业语气]`, etc.
- Skip turns where content is empty after stripping
- Preserve actual spoken content verbatim

### 5. Filtering Rules

**Skip entire events when:**
- `basic_transcript` is empty or whitespace-only (24 events)

**Skip entire fragments when:**
- Contains "被动媒体，转录内容已略过" (passive media, no real dialogue)

**Skip individual turns when:**
- Speaker contains `背景`, `环境`, `路人`, or `无关人员`
- Content is empty after annotation stripping
- Content matches metadata patterns (`【转录】`, `[Segment ...]`)

### 6. Output Structure

```
data/gcf/
├── 000baa06-2d02-415a-b905-5c8239b3055a.json          # single-group event
├── d99dece1-dc8a-xxxx-xxxx-xxxxxxxxxxxx_part0.json     # split event part 0
├── d99dece1-dc8a-xxxx-xxxx-xxxxxxxxxxxx_part1.json     # split event part 1
└── ...
```

Each file is a valid GroupChatFormat JSON:

```json
{
  "version": "1.0.0",
  "conversation_meta": {
    "group_id": "000baa06-2d02-415a-b905-5c8239b3055a",
    "name": "APP设计方案的用户反馈：记忆认知与AI准确性",
    "scene": "group_chat",
    "scene_desc": {
      "description": "APP设计方案的用户反馈：记忆认知与AI准确性",
      "type": "career"
    },
    "created_at": "2026-02-23T06:13:00+08:00",
    "default_timezone": "Asia/Shanghai",
    "user_details": {
      "user_main": {
        "full_name": "主用户",
        "role": "user",
        "custom_role": "记录者"
      },
      "访谈主持人/用户研究员/产品经理": {
        "full_name": "访谈主持人/用户研究员/产品经理",
        "role": "user"
      }
    },
    "tags": ["career", "self_awareness"]
  },
  "conversation_list": [
    {
      "message_id": "000baa06_0",
      "create_time": "2026-02-23T06:13:00+08:00",
      "sender": "访谈主持人/用户研究员/产品经理",
      "sender_name": "访谈主持人/用户研究员/产品经理",
      "role": "user",
      "type": "text",
      "content": "具体的设计，比如说这种字体啊，还有这些图标呢？",
      "refer_list": []
    }
  ]
}
```

### 7. Ingestion Workflow

```bash
# Step 1: Convert dataset to GCF files
python pipeline/convert_to_gcf.py \
  --input data/basic_events_79ef7f17.json \
  --output data/gcf/ \
  --split-threshold-fragments 8 \
  --split-threshold-turns 100

# Step 2: Ingest via official tool (one file at a time, using absolute paths)
for f in $(realpath data/gcf/*.json); do
  (cd EverMemOS && uv run python src/bootstrap.py src/run_memorize.py \
    --input "$f" \
    --scene group_chat \
    --api-url http://localhost:1995/api/v1/memories)
done
```

A wrapper in the Makefile (`make convert-gcf` and `make ingest-gcf`) will be added for convenience.

### 8. Makefile Integration

```makefile
# Convert dataset to GroupChatFormat
convert-gcf:
	python pipeline/convert_to_gcf.py \
		--input $(INPUT) \
		--output data/gcf/

# Ingest all GCF files via official tool (uses absolute paths)
ingest-gcf:
	@for f in $$(realpath data/gcf/*.json); do \
		echo "Ingesting $$f ..."; \
		(cd EverMemOS && uv run python src/bootstrap.py src/run_memorize.py \
			--input "$$f" --scene group_chat \
			--api-url http://localhost:1995/api/v1/memories); \
	done
```

## Implementation Plan

1. **`pipeline/convert_to_gcf.py`** — New script (~200 lines)
   - Reuses existing `transcript_parser.py` for parsing
   - Adds speaker normalization logic
   - Adds smart splitting logic
   - Outputs GCF JSON files

2. **Makefile additions** — `convert-gcf` and `ingest-gcf` targets

3. **Update `ingest_data.py`** — Mark as deprecated or remove, replaced by GCF pipeline

## Reuse

- `pipeline/transcript_parser.py` — reuse `parse_speaker_turns()` for turn-level parsing. The current `parse_transcript_with_metadata()` only extracts the first fragment's title/types. The conversion script will implement its own fragment-level iteration to extract per-fragment metadata (title, types, time range, turns) for the splitting logic.
- Speaker normalization is new logic, simple enough to inline in the conversion script
- No changes needed to EverMemOS or `run_memorize.py`

## Testing

- Validate all output files: `for f in data/gcf/*.json; do run_memorize.py --validate-only --input "$f"; done`
- Conversion script prints summary stats: events processed, skipped, split count, total groups, total messages
- Spot-check edge cases: 0-fragment event, passive-media-only event, split event, speaker-normalized event
- After ingestion, query EverMemOS to verify episodic_memory quality:
  ```bash
  curl -X GET "http://localhost:1995/api/v1/memories/search" \
    -H "Content-Type: application/json" \
    -d '{"query": "用户反馈", "group_id": "000baa06-2d02-415a-b905-5c8239b3055a", "retrieve_method": "rrf", "memory_types": ["episodic_memory"]}'
  ```

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| `run_memorize.py` has undocumented requirements | Run `--validate-only` first; fall back to direct API if needed |
| Smart splitting breaks cross-fragment context | Keep split threshold conservative (8 fragments); related parts share event_id prefix |
| Speaker normalization misidentifies someone | Only normalize the clearly-known main user aliases; leave ambiguous labels unchanged |
| Large number of GCF files (~900+) slows ingestion | Add progress tracking; can parallelize with `xargs` if needed |
| Ingestion fails partway through | `ingest-gcf` skips files already tracked in `data/gcf/.ingested` manifest |
