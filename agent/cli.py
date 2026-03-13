# codex_agent/cli.py
import argparse
import asyncio
import json
import os
import sys
from datetime import datetime

import subprocess

from shared.evermemos_api import EverMemosClient

from .config import AgentConfig
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


async def prefetch_memories(base_url: str, group_id: str) -> str:
    """Pre-fetch all episodic memories for a group and format as context string."""
    client = EverMemosClient(base_url)
    try:
        data = await client.get_memories(group_id=group_id, memory_type="episodic_memory", limit=100)
        memories = data.get("result", {}).get("memories", [])
        if not memories:
            return ""

        lines = [f"已从 EverMemOS 预加载 {len(memories)} 条情景记忆（group_id={group_id}）：\n"]
        for i, m in enumerate(memories, 1):
            title = m.get("title", "无标题")
            summary = m.get("summary", "")
            participants = ", ".join(m.get("participants", []))
            lines.append(f"### 记忆 {i}: {title}")
            lines.append(f"- 参与者: {participants}")
            lines.append(f"- 摘要: {summary}")
            if m.get("key_events"):
                lines.append(f"- 关键事件: {json.dumps(m['key_events'], ensure_ascii=False)}")
            lines.append("")
        return "\n".join(lines)
    finally:
        await client.close()


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Codex Agent — EverMemOS memory analysis")
    parser.add_argument("task", choices=TASK_REGISTRY.keys(), help="Analysis task to run")
    parser.add_argument("--user-id", required=True, help="Target user/participant name")
    parser.add_argument("--group-id", help="EverMemOS group_id (auto-detected if not set)")
    parser.add_argument("--focus-person", help="(relationships only) Person to focus on")
    parser.add_argument("--start-date", help="(timeline only) Start date filter")
    parser.add_argument("--end-date", help="(timeline only) End date filter")
    parser.add_argument("--keywords", nargs="+", help="(timeline only) Keyword filters")
    parser.add_argument("--output-dir", default="output", help="Directory to save results (default: output/)")
    parser.add_argument("--no-save", action="store_true", help="Don't save results to file")

    args = parser.parse_args(argv)

    config = AgentConfig.from_env()
    evermemos_url = os.environ.get("EVERMEMOS_BASE_URL", "http://localhost:1995")

    # Auto-detect group_id from dataset if not provided
    group_id = args.group_id
    if not group_id:
        try:
            dataset_path = "data/basic_events_79ef7f17.json"
            with open(dataset_path) as f:
                events = json.load(f)
            events.sort(key=lambda e: e["meta"]["basic_start_time"])
            group_id = events[0]["meta"]["basic_event_id"]
            print(f"Auto-detected group_id: {group_id}", file=sys.stderr)
        except Exception:
            pass

    # Pre-fetch memories
    prefetched = ""
    if group_id:
        print("Pre-fetching memories...", file=sys.stderr)
        prefetched = asyncio.run(prefetch_memories(evermemos_url, group_id))
        if prefetched:
            print(f"Pre-fetched context ready ({len(prefetched)} chars)", file=sys.stderr)

    task_class = TASK_REGISTRY[args.task]
    if args.task == "relationships":
        task = task_class(user_id=args.user_id, focus_person=args.focus_person, group_id=group_id, prefetched_context=prefetched)
    elif args.task == "timeline":
        task = task_class(
            user_id=args.user_id,
            start_date=args.start_date,
            end_date=args.end_date,
            keywords=args.keywords,
            group_id=group_id,
            prefetched_context=prefetched,
        )
    else:
        task = task_class(user_id=args.user_id, group_id=group_id, prefetched_context=prefetched)

    prompt = task.build_prompt()
    system_prompt = task.system_prompt
    full_prompt = f"System: {system_prompt}\n\n{prompt}"
    codex_result = subprocess.run(
        [config.codex_bin, "--model", config.model, "--prompt", full_prompt],
        capture_output=True, text=True, cwd=".",
    )
    result = codex_result.stdout
    print(result)

    if not args.no_save:
        os.makedirs(args.output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{args.task}_{timestamp}.md"
        filepath = os.path.join(args.output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"\n✓ 结果已保存至 {filepath}", file=sys.stderr)


if __name__ == "__main__":
    main()
