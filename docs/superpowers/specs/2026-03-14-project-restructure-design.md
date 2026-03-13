# Project Restructure Design

**Date:** 2026-03-14
**Status:** Draft

## Problem

项目目录结构存在以下问题：

1. 命名不统一：`DataExtraction`(PascalCase) vs `codex_agent`(snake_case) vs `scripts`(lowercase)
2. `scripts/` 名称模糊，实际包含 API 客户端、数据导入、解析器、GCF 转换
3. `codex_agent/runner.py` 错误地绕过 Codex CLI 直接调用 OpenAI API，应通过 Codex CLI + MCP
4. `evermemos_api.py` 放在 `scripts/` 里，但 `mcp_server` 也依赖它，位置不合理
5. demo 数据和代码混在 `DataExtraction/` 里
6. `.env` 分散三处，根目录 `.env` 包含不再需要的变量

## Solution

按职能重组目录结构，重构 agent 模块改为调用 Codex CLI。

### Directory Structure (Before → After)

```
# BEFORE                           # AFTER
.                                   .
├── codex_agent/                    ├── agent/
│   ├── __init__.py                 │   ├── __init__.py      # remove TaskRunner export
│   ├── cli.py                      │   ├── cli.py           # refactored → calls Codex CLI
│   ├── config.py                   │   ├── config.py        # simplified
│   ├── runner.py        ❌ DELETE  │   ├── setup_mcp.py
│   ├── setup_mcp.py                │   └── tasks/           # unchanged
│   └── tasks/                      │
├── DataExtraction/                 ├── pipeline/
│   ├── .env                        │   ├── __init__.py
│   ├── .env.example                │   ├── extract_transcript.py
│   ├── extract_transcript.py       │   ├── transcript_parser.py
│   ├── demo_audio.mp3              │   ├── ingest_data.py
│   └── demo_output.json            │   ├── convert_to_gcf.py
│                                   │   ├── .env
├── Dataset/                        │   └── .env.example
│   ├── basic_events_*.json         │
│   └── README.md                   ├── shared/
│                                   │   ├── __init__.py
├── scripts/                        │   └── evermemos_api.py
│   ├── __init__.py                 │
│   ├── evermemos_api.py            ├── data/
│   ├── ingest_data.py              │   ├── basic_events_*.json
│   ├── transcript_parser.py        │   ├── README.md
│   ├── convert_to_gcf.py           │   ├── demo_audio.mp3
│   └── ingestion_progress.json     │   └── demo_output.json
│                                   │
├── mcp_server/          (不动)     ├── mcp_server/          (import 更新)
├── EverMemOS/           (不动)     ├── EverMemOS/           (不动)
├── codex/               (不动)     ├── codex/               (不动)
├── tests/                          ├── tests/               (import 更新 + 部分重写)
├── docs/                           ├── docs/
├── output/                         ├── output/
└── logs/                           └── logs/
```

**注意：** 使用 `shared/` 而非 `lib/`，因为 `.gitignore` 第 17 行已有 `lib/`（Python C extension 默认规则），会导致整个目录被 git 忽略。

### File Move/Delete Plan

所有移动操作使用 `git mv` 以保留文件历史。

#### Moves

| From | To |
|------|----|
| `codex_agent/*` | `agent/*` |
| `DataExtraction/extract_transcript.py` | `pipeline/extract_transcript.py` |
| `DataExtraction/.env` | `pipeline/.env` |
| `DataExtraction/.env.example` | `pipeline/.env.example` |
| `scripts/evermemos_api.py` | `shared/evermemos_api.py` |
| `scripts/ingest_data.py` | `pipeline/ingest_data.py` |
| `scripts/transcript_parser.py` | `pipeline/transcript_parser.py` |
| `scripts/convert_to_gcf.py` | `pipeline/convert_to_gcf.py` |
| `scripts/ingestion_progress.json` | `pipeline/ingestion_progress.json` |
| `Dataset/basic_events_79ef7f17.json` | `data/basic_events_79ef7f17.json` |
| `Dataset/README.md` | `data/README.md` |
| `DataExtraction/demo_audio.mp3` | `data/demo_audio.mp3` |
| `DataExtraction/demo_output.json` | `data/demo_output.json` |

#### Deletes

| File | Reason |
|------|--------|
| `agent/runner.py` | 错误实现，Codex CLI + MCP 替代 |
| `scripts/__init__.py` | 目录已清空，由 `pipeline/__init__.py` 和 `shared/__init__.py` 替代 |
| `DataExtraction/` | 内容全部移走 |
| `scripts/` | 内容全部移走 |
| `Dataset/` | 重命名为 data/ |

#### New Files

| File | Content |
|------|---------|
| `shared/__init__.py` | 空 |
| `pipeline/__init__.py` | 空 |

### Agent Refactor

#### `agent/__init__.py` (updated)

移除 `TaskRunner` 导出（runner.py 已删除）：

```python
from .config import AgentConfig

__all__ = ["AgentConfig"]
```

#### `agent/config.py` (simplified)

```python
import os
from dataclasses import dataclass


@dataclass
class AgentConfig:
    codex_bin: str
    model: str = "gpt-4o"
    evermemos_url: str = "http://localhost:1995"

    @classmethod
    def from_env(cls) -> "AgentConfig":
        codex_bin = os.environ.get("CODEX_BIN")
        if not codex_bin:
            raise ValueError("CODEX_BIN environment variable is required")
        return cls(
            codex_bin=codex_bin,
            model=os.environ.get("CODEX_MODEL", "gpt-4o"),
            evermemos_url=os.environ.get("EVERMEMOS_BASE_URL", "http://localhost:1995"),
        )
```

