# Data

## Overview

Dataset for the [EverMemOS competition](https://github.com/EverMemOS) — **832 real conversation events** captured by the Spiro wearable band. All transcripts have been speaker-normalized and converted to structured formats for downstream analysis.

## Files

| File | Description | Size |
|------|-------------|------|
| `basic_events_79ef7f17.json` | Raw dataset with embedded speaker mappings | 13 MB, 832 events |
| `gcf_all.json` | Merged GroupChatFormat output (72 conversations, 15K messages) | 5.2 MB |
| `last100_events.json` | Subset of recent events for quick testing | 1.4 MB |
| `demo_audio.mp3` | Audio sample from the Spiro wearable | 6.5 MB |
| `demo_output.json` | Sample analysis output | 1.7 KB |

## Data Format

### Event Structure

Each event in `basic_events_79ef7f17.json` is a JSON object with two top-level keys:

```json
{
  "meta": {
    "user_id":          "User ID (UUID)",
    "basic_event_id":   "Event ID (UUID)",
    "basic_start_time": "Start time (Unix epoch seconds)",
    "basic_end_time":   "End time (Unix epoch seconds)"
  },
  "object": {
    "basic_transcript": "Normalized transcript text"
  }
}
```

#### `meta` Fields

| Field | Type | Description |
|-------|------|-------------|
| `user_id` | string | User unique identifier (UUID) |
| `basic_event_id` | string | Event unique identifier (UUID) |
| `basic_start_time` | number | Event start time, Unix epoch seconds |
| `basic_end_time` | number | Event end time, Unix epoch seconds |

#### `object` Fields

| Field | Type | Description |
|-------|------|-------------|
| `basic_transcript` | string | Speaker-normalized transcript (see format below) |

### Fragment Structure

Transcripts are organized into fragments, each representing a contiguous segment of conversation:

```
[Fragment N: YYYY-MM-DD HH:MM - YYYY-MM-DD HH:MM]
Title: Conversation title
Type: career, social, home, ...

[Speaker1]: Utterance text
[User]: Utterance text
[Colleague/Friend]: Utterance text
```

### Speaker Label Normalization

Speaker labels are normalized by `scripts/normalize_speakers.py` into the following categories:

| Label Type | Format | Description |
|------------|--------|-------------|
| Primary user | `[User]` | The person wearing the recording device |
| Generic speaker | `[Speaker1]`, `[Speaker2]`, ... | Numbered by order of appearance; numbering resets per event |
| Generic + gender | `[Speaker1/M]`, `[Speaker2/F]` | With gender annotation |
| Named role | `[Colleague/Friend]`, `[Partner]`, `[Interviewer]`, etc. | Original role description preserved |

### Dialogue Line Format

All dialogue lines follow a consistent format (no timestamps):

```
[Speaker Label]: Utterance content
```

### Non-Dialogue Lines

Transcripts may contain the following non-dialogue lines, which are automatically skipped during pipeline parsing:

- **Fragment header:** `[Fragment N: ...]`
- **Title / Type:** `Title: ...` / `Type: ...`
- **Metadata:** `[Full Transcript and Summary]`, etc.
- **Environment notes:** `[Quiet environment] [Clear audio]`, etc.
- **Passive media:** `Passive media, transcript content omitted`

## Pipeline Flow

```
Spiro Wearable Band
    │
    ▼
basic_events_79ef7f17.json   ← 832 raw events with speaker mappings
    │
    ├─► normalize_speakers.py ← Standardize speaker labels
    │
    ▼
gcf_all.json                 ← Merged GroupChatFormat for EverMemOS
    │
    ▼
EverMemOS API (localhost:1995)
```

1. **Capture:** The Spiro band records conversations and produces raw event transcripts.
2. **Normalize:** `scripts/normalize_speakers.py` standardizes all speaker labels into a consistent format.
3. **Convert:** The pipeline converts normalized events into GroupChatFormat (`gcf_all.json`), which merges related fragments into conversations.
4. **Ingest:** GCF data is posted to the EverMemOS API for memory storage and retrieval.
