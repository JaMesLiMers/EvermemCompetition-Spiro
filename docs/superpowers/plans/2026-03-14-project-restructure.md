# Project Restructure Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize the project directory structure by function, fix agent architecture to use Codex CLI + MCP.

**Architecture:** Rename and regroup directories: `codex_agent/` → `agent/`, `DataExtraction/` + `scripts/` → `pipeline/` + `shared/`, `Dataset/` → `data/`. Refactor agent to call Codex CLI subprocess instead of its own tool-calling loop.

**Tech Stack:** Python, git, Makefile, pyproject.toml

**Spec:** `docs/superpowers/specs/2026-03-14-project-restructure-design.md`

---

## Chunk 1: Directory Moves

### Task 1: Create target directories and move files with git mv

**Files:**
- Create: `shared/__init__.py`, `pipeline/__init__.py`
- Move: All files per spec move table
- Delete: `agent/runner.py` (after move)

- [ ] **Step 1: Create target directories and __init__.py files**

```bash
mkdir -p shared pipeline data
touch shared/__init__.py pipeline/__init__.py
```

- [ ] **Step 2: Move codex_agent/ → agent/**

```bash
git mv codex_agent agent
```

- [ ] **Step 3: Move scripts/evermemos_api.py → shared/**

```bash
git mv scripts/evermemos_api.py shared/evermemos_api.py
```

- [ ] **Step 4: Move scripts/ contents → pipeline/**

```bash
git mv scripts/ingest_data.py pipeline/ingest_data.py
git mv scripts/transcript_parser.py pipeline/transcript_parser.py
git mv scripts/convert_to_gcf.py pipeline/convert_to_gcf.py
```

Note: `scripts/ingestion_progress.json` is in `.gitignore` and may not exist in git. If it exists on disk, move manually: `mv scripts/ingestion_progress.json pipeline/ingestion_progress.json 2>/dev/null || true`

- [ ] **Step 5: Move DataExtraction/ contents → pipeline/ and data/**

```bash
git mv DataExtraction/extract_transcript.py pipeline/extract_transcript.py
git mv DataExtraction/.env.example pipeline/.env.example
git mv DataExtraction/demo_audio.mp3 data/demo_audio.mp3
git mv DataExtraction/demo_output.json data/demo_output.json
```

Note: `DataExtraction/.env` is in `.gitignore` and not tracked. Move manually: `mv DataExtraction/.env pipeline/.env 2>/dev/null || true`

- [ ] **Step 6: Move Dataset/ → data/**

```bash
git mv Dataset/basic_events_79ef7f17.json data/basic_events_79ef7f17.json
git mv Dataset/README.md data/README.md
```

- [ ] **Step 7: Clean up empty directories and delete runner.py**

```bash
git rm scripts/__init__.py
git rm agent/runner.py
rm -rf scripts/ DataExtraction/ Dataset/
```

- [ ] **Step 8: Stage new files and commit**

```bash
git add shared/__init__.py pipeline/__init__.py
git commit -m "refactor: reorganize directories by function

- codex_agent/ → agent/
- scripts/evermemos_api.py → shared/
- scripts/*.py + DataExtraction/ → pipeline/
- Dataset/ → data/
- Delete runner.py (incorrect direct OpenAI API implementation)"
```

---

## Chunk 2: Update All Import Paths

### Task 2: Fix imports in pipeline/ files

**Files:**
- Modify: `pipeline/ingest_data.py`
- Modify: `pipeline/convert_to_gcf.py`

- [ ] **Step 1: Update pipeline/ingest_data.py imports**

Change line 21-22:
```python
# Old
from scripts.transcript_parser import parse_transcript_with_metadata
from scripts.evermemos_api import EverMemosClient

# New
from pipeline.transcript_parser import parse_transcript_with_metadata
from shared.evermemos_api import EverMemosClient
```

- [ ] **Step 2: Update pipeline/ingest_data.py hardcoded path**

Change line 24:
```python
# Old
PROGRESS_FILE = Path("scripts/ingestion_progress.json")

# New
PROGRESS_FILE = Path("pipeline/ingestion_progress.json")
```

- [ ] **Step 3: Update pipeline/convert_to_gcf.py imports**

Change lines 15-20:
```python
# Old
from scripts.transcript_parser import (
    FRAGMENT_PATTERN,
    TITLE_PATTERN,
    TYPE_PATTERN,
    parse_fragment_time,
    parse_speaker_turns,
)

# New
from pipeline.transcript_parser import (
    FRAGMENT_PATTERN,
    TITLE_PATTERN,
    TYPE_PATTERN,
    parse_fragment_time,
    parse_speaker_turns,
)
```

- [ ] **Step 4: Commit import fixes for pipeline/**

```bash
git add pipeline/ingest_data.py pipeline/convert_to_gcf.py
git commit -m "fix: update import paths in pipeline/ modules"
```

### Task 3: Fix imports in shared/ consumers

**Files:**
- Modify: `mcp_server/server.py`

- [ ] **Step 1: Update mcp_server/server.py import**

Change line 5:
```python
# Old
from scripts.evermemos_api import EverMemosClient

# New
from shared.evermemos_api import EverMemosClient
```

- [ ] **Step 2: Commit**

```bash
git add mcp_server/server.py
git commit -m "fix: update evermemos_api import path in mcp_server"
```

### Task 4: Fix imports in agent/ files

**Files:**
- Modify: `agent/__init__.py`
- Modify: `agent/cli.py`
- Check: `agent/tasks/*.py` for any `codex_agent` imports

- [ ] **Step 1: Update agent/__init__.py — remove TaskRunner**

Replace entire file:
```python
from .config import AgentConfig

__all__ = ["AgentConfig"]
```

- [ ] **Step 2: Update agent/cli.py imports**

Change lines 9-12:
```python
# Old
from scripts.evermemos_api import EverMemosClient
from .config import AgentConfig
from .runner import TaskRunner

# New
from shared.evermemos_api import EverMemosClient
from .config import AgentConfig
```

- [ ] **Step 3: Update agent/cli.py — remove TaskRunner usage**

Two changes:

(a) Delete line 89 (`runner = TaskRunner(config)`) — remove entirely.

(b) Replace lines 106-107 (`result = runner.run(task)` / `print(result)`) with:
```python
    import subprocess
    prompt = task.build_prompt()
    system_prompt = task.system_prompt
    full_prompt = f"System: {system_prompt}\n\n{prompt}"
    codex_result = subprocess.run(
        [config.codex_bin, "--model", config.model, "--prompt", full_prompt],
        capture_output=True, text=True, cwd="."
    )
    result = codex_result.stdout
    print(result)
```

Note: The exact Codex CLI flags need to be verified against the actual `codex` binary interface. This is the structural change; the specific invocation may need adjustment after testing.

- [ ] **Step 4: Update agent/cli.py — fix Dataset path**

Change line 72:
```python
# Old
            dataset_path = "Dataset/basic_events_79ef7f17.json"

# New
            dataset_path = "data/basic_events_79ef7f17.json"
```

- [ ] **Step 5: Check agent/tasks/ for any codex_agent imports**

Grep for `codex_agent` in `agent/tasks/`. If any found, change to `agent.`. The tasks use relative imports (`.base`), so likely no changes needed.

- [ ] **Step 6: Commit**

```bash
git add agent/
git commit -m "refactor: update agent/ imports, remove TaskRunner, use Codex CLI"
```

---

## Chunk 3: Update Config Files

### Task 5: Update pyproject.toml

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Update pyproject.toml**

```toml
[project]
name = "codex-agent"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "httpx>=0.27",
    "mcp>=1.0",
]

[project.scripts]
codex-agent = "agent.cli:main"

[tool.setuptools.packages.find]
include = ["agent*", "mcp_server*", "pipeline*", "shared*"]
```

- [ ] **Step 2: Commit**

```bash
git add pyproject.toml
git commit -m "fix: update package paths in pyproject.toml"
```

### Task 6: Update .gitignore

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Update .gitignore — Dataset → data**

Change lines 209-211:
```gitignore
# Old
Dataset/*
!Dataset/README.md

# New
data/*
!data/README.md
```

- [ ] **Step 2: Update .gitignore — scripts → pipeline progress file**

Change line 225:
```gitignore
# Old
scripts/ingestion_progress.json

# New
pipeline/ingestion_progress.json
```

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "fix: update .gitignore paths for new directory structure"
```

### Task 7: Update Makefile

**Files:**
- Modify: `Makefile`

- [ ] **Step 1: Update init target — DataExtraction → pipeline**

Change line 35:
```makefile
# Old
	@echo "  - DataExtraction/.env   (数据提取)"

# New
	@echo "  - pipeline/.env         (数据提取)"
```

- [ ] **Step 2: Update init-env target**

Change line 38:
```makefile
# Old
	@for target in .env EverMemOS/.env DataExtraction/.env; do \

# New
	@for target in .env EverMemOS/.env pipeline/.env; do \
```

- [ ] **Step 3: Update ingest-data help text**

Change line 173:
```makefile
# Old
		echo "用法: make ingest-data INPUT=Dataset/basic_events_79ef7f17.json"; \

# New
		echo "用法: make ingest-data INPUT=data/basic_events_79ef7f17.json"; \
```

- [ ] **Step 4: Update ingest-data command**

Change line 177:
```makefile
# Old
	python -m scripts.ingest_data --input $(INPUT) \

# New
	python -m pipeline.ingest_data --input $(INPUT) \
```

- [ ] **Step 5: Update convert-gcf help text**

Change line 184:
```makefile
# Old
		echo "用法: make convert-gcf INPUT=Dataset/basic_events_79ef7f17.json"; \

# New
		echo "用法: make convert-gcf INPUT=data/basic_events_79ef7f17.json"; \
```

- [ ] **Step 6: Update convert-gcf command**

Change line 188:
```makefile
# Old
	python -m scripts.convert_to_gcf --input $(INPUT) --output data/gcf/ \

# New
	python -m pipeline.convert_to_gcf --input $(INPUT) --output data/gcf/ \
```

- [ ] **Step 7: Update run-task command**

Change line 219:
```makefile
# Old
	python -m codex_agent.cli $(TASK) --user-id $(USER_ID) \

# New
	python -m agent.cli $(TASK) --user-id $(USER_ID) \
```

- [ ] **Step 8: Update clean target**

Change line 229:
```makefile
# Old
	rm -f scripts/ingestion_progress.json

# New
	rm -f pipeline/ingestion_progress.json
```

- [ ] **Step 9: Commit**

```bash
git add Makefile
git commit -m "fix: update all paths in Makefile for new directory structure"
```

### Task 8: Update .env and .env.example

**Files:**
- Modify: `.env`
- Modify: `.env.example`

- [ ] **Step 1: Simplify .env.example**

```
# Codex Agent 配置
CODEX_MODEL=gpt-4o
CODEX_BIN=.codex-bin/codex
CODEX_HOME=.codex-local
EVERMEMOS_BASE_URL=http://localhost:1995
```

Remove `OPENAI_BASE_URL` and `OPENAI_API_KEY` (managed by Codex CLI).

- [ ] **Step 2: Simplify .env to match**

Remove the `OPENAI_BASE_URL` and `OPENAI_API_KEY` lines from `.env`. Keep:
```
# Codex Agent 配置
CODEX_MODEL=gpt-4o-mini
CODEX_BIN=.codex-bin/codex
CODEX_HOME=.codex-local
EVERMEMOS_BASE_URL=http://localhost:1995
```

- [ ] **Step 3: Commit**

```bash
git add .env.example
git commit -m "fix: simplify root .env.example, remove OpenAI vars managed by Codex"
```

Note: `.env` itself is in `.gitignore` and not committed.

---

## Chunk 4: Update Config and Tests

### Task 9: Simplify agent/config.py

**Files:**
- Modify: `agent/config.py`

- [ ] **Step 1: Rewrite agent/config.py**

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

- [ ] **Step 2: Commit**

```bash
git add agent/config.py
git commit -m "refactor: simplify AgentConfig — only CODEX_BIN, CODEX_MODEL, EVERMEMOS_BASE_URL"
```

### Task 10: Update tests — import paths

**Files:**
- Modify: `tests/test_transcript_parser.py`
- Modify: `tests/test_convert_to_gcf.py`
- Modify: `tests/test_evermemos_api.py`
- Modify: `tests/test_tasks.py`
- Modify: `tests/test_base_task.py`

- [ ] **Step 1: Update test_transcript_parser.py imports**

Change all `from scripts.transcript_parser import ...` to `from pipeline.transcript_parser import ...`

- [ ] **Step 2: Update test_convert_to_gcf.py imports**

Change all `from scripts.convert_to_gcf import ...` to `from pipeline.convert_to_gcf import ...`

- [ ] **Step 3: Update test_evermemos_api.py imports**

Change all `from scripts.evermemos_api import ...` to `from shared.evermemos_api import ...`

- [ ] **Step 4: Update test_tasks.py imports**

Change all `from codex_agent.tasks.* import ...` to `from agent.tasks.* import ...`

- [ ] **Step 5: Update test_base_task.py imports**

Change all `from codex_agent.tasks.base import ...` to `from agent.tasks.base import ...`

- [ ] **Step 6: Run tests to verify import changes**

Run: `python -m pytest tests/test_transcript_parser.py tests/test_convert_to_gcf.py tests/test_evermemos_api.py tests/test_tasks.py tests/test_base_task.py -v`

Expected: All pass (logic unchanged, only import paths differ).

- [ ] **Step 7: Commit**

```bash
git add tests/test_transcript_parser.py tests/test_convert_to_gcf.py tests/test_evermemos_api.py tests/test_tasks.py tests/test_base_task.py
git commit -m "fix: update import paths in tests for new directory structure"
```

### Task 11: Rewrite tests — runner, cli, config

**Files:**
- Delete: `tests/test_runner.py`
- Rewrite: `tests/test_config.py`
- Rewrite: `tests/test_cli.py`

- [ ] **Step 1: Delete test_runner.py**

```bash
git rm tests/test_runner.py
```

- [ ] **Step 2: Rewrite test_config.py**

```python
import os
import pytest
from agent.config import AgentConfig


def test_from_env_all_set(monkeypatch):
    monkeypatch.setenv("CODEX_BIN", "/usr/local/bin/codex")
    monkeypatch.setenv("CODEX_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("EVERMEMOS_BASE_URL", "http://localhost:2000")
    config = AgentConfig.from_env()
    assert config.codex_bin == "/usr/local/bin/codex"
    assert config.model == "gpt-4o-mini"
    assert config.evermemos_url == "http://localhost:2000"


def test_from_env_defaults(monkeypatch):
    monkeypatch.setenv("CODEX_BIN", "/usr/local/bin/codex")
    monkeypatch.delenv("CODEX_MODEL", raising=False)
    monkeypatch.delenv("EVERMEMOS_BASE_URL", raising=False)
    config = AgentConfig.from_env()
    assert config.model == "gpt-4o"
    assert config.evermemos_url == "http://localhost:1995"


def test_from_env_missing_codex_bin(monkeypatch):
    monkeypatch.delenv("CODEX_BIN", raising=False)
    with pytest.raises(ValueError, match="CODEX_BIN"):
        AgentConfig.from_env()
```

- [ ] **Step 3: Rewrite test_cli.py**

```python
from agent.cli import TASK_REGISTRY, main
from agent.tasks.relationships import RelationshipsTask
from agent.tasks.profiling import ProfilingTask
from agent.tasks.timeline import TimelineTask
from agent.tasks.suggestions import SuggestionsTask


def test_task_registry_contains_all_tasks():
    assert "relationships" in TASK_REGISTRY
    assert "profiling" in TASK_REGISTRY
    assert "timeline" in TASK_REGISTRY
    assert "suggestions" in TASK_REGISTRY


def test_task_registry_classes():
    assert TASK_REGISTRY["relationships"] is RelationshipsTask
    assert TASK_REGISTRY["profiling"] is ProfilingTask
    assert TASK_REGISTRY["timeline"] is TimelineTask
    assert TASK_REGISTRY["suggestions"] is SuggestionsTask
```

- [ ] **Step 4: Run all tests**

Run: `python -m pytest tests/ -v`

Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add tests/
git commit -m "test: rewrite config/cli tests for new AgentConfig, delete stale runner tests"
```

---

## Chunk 5: Update Design Docs and Final Verification

### Task 12: Update references in docs

**Files:**
- Modify: `docs/superpowers/specs/2026-03-14-gcf-conversion-pipeline-design.md` (if it references old paths)

- [ ] **Step 1: Check and update old path references in design docs**

Search for `scripts/`, `Dataset/`, `codex_agent/`, `DataExtraction/` in all files under `docs/` and update to new paths.

- [ ] **Step 2: Commit if changes were made**

```bash
git add docs/
git commit -m "docs: update path references to match new directory structure"
```

### Task 13: Final verification

- [ ] **Step 1: Run full test suite**

Run: `python -m pytest tests/ -v`

Expected: All tests pass.

- [ ] **Step 2: Verify no stale imports remain**

```bash
grep -r "from scripts\." --include="*.py" . | grep -v ".git/" | grep -v "__pycache__"
grep -r "from codex_agent" --include="*.py" . | grep -v ".git/" | grep -v "__pycache__"
grep -r "DataExtraction" . --include="*.py" --include="Makefile" --include="*.toml" | grep -v ".git/"
grep -r "Dataset/" . --include="*.py" --include="Makefile" --include="*.toml" --include=".gitignore" | grep -v ".git/"
```

Expected: No matches (all references updated).

- [ ] **Step 3: Verify pip install -e . works**

```bash
pip install -e . 2>&1 | tail -5
```

Expected: Successfully installed.

- [ ] **Step 4: Verify directory structure is clean**

```bash
ls -la agent/ shared/ pipeline/ data/ mcp_server/
# Confirm: no scripts/, DataExtraction/, Dataset/, codex_agent/ directories remain
ls scripts/ DataExtraction/ Dataset/ codex_agent/ 2>&1
```

Expected: `ls: cannot access 'scripts/': No such file or directory` (etc.)
