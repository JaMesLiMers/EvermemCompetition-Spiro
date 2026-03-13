from agent.tasks.base import BaseTask


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