#### `agent/cli.py` (refactored)

关键变化：
1. 删除 `from .runner import TaskRunner`，改为调用 Codex CLI subprocess
2. **保留 `prefetch_memories()`** — 它预取记忆注入 prompt 上下文，不是 tool-calling，是合理的上下文准备
3. `prefetch_memories` 的 import 从 `scripts.evermemos_api` 改为 `shared.evermemos_api`
4. 硬编码路径 `Dataset/basic_events_79ef7f17.json` 改为 `data/basic_events_79ef7f17.json`

核心逻辑改为：

```python
import subprocess

def run_task(config: AgentConfig, task: BaseTask) -> str:
    prompt = task.build_prompt()
    result = subprocess.run(
        [config.codex_bin, "--model", config.model, "--prompt", prompt],
        capture_output=True, text=True
    )
    return result.stdout
```

具体的 Codex CLI 参数需要根据 codex 实际的命令行接口调整。

### Import Path Changes

| File | Old | New |
|------|-----|-----|
| `mcp_server/server.py` | `from scripts.evermemos_api import ...` | `from shared.evermemos_api import ...` |
| `pipeline/ingest_data.py` | `from scripts.evermemos_api import ...` | `from shared.evermemos_api import ...` |
| `pipeline/ingest_data.py` | `from scripts.transcript_parser import ...` | `from pipeline.transcript_parser import ...` |
| `pipeline/convert_to_gcf.py` | `from scripts.transcript_parser import ...` | `from pipeline.transcript_parser import ...` |
| `agent/cli.py` | `from scripts.evermemos_api import ...` | `from shared.evermemos_api import ...` |
| `agent/cli.py` | `from .runner import TaskRunner` | 删除 |
| `agent/cli.py` | `from codex_agent.* import ...` | `from agent.* import ...` |
| `agent/tasks/*.py` | `from codex_agent.* import ...` | `from agent.* import ...` |
| All tests | `from codex_agent.* import ...` | `from agent.* import ...` |
| All tests | `from scripts.* import ...` | `from pipeline.* / from shared.* import ...` |

### Hardcoded Path Changes

| File | Old | New |
|------|-----|-----|
| `agent/cli.py` | `"Dataset/basic_events_79ef7f17.json"` | `"data/basic_events_79ef7f17.json"` |
| `pipeline/ingest_data.py` | `Path("scripts/ingestion_progress.json")` | `Path("pipeline/ingestion_progress.json")` |

### Config File Updates

#### `pyproject.toml`

```toml
[project.scripts]
codex-agent = "agent.cli:main"

# packages: replace codex_agent with agent, scripts with pipeline + shared
```

#### `.gitignore`

```gitignore
# Old
Dataset/*
!Dataset/README.md
scripts/ingestion_progress.json

# New
data/*
!data/README.md
pipeline/ingestion_progress.json
```

注意：`.env` 已由通配规则 `.env`（第 138 行）覆盖，无需为 `pipeline/.env` 单独添加。

#### Root `.env` (simplified)

Remove `OPENAI_BASE_URL` and `OPENAI_API_KEY` (managed by Codex CLI itself).

Keep:
- `CODEX_BIN`
- `CODEX_MODEL`
- `EVERMEMOS_BASE_URL`

#### Root `.env.example` (updated to match)

#### Makefile

具体需要更新的 target 和路径：

| Target/Line | Old | New |
|-------------|-----|-----|
| `ingest-data` | `python -m scripts.ingest_data` | `python -m pipeline.ingest_data` |
| `convert-gcf` | `python -m scripts.convert_to_gcf` | `python -m pipeline.convert_to_gcf` |
| `run-task` | `python -m codex_agent.cli` | `python -m agent.cli` |
| `clean` | `scripts/ingestion_progress.json` | `pipeline/ingestion_progress.json` |
| `init-env` | `DataExtraction/.env` template | `pipeline/.env` template |

### .env Management

| File | Service | Key Variables |
|------|---------|---------------|
| `.env` | Codex Agent (root) | `CODEX_BIN`, `CODEX_MODEL`, `EVERMEMOS_BASE_URL` |
| `pipeline/.env` | Data extraction | `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_BASE_URL` etc. |
| `EverMemOS/.env` | Backend services | MongoDB, Redis, ES, Milvus, LLM etc. |

### Test Updates

| Test File | Change |
|-----------|--------|
| `test_runner.py` | **删除** — runner.py 已删除，且测试本身已过期（引用不存在的 AppServerClient 等） |
| `test_cli.py` | **重写** — 原来 mock `TaskRunner`，现在需要 mock `subprocess.run`（Codex CLI 调用） |
| `test_config.py` | **重写** — 新 `AgentConfig` 用 `CODEX_BIN` 替代 `OPENAI_BASE_URL`/`OPENAI_API_KEY` |
| `test_transcript_parser.py` | import 路径更新：`from scripts.` → `from pipeline.` |
| `test_convert_to_gcf.py` | import 路径更新：`from scripts.` → `from pipeline.` |
| 其他 task 相关测试 | import 路径更新：`from codex_agent.` → `from agent.` |

### What Stays Unchanged

- `EverMemOS/` — submodule, not touched
- `codex/` — submodule, not touched
- `mcp_server/server.py` — only import path updated (`scripts` → `shared`)
- `agent/tasks/` — prompt templates unchanged
- `agent/setup_mcp.py` — logic unchanged
- `EverMemOS/.env` — submodule internal
- `agent/cli.py:prefetch_memories()` — 保留，改 import 路径即可
