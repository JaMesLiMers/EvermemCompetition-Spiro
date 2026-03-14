"""Batch-generate speaker mapping for all events using LLM.

Sends every event's transcript (with title/type context) to gpt-4o-mini to infer
concrete speaker roles. Existing labels in the transcript are passed as hints.

Usage:
    python -m pipeline.generate_speaker_mapping --input data/basic_events_79ef7f17.json --output data/speaker_mappings.json
    python -m pipeline.generate_speaker_mapping --input data/basic_events_79ef7f17.json --output data/speaker_mappings.json --dry-run
    python -m pipeline.generate_speaker_mapping --input data/basic_events_79ef7f17.json --output data/speaker_mappings.json --force
"""

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path

import httpx
from tqdm import tqdm

# Labels to skip (not real speakers)
_SKIP_LABELS = {"Environment", "Media", "Background", "Background_Voice", "Device"}

# Main user aliases
_MAIN_USER = {"user", "用户", "User"}

SYSTEM_PROMPT = """你是一个对话角色分析专家。给定一段对话转录及其标题和类型，为每个说话人推断出具体、有辨识度的角色标签。

## 核心原则
- 标签必须**具体且有辨识度**，能让读者立刻理解这个人在对话中的身份
- 优先使用**职业/职位**（产品经理、前端工程师、HR总监）
- 其次使用**关系身份**（妻子、丈夫、母亲、室友、大学同学）
- 再次使用**场景角色**（面试官、客户、外卖骑手、医生、房东）
- **绝对禁止**使用以下无意义标签：对话参与者、参与者A/B/C、男性/女性参与者、未知人物

## 推断方法
1. 从对话内容中找线索：称呼（"张总"、"老师"）、话题（技术讨论→工程师）、语气（指导→上级/导师）
2. 从标题和类型找线索：面试场景→面试官+候选人，家庭场景→家人关系
3. 如果说话人标签已包含信息（如"说话人1/女"），保留性别并补充具体角色
4. 多个同类角色用后缀区分（同事甲、同事乙）而不是用字母（A、B、C）
5. 如果实在无法从内容推断具体角色，根据对话场景给出最合理的角色猜测（如工作会议中的"与会同事甲"）

## 输出格式
严格输出 JSON：{"mappings": {"原始标签": "具体角色标签", ...}}

## 示例
标题：产品需求评审会议
{"mappings": {"说话人1": "产品经理", "说话人2": "前端工程师", "说话人3/女": "UI设计师"}}

标题：周末家庭聚餐
{"mappings": {"说话人1/女": "妻子", "说话人2": "岳父", "说话人3/女": "岳母"}}

标题：关于公司裁员消息的讨论
{"mappings": {"说话人1/女": "同事甲(女)", "说话人2/男": "同事乙(男)", "说话人3/女": "同事丙(女)"}}"""


def _extract_speaker_labels(transcript: str) -> set[str]:
    """Extract unique speaker labels from transcript."""
    labels = set()
    for m in re.finditer(r"\[([^\]]+)\]:\s", transcript):
        label = m.group(1)
        if label not in _SKIP_LABELS:
            labels.add(label)
    return labels


def _extract_title_and_types(transcript: str) -> tuple[str, str]:
    """Extract title and type from transcript header."""
    title = ""
    types = ""
    for line in transcript.split("\n")[:20]:
        stripped = line.strip()
        if stripped.startswith("标题:") or stripped.startswith("标题："):
            title = stripped.split(":", 1)[-1].split("：", 1)[-1].strip()
        elif stripped.startswith("类型:") or stripped.startswith("类型："):
            types = stripped.split(":", 1)[-1].split("：", 1)[-1].strip()
    return title, types


def _truncate_transcript(transcript: str, max_chars: int = 4000) -> str:
    """Truncate transcript keeping beginning and end for context."""
    if len(transcript) <= max_chars:
        return transcript
    # Keep more from beginning (context setup) and end (conclusion)
    begin = max_chars * 3 // 5
    end = max_chars * 2 // 5
    return transcript[:begin] + "\n...(中间省略)...\n" + transcript[-end:]


async def _call_llm(
    client: httpx.AsyncClient,
    api_base: str,
    api_key: str,
    model: str,
    transcript_snippet: str,
    labels: set[str],
    title: str,
    types: str,
    semaphore: asyncio.Semaphore,
) -> dict[str, str]:
    """Call LLM to generate speaker mapping."""
    non_user_labels = sorted(l for l in labels if l not in _MAIN_USER and l not in _SKIP_LABELS)
    if not non_user_labels:
        return {}

    context_parts = []
    if title:
        context_parts.append(f"对话标题：{title}")
    if types:
        context_parts.append(f"对话类型：{types}")
    context_header = "\n".join(context_parts)

    user_prompt = f"""{context_header}

以下是对话转录片段：

{transcript_snippet}

需要映射的说话人标签：{json.dumps(non_user_labels, ensure_ascii=False)}

请为每个说话人推断具体角色。"""

    async with semaphore:
        last_err = None
        for attempt in range(3):
            try:
                resp = await client.post(
                    f"{api_base}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": 0.1,
                        "max_tokens": 500,
                        "response_format": {"type": "json_object"},
                    },
                    timeout=60.0,
                )
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                result = json.loads(content)
                return result.get("mappings", result)
            except Exception as e:
                last_err = e
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)  # 1s, 2s backoff
                    continue
                raise last_err


