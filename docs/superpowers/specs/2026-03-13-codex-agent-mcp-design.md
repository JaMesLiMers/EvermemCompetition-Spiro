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

**Data flow:** User invokes a Task → TaskRunner starts Codex SDK agent with system prompt → Agent uses MCP tools (search_memory, get_memories, etc.) to retrieve relevant memories → Agent analyzes and outputs structured results to terminal.

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

Unified configuration read from environment variables:

```bash
OPENAI_BASE_URL=https://your-uniapi.com/v1   # UniAPI endpoint
OPENAI_API_KEY=sk-xxx                          # UniAPI key
CODEX_MODEL=gpt-4o                             # Model name (configurable)
```

Codex SDK natively reads `OPENAI_BASE_URL` and `OPENAI_API_KEY`. The config module provides a typed wrapper with defaults and validation.

### TaskRunner (`runner.py`)

Wraps the Codex Python SDK (`codex-app-server-sdk`):

1. Starts Codex SDK client (reads UniAPI config from env)
2. Codex process connects to EverMemOS MCP server (configured in `~/.codex/config.toml`)
3. Sends task system prompt + user prompt to agent
4. Agent autonomously reasons, calls MCP tools, and produces analysis
5. Returns result text to caller

### BaseTask (`tasks/base.py`)

```python
class BaseTask:
    name: str                    # Task identifier
    system_prompt: str           # System prompt guiding agent behavior
    user_prompt_template: str    # User prompt template with parameters

    def build_prompt(self, **kwargs) -> str: ...
    def parse_output(self, raw: str) -> str: ...
```

### MCP Configuration

EverMemOS MCP server configured in `~/.codex/config.toml`:

```toml
[mcp_servers.evermemos]
command = "python"
args = ["-m", "mcp_server.server"]
```

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

- `codex-app-server-sdk` — Codex Python SDK (from `codex/sdk/python/`)
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
