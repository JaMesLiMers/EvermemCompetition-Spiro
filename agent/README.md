# Spiro Agent — Memory Analysis System

## Overview

The Spiro agent is an AI-powered analysis system that extracts structured insights from episodic memories stored in [EverMemOS](https://github.com/anthropics/evermemos). It uses **Claude Sonnet 4.6** (via the [opencode](https://opencode.ai) CLI) to run five specialized analysis tasks — relationship mapping, life-topic profiling, event timelines, personal insights, and event cards — each producing strict JSON output ready for downstream rendering.

The agent is designed as the intelligence layer for a context-native empathic AI wearable (Spiro band). It reads raw conversation memories, reasons over them, and produces structured data that powers the companion app's UI.

## How It Works

Every task execution follows a four-step pipeline:

```
1. Prefetch          2. Build Prompt        3. Execute            4. Parse
───────────────      ───────────────        ───────────────       ───────────────
EverMemOS API   →    Task-specific     →    opencode CLI     →    Extract JSON
episodic memories    system + user          (MCP-enabled,         from raw output,
(up to 100 per       prompt with            Claude Sonnet 4.6)    wrap in metadata
group, 50KB cap)     injected context                             envelope, save
```

### Step 1 — Prefetch Episodic Memories

The CLI fetches episodic memories from the EverMemOS API for each group. Groups are either specified via `--group-id` or auto-detected from `data/gcf_all.json`. Memories are fetched with a limit of 100 per group and a total context cap of 50,000 characters across all groups. Each memory's title, summary, participants, and key events are formatted into a context string.

### Step 2 — Build Task-Specific Prompt

Each task defines a `system_prompt` (role + output schema) and a `user_prompt_template` (parameterized instruction). The `BaseTask.build_prompt()` method renders the user template with the target `user_id` and any task-specific parameters, then appends the prefetched memory context below a separator line.

The final prompt sent to the model is: `System: {system_prompt}\n\n{rendered_user_prompt + prefetched_context}`.

### Step 3 — Execute via opencode CLI

The combined prompt is written to a temporary file (to avoid shell argument-length limits) and piped into opencode:

```bash
cat /tmp/prompt.txt | opencode run --model anthropic/claude-sonnet-4-6
```

opencode is configured with an MCP server (`opencode.json`) that exposes EverMemOS tools (`search_memory`, `get_memories`) so the model can perform supplementary memory searches beyond the prefetched context if needed.

### Step 4 — Parse JSON Output

The `_extract_json()` function strips markdown fences or surrounding text from the model's raw output and validates it as JSON. The parsed result is printed to stdout and (unless `--no-save`) wrapped in a metadata envelope and saved to `output/`.

## Task Types

| Task | Description | Key Output Fields |
|------|-------------|-------------------|
| **relationships** | Maps the interpersonal relationship network around a target user. Identifies all people mentioned, their relationship to the user, and key personality traits. Optionally focuses on one specific person. | `people[]` — each with `id` (snake_case), `name`, `relationship`, `key_traits[]` |
| **profiling** | Extracts 5-8 dominant life topics/themes from conversation history. Each topic gets a gravity score (0-100), a poetic description, an emoji icon, and a color category. | `life_topics[]` — each with `id`, `name`, `gravity`, `description`, `icon`, `color` (one of: blue, purple, emerald, amber) |
| **timeline** | Builds a chronological event timeline with causal analysis. Supports date-range filtering and keyword focus. | `timeline[]` — each with `date`, `event`, `participants[]`, `notes`; plus `causal_analysis[]` with `cause_event`, `effect_event`, `explanation` |
| **suggestions** | Generates actionable personal insights grouped by person — promises, needs, personality observations, upcoming events, birthdays. | `insights_by_person{}` — keyed by person name, each value is an array of `{id, text, type}` where type is one of: birthday, event, personality, promise, need |
| **event_cards** | Transforms memories into readable diary-style event cards, ordered chronologically. Each card has a title, narrative content, participants, tags, and sentiment. | `diaries[]` — each with `id`, `title`, `date`, `content`, `peopleIds[]` (snake_case), `tags[]`, `sentiment` (positive/neutral/negative) |

## Usage

All tasks are run through `make run-task`. The underlying command is `python -m agent.cli`.

### Parameters

| Parameter | Flag | Required | Used By | Description |
|-----------|------|----------|---------|-------------|
| `TASK` | positional | Yes | all | Task name: `relationships`, `profiling`, `timeline`, `suggestions`, `event_cards` |
| `USER_ID` | `--user-id` | Yes | all | Target user/participant name to analyze |
| `FOCUS_PERSON` | `--focus-person` | No | relationships | Narrow the relationship analysis to one specific person |
| `START_DATE` | `--start-date` | No | timeline | Start date filter (YYYY-MM-DD) |
| `END_DATE` | `--end-date` | No | timeline | End date filter (YYYY-MM-DD) |
| `KEYWORDS` | `--keywords` | No | timeline | Space-separated keyword filters for event relevance |

### Examples

```bash
# Map all relationships for a user
make run-task TASK=relationships USER_ID=Alice

# Focus on one relationship
make run-task TASK=relationships USER_ID=Alice FOCUS_PERSON=Bob

# Extract life topics
make run-task TASK=profiling USER_ID=Alice

# Build a filtered timeline
make run-task TASK=timeline USER_ID=Alice START_DATE=2026-01-01 END_DATE=2026-03-15 KEYWORDS="work project"

# Generate personal insights
make run-task TASK=suggestions USER_ID=Alice

# Generate event cards for the companion app
make run-task TASK=event_cards USER_ID=Alice
```

### Direct CLI Usage

```bash
python -m agent.cli relationships --user-id Alice --focus-person Bob
python -m agent.cli timeline --user-id Alice --start-date 2026-01-01 --keywords work project
python -m agent.cli event_cards --user-id Alice --no-save
```

## Output Format

Every saved result is wrapped in a JSON metadata envelope and written to `output/<task>_<timestamp>.json`. A JSONL manifest (`output/manifest.jsonl`) is appended for experiment tracking.

### Envelope Structure

```json
{
  "metadata": {
    "task": "relationships",
    "model": "anthropic/claude-sonnet-4-6",
    "user_id": "Alice",
    "group_id": "grp_abc123",
    "timestamp": "2026-03-15T14:30:00.000000",
    "duration_seconds": 12.3,
    "prefetched_memories": 42
  },
  "result": {
    "people": [
      {
        "id": "bob",
        "name": "Bob",
        "relationship": "Husband",
        "key_traits": ["supportive", "pragmatic", "tech-savvy"]
      }
    ]
  }
}
```

The `metadata` block always contains:

| Field | Type | Description |
|-------|------|-------------|
| `task` | string | Task name that produced this result |
| `model` | string | Model identifier (default: `anthropic/claude-sonnet-4-6`) |
| `user_id` | string | Target user analyzed |
| `group_id` | string or null | EverMemOS group ID (first group if multiple) |
| `timestamp` | string | ISO 8601 timestamp of execution |
| `duration_seconds` | number | Wall-clock execution time |
| `prefetched_memories` | integer | Number of episodic memories loaded as context |

When task-specific parameters are provided, they are included in the metadata as well (`focus_person`, `start_date`, `end_date`, `keywords`).

The `result` field contains the task-specific JSON output as described in the Task Types table above.

## Configuration

The agent reads configuration from environment variables (with `.env` file support):

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_BIN` | auto-detect `opencode` on PATH | Path to the opencode CLI binary |
| `AGENT_MODEL` | `anthropic/claude-sonnet-4-6` | Model identifier passed to opencode |
| `EVERMEMOS_BASE_URL` | `http://localhost:1995` | EverMemOS API base URL |

The opencode MCP configuration (`opencode.json` at project root) must include the EverMemOS MCP server:

```json
{
  "mcp": {
    "evermemos": {
      "type": "local",
      "command": ["python", "-m", "mcp_server.server"]
    }
  }
}
```
