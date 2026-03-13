from agent.tasks.profiling import ProfilingTask
from agent.tasks.relationships import RelationshipsTask
from agent.tasks.suggestions import SuggestionsTask
from agent.tasks.timeline import TimelineTask


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


def test_profiling_task_build_prompt():
    task = ProfilingTask(user_id="user_001")
    prompt = task.build_prompt()
    assert "user_001" in prompt


def test_profiling_task_has_system_prompt():
    task = ProfilingTask(user_id="user_001")
    assert "search_memory" in task.system_prompt


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


def test_suggestions_task_build_prompt():
    task = SuggestionsTask(user_id="user_001")
    prompt = task.build_prompt()
    assert "user_001" in prompt


def test_suggestions_task_has_system_prompt():
    task = SuggestionsTask(user_id="user_001")
    assert "search_memory" in task.system_prompt
