# Codex Agent MCP Integration Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable Python framework that uses Codex Python SDK to run AI agents that analyze EverMemOS memories via MCP.

**Architecture:** `codex_agent` Python package wraps `codex_app_server` SDK. `TaskRunner` manages the Codex thread/turn lifecycle. Each analysis task (relationships, profiling, timeline, suggestions) is a `BaseTask` subclass with task-specific prompts. Codex agent autonomously calls EverMemOS MCP tools during execution.

**Tech Stack:** Python 3.10+, `codex-app-server` SDK, `codex_app_server.generated.v2_all` types, EverMemOS MCP server (existing)

**Spec:** `docs/superpowers/specs/2026-03-13-codex-agent-mcp-design.md`

---

## Chunk 1: Core Framework (config, runner, base task)

### Task 0: Project Setup

**Files:**
- Create: `pyproject.toml` (add `codex_agent` as a package)

- [ ] **Step 1: Create pyproject.toml for the codex_agent package**

```toml
# pyproject.toml (append or create)
[project]
name = "codex-agent"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "codex-app-server",
]

[tool.setuptools.packages.find]
include = ["codex_agent*"]
```

- [ ] **Step 2: Install in editable mode**

Run: `pip install -e .`
Expected: Successfully installed codex-agent

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add pyproject.toml for codex_agent package"
```

---

### Task 1: AgentConfig

**Files:**
- Create: `codex_agent/__init__.py`
- Create: `codex_agent/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test for AgentConfig**

```python
# tests/test_config.py
import os
import pytest
from unittest.mock import patch


def test_from_env_reads_all_vars():
    env = {
        "OPENAI_BASE_URL": "https://uniapi.example.com/v1",
        "OPENAI_API_KEY": "sk-test-key",
        "CODEX_MODEL": "gpt-4o",
        "CODEX_BIN": "/usr/local/bin/codex",
    }
    with patch.dict(os.environ, env, clear=False):
        from codex_agent.config import AgentConfig
        config = AgentConfig.from_env()
        assert config.base_url == "https://uniapi.example.com/v1"
        assert config.api_key == "sk-test-key"
        assert config.model == "gpt-4o"
        assert config.codex_bin == "/usr/local/bin/codex"


def test_from_env_defaults():
    env = {
        "OPENAI_BASE_URL": "https://uniapi.example.com/v1",
        "OPENAI_API_KEY": "sk-test-key",
    }
    with patch.dict(os.environ, env, clear=True):
        from codex_agent.config import AgentConfig
        config = AgentConfig.from_env()
        assert config.model == "gpt-4o"  # default
        assert config.codex_bin is None


def test_from_env_missing_required():
    with patch.dict(os.environ, {}, clear=True):
        from codex_agent.config import AgentConfig
        with pytest.raises(ValueError, match="OPENAI_BASE_URL"):
            AgentConfig.from_env()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — module `codex_agent.config` does not exist

- [ ] **Step 3: Write AgentConfig implementation**

```python
# codex_agent/__init__.py
from .config import AgentConfig

__all__ = ["AgentConfig"]
```

```python
# codex_agent/config.py
import os
from dataclasses import dataclass


