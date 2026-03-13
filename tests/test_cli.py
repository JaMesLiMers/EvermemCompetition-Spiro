# tests/test_cli.py
from agent.cli import TASK_REGISTRY
from agent.tasks.profiling import ProfilingTask
from agent.tasks.relationships import RelationshipsTask
from agent.tasks.suggestions import SuggestionsTask
from agent.tasks.timeline import TimelineTask


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
