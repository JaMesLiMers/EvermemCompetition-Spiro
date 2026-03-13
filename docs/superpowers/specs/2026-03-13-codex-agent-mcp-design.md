# Codex Agent MCP Integration Design

**Date:** 2026-03-13
**Status:** Approved

## Overview

Integrate OpenAI Codex Python SDK with EverMemOS MCP server to build a reusable agent framework for memory analysis tasks. Codex acts as the AI agent, connecting to EverMemOS via MCP to search/retrieve memories, then performs analysis and outputs results to the terminal.

## Architecture

```
┌─────────────────────────────────────┐
│         codex_agent (Python)        │
│                                     │
│  ┌───────────┐   ┌───────────────┐  │
│  │ TaskRunner │   │  Task 定义层   │  │
│  │ (Codex SDK)│   │ (关系/画像/…) │  │
│  └─────┬─────┘   └───────┬───────┘  │
│        │                  │          │
│        ▼                  ▼          │
│  ┌─────────────────────────────────┐ │
│  │      AgentConfig                │ │
│  │  - UniAPI base_url / api_key    │ │
│  │  - model name                   │ │
│  │  - MCP server 配置              │ │
│  └─────────────┬───────────────────┘ │
└────────────────┼─────────────────────┘
                 │ MCP (stdio)
                 ▼
        ┌────────────────┐
        │ EverMemOS MCP  │
        │    Server       │
        └────────┬───────┘
                 │ HTTP
                 ▼
        ┌────────────────┐
        │   EverMemOS    │
        │  localhost:1995 │
        └────────────────┘
```

**Data flow:** User invokes a Task → TaskRunner starts Codex SDK agent with `developer_instructions` → Agent uses MCP tools (search_memory, get_memories, etc.) to retrieve relevant memories → Agent analyzes and outputs structured results to terminal.

## Module Structure

```
codex_agent/
├── __init__.py
├── config.py          # AgentConfig: UniAPI/model/MCP configuration
├── runner.py          # TaskRunner: Codex SDK wrapper
├── tasks/
│   ├── __init__.py
│   ├── base.py        # BaseTask abstract class
│   ├── relationships.py   # 人际关系梳理
│   ├── profiling.py       # 用户画像/性格分析
│   ├── timeline.py        # 事件时间线
│   └── suggestions.py     # 主动建议/提醒
└── cli.py             # CLI entry point
```

## Components

### AgentConfig (`config.py`)

Unified configuration read from environment variables. These env vars are forwarded to the Codex subprocess via `AppServerConfig.env`:

```bash
OPENAI_BASE_URL=https://your-uniapi.com/v1   # UniAPI endpoint (forwarded to Codex subprocess)
OPENAI_API_KEY=sk-xxx                          # UniAPI key (forwarded to Codex subprocess)
CODEX_MODEL=gpt-4o                             # Model name (configurable)
CODEX_BIN=/path/to/codex                       # Optional: explicit codex binary path
```

The config module reads these and constructs `AppServerConfig` with the `env` dict and optional `codex_bin` override.

### TaskRunner (`runner.py`)

Wraps the Codex Python SDK (`codex-app-server` package, importable as `codex_app_server`).

**SDK API mapping:**
- `AppServerClient` — synchronous JSON-RPC client over stdio
- `AppServerConfig` — configuration (codex_bin, env, config_overrides, cwd)
- `ThreadStartParams` — thread creation params (model, developer_instructions, approval_policy)
- `TurnStartParams` — turn input params

**Thread/turn lifecycle per task:**
1. Create `AppServerConfig` with `env={"OPENAI_BASE_URL": ..., "OPENAI_API_KEY": ...}` and optional `codex_bin`
2. Start `AppServerClient` as context manager
3. Call `thread_start(ThreadStartParams(model=..., developer_instructions=task.system_prompt))` — one thread per task
4. Call `turn_start(thread_id, task.build_prompt())` to submit the user prompt
5. Call `wait_for_turn_completed(turn_id)` to block until agent finishes (agent autonomously calls MCP tools during this phase)
6. Extract result text from `TurnCompletedNotification`
7. Client closes on context manager exit