async def run(
    input_path: str,
    output_path: str,
    api_base: str,
    api_key: str,
    model: str,
    concurrency: int,
    dry_run: bool,
    force: bool,
):
    with open(input_path, encoding="utf-8") as f:
        events = json.load(f)

    # Load existing mappings for resume (unless --force)
    existing: dict[str, dict] = {}
    if not force and Path(output_path).exists():
        with open(output_path, encoding="utf-8") as f:
            existing = json.load(f)
        print(f"Loaded {len(existing)} existing mappings (use --force to regenerate all)", file=sys.stderr)

    results: dict[str, dict] = dict(existing)
    skip_count = 0

    # Collect all events that need LLM processing
    to_llm = []
    for event in events:
        event_id = event["meta"]["basic_event_id"]
        transcript = event["object"].get("basic_transcript", "")

        if event_id in existing:
            skip_count += 1
            continue

        if not transcript.strip():
            results[event_id] = {"labels": {}, "source": "empty"}
            skip_count += 1
            continue

        labels = _extract_speaker_labels(transcript)
        non_user = {l for l in labels if l not in _MAIN_USER and l not in _SKIP_LABELS}

        if not non_user:
            results[event_id] = {"labels": {}, "source": "user_only"}
            skip_count += 1
            continue

        to_llm.append((event_id, transcript, labels))

    print(f"Events: {len(events)} total, {len(to_llm)} to process via LLM, {skip_count} skipped", file=sys.stderr)

    if dry_run:
        print(f"\n[DRY RUN] Would call LLM for {len(to_llm)} events", file=sys.stderr)
        for eid, transcript, labels in to_llm[:5]:
            title, types = _extract_title_and_types(transcript)
            non_user = sorted(l for l in labels if l not in _MAIN_USER and l not in _SKIP_LABELS)
            print(f"  {eid[:16]}... title={title[:30]}  labels={non_user}", file=sys.stderr)
        return

    if to_llm:
        semaphore = asyncio.Semaphore(concurrency)
        bar = tqdm(total=len(to_llm), desc="LLM mapping", unit="event")
        errors = 0

        async with httpx.AsyncClient() as client:
            async def process_one(event_id: str, transcript: str, labels: set[str]):
                nonlocal errors
                title, types = _extract_title_and_types(transcript)
                snippet = _truncate_transcript(transcript)
                try:
                    mapping = await _call_llm(
                        client, api_base, api_key, model,
                        snippet, labels, title, types, semaphore,
                    )
                    results[event_id] = {"labels": mapping, "source": "llm"}
                except Exception as e:
                    err_str = f"{type(e).__name__}: {e}" if str(e) else type(e).__name__
                    tqdm.write(f"  ERROR {event_id[:12]}...: {err_str}")
                    results[event_id] = {"labels": {}, "source": "error", "error": err_str}
                    errors += 1
                bar.update(1)

            tasks = [process_one(eid, t, l) for eid, t, l in to_llm]
            await asyncio.gather(*tasks)

        bar.close()
        llm_count = len(to_llm) - errors
        if errors:
            print(f"  {errors} LLM errors", file=sys.stderr)

    # Save results
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\nDone: {len(results)} mappings saved to {output_path}", file=sys.stderr)
    print(f"  LLM-processed:   {len(to_llm)}", file=sys.stderr)
    print(f"  Skipped/cached:  {skip_count}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Generate speaker mappings for all events via LLM")
    parser.add_argument("--input", required=True, help="Path to dataset JSON file")
    parser.add_argument("--output", default="data/speaker_mappings.json", help="Output mapping file")
    parser.add_argument("--api-base", default="https://api.uniapi.me/v1", help="OpenAI-compatible API base URL")
    parser.add_argument("--api-key", default=None, help="API key (default: from OPENCODE_API_KEY env)")
    parser.add_argument("--model", default="gpt-4o-mini", help="Model to use for LLM inference")
    parser.add_argument("--concurrency", type=int, default=10, help="Max concurrent LLM calls")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without calling LLM")
    parser.add_argument("--force", action="store_true", help="Regenerate all mappings (ignore existing)")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("OPENCODE_API_KEY")
    if not api_key and not args.dry_run:
        print("Error: API key required. Set OPENCODE_API_KEY or use --api-key", file=sys.stderr)
        sys.exit(1)

    asyncio.run(run(
        args.input, args.output, args.api_base, api_key or "", args.model,
        args.concurrency, args.dry_run, args.force,
    ))


if __name__ == "__main__":
    main()