@dataclass
class AgentConfig:
    base_url: str
    api_key: str
    model: str = "gpt-4o"
    codex_bin: str | None = None

    @classmethod
    def from_env(cls) -> "AgentConfig":
        base_url = os.environ.get("OPENAI_BASE_URL")
        if not base_url:
            raise ValueError("OPENAI_BASE_URL environment variable is required")
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        return cls(
            base_url=base_url,
            api_key=api_key,
            model=os.environ.get("CODEX_MODEL", "gpt-4o"),
            codex_bin=os.environ.get("CODEX_BIN"),
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add codex_agent/__init__.py codex_agent/config.py tests/test_config.py
git commit -m "feat: add AgentConfig with env var support"
```

---

### Task 2: BaseTask

**Files:**
- Create: `codex_agent/tasks/__init__.py`
- Create: `codex_agent/tasks/base.py`
- Test: `tests/test_base_task.py`

- [ ] **Step 1: Write the failing test for BaseTask**

```python
# tests/test_base_task.py
from codex_agent.tasks.base import BaseTask


def test_build_prompt_substitutes_template():
    task = BaseTask(
        name="test_task",
        system_prompt="You are a test agent.",
        user_prompt_template="Analyze user {user_id} focusing on {topic}.",
        user_id="user_001",
    )
    prompt = task.build_prompt(topic="relationships")
    assert prompt == "Analyze user user_001 focusing on relationships."


def test_build_prompt_includes_user_id():
    task = BaseTask(
        name="test_task",
        system_prompt="System prompt.",
        user_prompt_template="Search memories for user {user_id}.",
        user_id="user_002",
    )
    prompt = task.build_prompt()
    assert "user_002" in prompt


def test_parse_output_returns_raw_by_default():
    task = BaseTask(
        name="test_task",
        system_prompt="System.",
        user_prompt_template="Template.",
        user_id="user_001",
    )
    assert task.parse_output("raw text") == "raw text"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_base_task.py -v`
Expected: FAIL — module `codex_agent.tasks.base` does not exist

- [ ] **Step 3: Write BaseTask implementation**

```python
# codex_agent/tasks/__init__.py
from .base import BaseTask

__all__ = ["BaseTask"]
```

```python
# codex_agent/tasks/base.py
from dataclasses import dataclass


@dataclass
class BaseTask:
    name: str
    system_prompt: str
    user_prompt_template: str
    user_id: str

    def build_prompt(self, **kwargs) -> str:
        return self.user_prompt_template.format(user_id=self.user_id, **kwargs)

    def parse_output(self, raw: str) -> str:
        return raw
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_base_task.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add codex_agent/tasks/__init__.py codex_agent/tasks/base.py tests/test_base_task.py
git commit -m "feat: add BaseTask with prompt templating"
```

---

### Task 3: TaskRunner

**Files:**
- Create: `codex_agent/runner.py`
- Modify: `codex_agent/__init__.py`
- Test: `tests/test_runner.py`

**Reference docs:**
- Codex SDK client: `codex/sdk/python/src/codex_app_server/client.py`
- V2 types: `codex/sdk/python/src/codex_app_server/generated/v2_all.py`
  - `ThreadStartParams` (line 3888): has `model`, `developer_instructions` fields
  - `AgentMessageDeltaNotification` (line 60): has `.delta` (str) for text chunks
  - `stream_text()` (client.py line 431): convenience method that calls `turn_start`, yields `AgentMessageDeltaNotification` deltas, and waits for `TurnCompletedNotification` internally
  - `ThreadStartResponse`: has `.thread.id`

- [ ] **Step 1: Write the failing test for TaskRunner**

```python
# tests/test_runner.py
from unittest.mock import MagicMock, patch
from codex_agent.config import AgentConfig
from codex_agent.runner import TaskRunner
from codex_agent.tasks.base import BaseTask


def _make_config():
    return AgentConfig(
        base_url="https://uniapi.example.com/v1",
        api_key="sk-test",
        model="gpt-4o",
        codex_bin="/usr/local/bin/codex",
    )


def _make_task():
    return BaseTask(
        name="test",
        system_prompt="You are a test agent.",
        user_prompt_template="Analyze user {user_id}.",
        user_id="user_001",
    )


def test_runner_creates_app_server_config():
    """TaskRunner should build AppServerConfig with correct env and codex_bin."""
    config = _make_config()
    runner = TaskRunner(config)
    app_config = runner._build_app_server_config()
    assert app_config.env["OPENAI_BASE_URL"] == "https://uniapi.example.com/v1"
    assert app_config.env["OPENAI_API_KEY"] == "sk-test"
    assert app_config.codex_bin == "/usr/local/bin/codex"


def test_runner_run_calls_sdk_lifecycle():
    """TaskRunner.run() should call initialize, thread_start, turn_start, and collect deltas."""
    config = _make_config()
    runner = TaskRunner(config)
    task = _make_task()

    # Mock the SDK client
    mock_client = MagicMock()
    mock_thread_resp = MagicMock()
    mock_thread_resp.thread.id = "thread_123"
    mock_client.thread_start.return_value = mock_thread_resp

    mock_turn_resp = MagicMock()
    mock_turn_resp.turn.id = "turn_456"
    mock_client.turn_start.return_value = mock_turn_resp

    # Mock stream_text to yield delta notifications
    mock_delta1 = MagicMock()
    mock_delta1.delta = "Hello "
    mock_delta2 = MagicMock()
    mock_delta2.delta = "World"
    mock_client.stream_text.return_value = iter([mock_delta1, mock_delta2])

    with patch("codex_agent.runner.AppServerClient") as MockClientClass:
        MockClientClass.return_value.__enter__ = MagicMock(return_value=mock_client)
        MockClientClass.return_value.__exit__ = MagicMock(return_value=False)

        result = runner.run(task)

    assert result == "Hello World"
    mock_client.initialize.assert_called_once()
    mock_client.thread_start.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_runner.py -v`
Expected: FAIL — module `codex_agent.runner` does not exist

- [ ] **Step 3: Write TaskRunner implementation**

```python
# codex_agent/runner.py
from codex_app_server import AppServerClient, AppServerConfig
from codex_app_server.generated.v2_all import ThreadStartParams

from .config import AgentConfig
from .tasks.base import BaseTask


class TaskRunner:
    def __init__(self, config: AgentConfig):
        self.config = config

    def _build_app_server_config(self) -> AppServerConfig:
        env = {
            "OPENAI_BASE_URL": self.config.base_url,
            "OPENAI_API_KEY": self.config.api_key,
        }
        return AppServerConfig(
            codex_bin=self.config.codex_bin,
            env=env,
        )

    def run(self, task: BaseTask) -> str:
        app_config = self._build_app_server_config()
        with AppServerClient(config=app_config) as client:
            client.initialize()
            thread = client.thread_start(ThreadStartParams(
                model=self.config.model,
                developer_instructions=task.system_prompt,
            ))
            prompt = task.build_prompt()
            # stream_text handles turn_start + delta collection + wait for completion
            chunks = []
            for delta in client.stream_text(thread.thread.id, prompt):
                chunks.append(delta.delta)
            raw = "".join(chunks)
            return task.parse_output(raw)
```

Update `codex_agent/__init__.py`:

```python
# codex_agent/__init__.py
from .config import AgentConfig
from .runner import TaskRunner

__all__ = ["AgentConfig", "TaskRunner"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_runner.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add codex_agent/runner.py codex_agent/__init__.py tests/test_runner.py
git commit -m "feat: add TaskRunner with Codex SDK lifecycle"
```

---

## Chunk 2: Analysis Tasks

### Task 4: RelationshipsTask

**Files:**
- Create: `codex_agent/tasks/relationships.py`
- Modify: `codex_agent/tasks/__init__.py`
- Test: `tests/test_tasks.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_tasks.py
from codex_agent.tasks.relationships import RelationshipsTask


def test_relationships_task_build_prompt_default():
    task = RelationshipsTask(user_id="user_001")
    prompt = task.build_prompt()
    assert "user_001" in prompt
    assert "人际关系" in prompt or "relationship" in prompt.lower()


def test_relationships_task_build_prompt_with_focus():
    task = RelationshipsTask(user_id="user_001", focus_person="张三")
    prompt = task.build_prompt()
    assert "张三" in prompt


def test_relationships_task_has_system_prompt():
    task = RelationshipsTask(user_id="user_001")
    assert "search_memory" in task.system_prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tasks.py::test_relationships_task_build_prompt_default -v`
Expected: FAIL — module does not exist

- [ ] **Step 3: Write RelationshipsTask implementation**

```python
# codex_agent/tasks/relationships.py
from dataclasses import dataclass, field
from .base import BaseTask

SYSTEM_PROMPT = """你是一个记忆分析助手，专门分析人际关系。你可以使用以下 MCP 工具：
- search_memory: 搜索记忆，支持 keyword/vector/hybrid 检索
- get_memories: 按类型获取记忆

分析流程：
1. 使用 search_memory 搜索与人物、社交场景相关的记忆
2. 多次搜索，覆盖不同关键词（人名、称呼、关系词汇如"朋友""同事""家人"等）
3. 整理所有出现的人物及其关系
4. 输出结构化的人际关系分析

输出格式：
## 人物列表
- 姓名 | 身份/角色 | 与用户的关系

## 关系图谱
- A ↔ B: 关系类型（家人/朋友/同事/…）

## 关键互动事件
- 事件描述 + 涉及人物"""


@dataclass
class RelationshipsTask(BaseTask):
    focus_person: str | None = None

    def __init__(self, user_id: str, focus_person: str | None = None):
        self.focus_person = focus_person
        template = "请分析用户 {user_id} 的人际关系网络。"
        if focus_person:
            template = f"请重点分析用户 {{user_id}} 与「{focus_person}」的关系，同时梳理相关的人际网络。"
        super().__init__(
            name="relationships",
            system_prompt=SYSTEM_PROMPT,
            user_prompt_template=template,
            user_id=user_id,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_tasks.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add codex_agent/tasks/relationships.py tests/test_tasks.py
git commit -m "feat: add RelationshipsTask for relationship analysis"
```

---

### Task 5: ProfilingTask

**Files:**
- Create: `codex_agent/tasks/profiling.py`
- Modify: `codex_agent/tasks/__init__.py`
- Test: append to `tests/test_tasks.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_tasks.py`:

```python
from codex_agent.tasks.profiling import ProfilingTask


def test_profiling_task_build_prompt():
    task = ProfilingTask(user_id="user_001")
    prompt = task.build_prompt()
    assert "user_001" in prompt


def test_profiling_task_has_system_prompt():
    task = ProfilingTask(user_id="user_001")
    assert "search_memory" in task.system_prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tasks.py::test_profiling_task_build_prompt -v`
Expected: FAIL

- [ ] **Step 3: Write ProfilingTask implementation**

```python
# codex_agent/tasks/profiling.py
from dataclasses import dataclass
from .base import BaseTask

SYSTEM_PROMPT = """你是一个记忆分析助手，专门构建用户画像。你可以使用以下 MCP 工具：
- search_memory: 搜索记忆
- get_memories: 按类型获取记忆

分析流程：
1. 广泛搜索用户的日常对话、决策场景、情绪表达
2. 搜索关键词包括：兴趣、爱好、习惯、偏好、态度、情绪、决定等
3. 分析并归纳用户特征

输出格式：
## 兴趣爱好
- 具体兴趣 + 依据

## 性格特征
- 特征描述 + 依据

## 行为习惯
- 习惯描述 + 频率/场景

## 价值观倾向
- 价值观 + 依据"""


@dataclass
class ProfilingTask(BaseTask):
    def __init__(self, user_id: str):
        super().__init__(
            name="profiling",
            system_prompt=SYSTEM_PROMPT,
            user_prompt_template="请为用户 {user_id} 构建详细的用户画像和性格分析。",
            user_id=user_id,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_tasks.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add codex_agent/tasks/profiling.py tests/test_tasks.py
git commit -m "feat: add ProfilingTask for user profiling analysis"
```

---

### Task 6: TimelineTask

**Files:**
- Create: `codex_agent/tasks/timeline.py`
- Test: append to `tests/test_tasks.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_tasks.py`:

```python
from codex_agent.tasks.timeline import TimelineTask


def test_timeline_task_build_prompt_default():
    task = TimelineTask(user_id="user_001")
    prompt = task.build_prompt()
    assert "user_001" in prompt


def test_timeline_task_build_prompt_with_filters():
    task = TimelineTask(
        user_id="user_001",
        start_date="2026-01-01",
        end_date="2026-03-01",
        keywords=["项目", "会议"],
    )
    prompt = task.build_prompt()
    assert "2026-01-01" in prompt
    assert "2026-03-01" in prompt
    assert "项目" in prompt


def test_timeline_task_has_system_prompt():
    task = TimelineTask(user_id="user_001")
    assert "search_memory" in task.system_prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tasks.py::test_timeline_task_build_prompt_default -v`
Expected: FAIL

- [ ] **Step 3: Write TimelineTask implementation**

```python
# codex_agent/tasks/timeline.py
from dataclasses import dataclass
from .base import BaseTask

SYSTEM_PROMPT = """你是一个记忆分析助手，专门整理事件时间线。你可以使用以下 MCP 工具：
- search_memory: 搜索记忆，支持 start_time/end_time 过滤
- get_memories: 按类型获取记忆

分析流程：
1. 使用 search_memory 按时间范围搜索相关事件
2. 如有关键词，使用关键词进一步过滤
3. 按时间顺序整理事件，标注因果关系

输出格式：
## 事件时间线
| 日期 | 事件 | 参与者 | 备注 |
|------|------|--------|------|
| YYYY-MM-DD | 事件描述 | 相关人物 | 因果/关联 |

## 因果关系分析
- 事件A → 事件B: 关联说明"""


@dataclass
class TimelineTask(BaseTask):
    start_date: str | None = None
    end_date: str | None = None
    keywords: list[str] | None = None

    def __init__(
        self,
        user_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
        keywords: list[str] | None = None,
    ):
        self.start_date = start_date
        self.end_date = end_date
        self.keywords = keywords

        parts = ["请整理用户 {user_id} 的事件时间线。"]
        if start_date or end_date:
            time_range = f"时间范围：{start_date or '不限'} 至 {end_date or '不限'}。"
            parts.append(time_range)
        if keywords:
            parts.append(f"重点关注以下关键词：{'、'.join(keywords)}。")

        super().__init__(
            name="timeline",
            system_prompt=SYSTEM_PROMPT,
            user_prompt_template=" ".join(parts),
            user_id=user_id,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_tasks.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add codex_agent/tasks/timeline.py tests/test_tasks.py
git commit -m "feat: add TimelineTask for event timeline analysis"
```

---

### Task 7: SuggestionsTask

**Files:**
- Create: `codex_agent/tasks/suggestions.py`
- Test: append to `tests/test_tasks.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_tasks.py`:

```python
from codex_agent.tasks.suggestions import SuggestionsTask


def test_suggestions_task_build_prompt():
    task = SuggestionsTask(user_id="user_001")
    prompt = task.build_prompt()
    assert "user_001" in prompt


def test_suggestions_task_has_system_prompt():
    task = SuggestionsTask(user_id="user_001")
    assert "search_memory" in task.system_prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tasks.py::test_suggestions_task_build_prompt -v`
Expected: FAIL

- [ ] **Step 3: Write SuggestionsTask implementation**

```python
# codex_agent/tasks/suggestions.py
from dataclasses import dataclass
from .base import BaseTask

SYSTEM_PROMPT = """你是一个记忆分析助手，专门生成主动建议和提醒。你可以使用以下 MCP 工具：
- search_memory: 搜索记忆
- get_memories: 按类型获取记忆（特别关注 foresight 类型）

分析流程：
1. 搜索用户的 foresight 类型记忆（前瞻性记忆）
2. 搜索未完成事项、约定、承诺、周期性事件
3. 关键词包括：计划、约定、承诺、提醒、待办、截止、生日、纪念日等
4. 评估紧急程度和重要性

输出格式：
## 待跟进事项
| 优先级 | 事项 | 建议行动 | 相关上下文 |
|--------|------|----------|------------|
| 高/中/低 | 事项描述 | 建议的下一步 | 来源记忆摘要 |

## 周期性提醒
- 提醒内容 + 建议时间"""


@dataclass
class SuggestionsTask(BaseTask):
    def __init__(self, user_id: str):
        super().__init__(
            name="suggestions",
            system_prompt=SYSTEM_PROMPT,
            user_prompt_template="请为用户 {user_id} 生成主动建议和待办提醒。",
            user_id=user_id,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_tasks.py -v`
Expected: PASS (10 tests)

- [ ] **Step 5: Update tasks `__init__.py` with all exports and commit**

```python
# codex_agent/tasks/__init__.py
from .base import BaseTask
from .relationships import RelationshipsTask
from .profiling import ProfilingTask
from .timeline import TimelineTask
from .suggestions import SuggestionsTask

__all__ = [
    "BaseTask",
    "RelationshipsTask",
    "ProfilingTask",
    "TimelineTask",
    "SuggestionsTask",
]
```

```bash
git add codex_agent/tasks/suggestions.py codex_agent/tasks/__init__.py tests/test_tasks.py
git commit -m "feat: add SuggestionsTask and export all task types"
```

---

## Chunk 3: CLI Entry Point and Integration

### Task 8: CLI Entry Point

**Files:**
- Create: `codex_agent/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli.py
from unittest.mock import patch, MagicMock
from codex_agent.cli import main, TASK_REGISTRY


def test_task_registry_has_all_tasks():
    assert "relationships" in TASK_REGISTRY
    assert "profiling" in TASK_REGISTRY
    assert "timeline" in TASK_REGISTRY
    assert "suggestions" in TASK_REGISTRY


def test_main_calls_runner(capsys):
    with patch("codex_agent.cli.TaskRunner") as MockRunner:
        mock_runner = MagicMock()
        mock_runner.run.return_value = "Analysis result"
        MockRunner.return_value = mock_runner

        with patch("codex_agent.cli.AgentConfig.from_env") as mock_config:
            mock_config.return_value = MagicMock()
            main(["relationships", "--user-id", "user_001"])

        captured = capsys.readouterr()
        assert "Analysis result" in captured.out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL

- [ ] **Step 3: Write CLI implementation**

```python
# codex_agent/cli.py
import argparse
import sys

from .config import AgentConfig
from .runner import TaskRunner
from .tasks.relationships import RelationshipsTask
from .tasks.profiling import ProfilingTask
from .tasks.timeline import TimelineTask
from .tasks.suggestions import SuggestionsTask

TASK_REGISTRY = {
    "relationships": RelationshipsTask,
    "profiling": ProfilingTask,
    "timeline": TimelineTask,
    "suggestions": SuggestionsTask,
}


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Codex Agent — EverMemOS memory analysis")
    parser.add_argument("task", choices=TASK_REGISTRY.keys(), help="Analysis task to run")
    parser.add_argument("--user-id", required=True, help="Target user ID for memory search")
    parser.add_argument("--focus-person", help="(relationships only) Person to focus on")
    parser.add_argument("--start-date", help="(timeline only) Start date filter")
    parser.add_argument("--end-date", help="(timeline only) End date filter")
    parser.add_argument("--keywords", nargs="+", help="(timeline only) Keyword filters")

    args = parser.parse_args(argv)

    config = AgentConfig.from_env()
    runner = TaskRunner(config)

    task_class = TASK_REGISTRY[args.task]
    if args.task == "relationships":
        task = task_class(user_id=args.user_id, focus_person=args.focus_person)
    elif args.task == "timeline":
        task = task_class(
            user_id=args.user_id,
            start_date=args.start_date,
            end_date=args.end_date,
            keywords=args.keywords,
        )
    else:
        task = task_class(user_id=args.user_id)

    result = runner.run(task)
    print(result)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add codex_agent/cli.py tests/test_cli.py
git commit -m "feat: add CLI entry point for codex_agent"
```

---

### Task 9: Codex MCP Configuration

**Files:**
- Modify or create: `~/.codex/config.toml` (document the required config)
- Create: `codex_agent/setup_mcp.py` (helper to print/verify config)

- [ ] **Step 1: Create MCP config helper**

```python
# codex_agent/setup_mcp.py
"""Helper to verify Codex MCP configuration for EverMemOS."""
import os
from pathlib import Path

CODEX_CONFIG_PATH = Path.home() / ".codex" / "config.toml"

REQUIRED_CONFIG = """
# Add this to ~/.codex/config.toml:

[mcp_servers.evermemos]
command = "python"
args = ["-m", "mcp_server.server"]
""".strip()


def check_config() -> bool:
    if not CODEX_CONFIG_PATH.exists():
        print(f"Codex config not found at {CODEX_CONFIG_PATH}")
        print(REQUIRED_CONFIG)
        return False
    content = CODEX_CONFIG_PATH.read_text()
    if "mcp_servers" not in content or "evermemos" not in content:
        print("EverMemOS MCP server not configured in Codex config.")
        print(REQUIRED_CONFIG)
        return False
    print("EverMemOS MCP server is configured in Codex.")
    return True


if __name__ == "__main__":
    check_config()
```

- [ ] **Step 2: Commit**

```bash
git add codex_agent/setup_mcp.py
git commit -m "feat: add MCP config verification helper"
```

---

### Task 10: Run all tests and final commit

- [ ] **Step 1: Run full test suite**

Run: `pytest tests/test_config.py tests/test_base_task.py tests/test_runner.py tests/test_tasks.py tests/test_cli.py -v`
Expected: All tests PASS

- [ ] **Step 2: Final integration verification**

Run: `python -c "from codex_agent import AgentConfig, TaskRunner; from codex_agent.tasks import RelationshipsTask, ProfilingTask, TimelineTask, SuggestionsTask; print('All imports OK')"`
Expected: "All imports OK"

- [ ] **Step 3: Commit any remaining changes**

```bash
git add -A codex_agent/ tests/
git commit -m "feat: complete codex_agent framework with all tasks and CLI"
```
