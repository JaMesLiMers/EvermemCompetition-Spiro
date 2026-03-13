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