**Approval policy:** Set `approval_policy` to auto-approve on `ThreadStartParams`, since the agent needs to call MCP tools autonomously without human approval gates.

**Error handling:**
- `AppServerError` / `JsonRpcError` — log and re-raise with context
- `TransportClosedError` — Codex process crashed, log stderr and raise
- Use `retry_on_overload` for rate limit / overload errors from the model provider

### BaseTask (`tasks/base.py`)

```python
from dataclasses import dataclass

@dataclass
class BaseTask:
    name: str                    # Task identifier
    system_prompt: str           # Maps to ThreadStartParams.developer_instructions
    user_prompt_template: str    # User prompt template with parameters
    user_id: str                 # Target user for memory search

    def build_prompt(self, **kwargs) -> str: ...
    def parse_output(self, raw: str) -> str: ...
```

`system_prompt` is passed as `developer_instructions` in `ThreadStartParams`, which sets the agent's system-level behavior for the entire thread.

### MCP Configuration

EverMemOS MCP server configured in `~/.codex/config.toml`:

```toml
[mcp_servers.evermemos]
command = "python"
args = ["-m", "mcp_server.server"]
```

The Codex binary reads this config file at startup and connects to configured MCP servers automatically. The Python SDK does not handle MCP configuration — it's managed by the underlying Codex process.

## Task Definitions

### 1. RelationshipsTask (人际关系梳理)

- **Search strategy:** Multi-round search_memory by person names, social keywords
- **Output:** Person list (name, role), relationship types (family/friend/colleague/...), key interactions
- **Parameters:** `user_id` (required), `focus_person` (optional)

### 2. ProfilingTask (用户画像/性格分析)

- **Search strategy:** Broad search across daily conversations, decisions, emotional expressions
- **Output:** Interests, personality traits, behavioral habits, values
- **Parameters:** `user_id` (required)

### 3. TimelineTask (事件时间线)

- **Search strategy:** Time-range search, keyword filtering
- **Output:** Chronologically sorted events with dates, participants, causal relationships
- **Parameters:** `user_id` (required), `start_date` / `end_date` (optional), `keywords` (optional)

### 4. SuggestionsTask (主动建议/提醒)

- **Search strategy:** Search for incomplete items, commitments, periodic events
- **Output:** Action items with suggested actions and priority
- **Parameters:** `user_id` (required)

## Dependencies

- `codex-app-server` — Codex Python SDK (from `codex/sdk/python/`, imports as `codex_app_server`)
- `codex-cli-bin` — Codex binary runtime (required by SDK to spawn the agent process). Alternative: set `CODEX_BIN` env var to an explicit binary path.
- `mcp_server/` — Existing EverMemOS MCP server (already built)
- UniAPI-compatible endpoint (OpenAI API format)

## Usage Example

```python
from codex_agent import AgentConfig, TaskRunner
from codex_agent.tasks import RelationshipsTask

config = AgentConfig.from_env()
runner = TaskRunner(config)

result = runner.run(RelationshipsTask(user_id="user_xxx"))
print(result)
```

Internally, `TaskRunner.run()` does:

```python
from codex_app_server import AppServerClient, AppServerConfig
from codex_app_server.generated.v2_all import ThreadStartParams

with AppServerClient(config=AppServerConfig(
    codex_bin=self.config.codex_bin,
    env={"OPENAI_BASE_URL": self.config.base_url, "OPENAI_API_KEY": self.config.api_key},
)) as client:
    thread = client.thread_start(ThreadStartParams(
        model=self.config.model,
        developer_instructions=task.system_prompt,
    ))
    turn = client.turn_start(thread.thread.id, task.build_prompt())
    completed = client.wait_for_turn_completed(turn.turn.id)
    # Extract agent's text output from completed notification
```
