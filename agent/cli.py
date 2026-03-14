# agent/cli.py
import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
import re
from datetime import datetime
from pathlib import Path

from shared.evermemos_api import EverMemosClient

from .config import AgentConfig
from .tasks.event_cards import EventCardsTask
from .tasks.profiling import ProfilingTask
from .tasks.relationships import RelationshipsTask
from .tasks.suggestions import SuggestionsTask
from .tasks.timeline import TimelineTask

TASK_REGISTRY = {
    "relationships": RelationshipsTask,
    "profiling": ProfilingTask,
    "timeline": TimelineTask,
    "suggestions": SuggestionsTask,
    "event_cards": EventCardsTask,
}


async def prefetch_memories(base_url: str, group_id: str) -> tuple[str, int]:
    """Pre-fetch all episodic memories for a group and format as context string.

    Returns (context_string, memory_count).
    """
    client = EverMemosClient(base_url)
    try:
        data = await client.get_memories(group_id=group_id, memory_type="episodic_memory", limit=100)
        memories = data.get("result", {}).get("memories", [])
        if not memories:
            return "", 0

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
        return "\n".join(lines), len(memories)
    finally:
        await client.close()


def _extract_json(raw: str) -> str:
    """Extract JSON from agent output, stripping markdown fences or surrounding text."""
    # Try to find JSON in ```json ... ``` blocks
    m = re.search(r"```json\s*\n(.*?)\n\s*```", raw, re.DOTALL)
    if m:
        return m.group(1).strip()
    # Try to find a top-level JSON object
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if m:
        candidate = m.group(0)
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            pass
    # Fallback: return raw
    return raw.strip()


def _build_task(task_name: str, args: argparse.Namespace, group_id: str | None, prefetched: str):
    """Build a task instance from parsed CLI arguments."""
    task_class = TASK_REGISTRY[task_name]

    # Collect all optional kwargs that the task class __init__ accepts
    optional_params = {
        "focus_person": getattr(args, "focus_person", None),
        "start_date": getattr(args, "start_date", None),
        "end_date": getattr(args, "end_date", None),
        "keywords": getattr(args, "keywords", None),
    }

    # Only pass params that the task class actually accepts
    import inspect

    sig = inspect.signature(task_class.__init__)
    accepted = set(sig.parameters.keys()) - {"self"}

    kwargs = {"user_id": args.user_id, "group_id": group_id, "prefetched_context": prefetched}
    for key, value in optional_params.items():
        if key in accepted and value is not None:
            kwargs[key] = value

    return task_class(**kwargs)


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="EverMemOS Agent — memory analysis")
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
    evermemos_url = config.evermemos_url

    # Auto-detect group_ids from GCF file if not provided
    group_id = args.group_id
    group_ids: list[str] = []
    if group_id:
        group_ids = [group_id]
    else:
        try:
            gcf_path = Path("data/gcf_all.json")
            if gcf_path.exists():
                with open(gcf_path) as f:
                    gcf_list = json.load(f)
                for gcf in gcf_list:
                    gid = gcf.get("conversation_meta", {}).get("group_id")
                    if gid:
                        group_ids.append(gid)
                if group_ids:
                    group_id = group_ids[0]
                    print(f"Auto-detected {len(group_ids)} group_ids from data/gcf_all.json", file=sys.stderr)
        except Exception:
            pass

    # Pre-fetch memories from all groups (capped to avoid oversized prompts)
    prefetched = ""
    memory_count = 0
    MAX_PREFETCH_CHARS = 50000  # Cap total context to ~50KB
    if group_ids:
        print(f"Pre-fetching memories from {len(group_ids)} groups...", file=sys.stderr)
        all_parts = []
        total_chars = 0
        for gid in group_ids:
            ctx, cnt = asyncio.run(prefetch_memories(evermemos_url, gid))
            if ctx:
                if total_chars + len(ctx) > MAX_PREFETCH_CHARS:
                    print(f"  Reached {MAX_PREFETCH_CHARS} char limit, stopping prefetch", file=sys.stderr)
                    break
                all_parts.append(ctx)
                memory_count += cnt
                total_chars += len(ctx)
        prefetched = "\n".join(all_parts)
        if prefetched:
            print(f"Pre-fetched context ready ({len(prefetched)} chars, {memory_count} memories)", file=sys.stderr)

    task = _build_task(args.task, args, group_id, prefetched)

    prompt = task.build_prompt()
    system_prompt = task.system_prompt
    full_prompt = f"System: {system_prompt}\n\n{prompt}"

    import tempfile

    start_time = time.monotonic()

    # Write prompt to temp file to avoid "Argument list too long" error
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as tmp:
        tmp.write(full_prompt)
        tmp_path = tmp.name

    try:
        agent_result = subprocess.run(
            f'cat "{tmp_path}" | {config.agent_bin} run --model {config.model}',
            capture_output=True,
            text=True,
            shell=True,
            cwd=".",
        )
    finally:
        os.unlink(tmp_path)
    duration_s = time.monotonic() - start_time

    if agent_result.returncode != 0:
        print(f"ERROR: opencode exited with code {agent_result.returncode}", file=sys.stderr)
        if agent_result.stderr:
            print(agent_result.stderr, file=sys.stderr)
        sys.exit(agent_result.returncode)

    raw_result = agent_result.stdout
    result = _extract_json(raw_result)
    print(result)

    if not args.no_save:
        os.makedirs(args.output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{args.task}_{timestamp}.json"
        filepath = os.path.join(args.output_dir, filename)

        # Wrap result with metadata into a JSON envelope
        metadata = {
            "task": args.task,
            "model": config.model,
            "user_id": args.user_id,
            "group_id": group_id or None,
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": round(duration_s, 1),
            "prefetched_memories": memory_count,
        }
        if getattr(args, "focus_person", None):
            metadata["focus_person"] = args.focus_person
        if getattr(args, "start_date", None):
            metadata["start_date"] = args.start_date
        if getattr(args, "end_date", None):
            metadata["end_date"] = args.end_date
        if getattr(args, "keywords", None):
            metadata["keywords"] = args.keywords

        # Try to parse result as JSON for clean output; fallback to raw string
        try:
            result_obj = json.loads(result)
        except (json.JSONDecodeError, TypeError):
            result_obj = result

        envelope = {"metadata": metadata, "result": result_obj}
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(envelope, f, ensure_ascii=False, indent=2)
        print(f"\n✓ 结果已保存至 {filepath}", file=sys.stderr)

        # Append to experiment manifest
        manifest_path = os.path.join(args.output_dir, "manifest.jsonl")
        entry = {
            "task": args.task,
            "model": config.model,
            "user_id": args.user_id,
            "group_id": group_id,
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": round(duration_s, 1),
            "prefetched_memories": memory_count,
            "output_file": filename,
        }
        if getattr(args, "focus_person", None):
            entry["focus_person"] = args.focus_person
        if getattr(args, "start_date", None):
            entry["start_date"] = args.start_date
        if getattr(args, "end_date", None):
            entry["end_date"] = args.end_date
        if getattr(args, "keywords", None):
            entry["keywords"] = args.keywords
        with open(manifest_path, "a", encoding="utf-8") as mf:
            mf.write(json.dumps(entry, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
