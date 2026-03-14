"""Batch-ingest GCF JSON into EverMemOS via REST API.

Reads a single merged GCF file (JSON array of groups) and ingests all groups
with async concurrent requests.

Usage:
    python -m pipeline.ingest_gcf --input data/gcf_all.json
    python -m pipeline.ingest_gcf --input data/gcf_all.json --concurrency 8 --api-url http://localhost:1995/api/v1/memories
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

import httpx
from tqdm import tqdm


async def ingest_one_group(
    client: httpx.AsyncClient,
    group: dict,
    api_url: str,
    scene: str,
    semaphore: asyncio.Semaphore,
    msg_progress: tqdm,
) -> dict:
    """Ingest a single GCF group: save meta then post all messages."""
    meta = group.get("conversation_meta", {})
    messages = group.get("conversation_list", [])
    group_id = meta.get("group_id")
    group_name = meta.get("name")

    result = {"group_id": group_id, "messages": len(messages), "success": 0, "errors": 0}

    async with semaphore:
        # Step 1: save conversation meta
        meta_url = f"{api_url}/conversation-meta"
        meta_payload = {
            "scene": scene,
            "scene_desc": meta.get("scene_desc", {}),
            "name": meta.get("name", "Untitled"),
            "description": meta.get("description", ""),
            "group_id": group_id,
            "created_at": meta.get("created_at", ""),
            "default_timezone": meta.get("default_timezone", "Asia/Shanghai"),
            "user_details": meta.get("user_details", {}),
            "tags": meta.get("tags", []),
        }
        try:
            resp = await client.post(meta_url, json=meta_payload)
            if resp.status_code != 200:
                tqdm.write(f"  WARN meta failed for {group_id}: {resp.status_code}")
        except Exception as e:
            tqdm.write(f"  WARN meta error for {group_id}: {e}")

        # Step 2: post messages sequentially (order matters for memory boundary detection)
        for msg in messages:
            payload = {
                "message_id": msg.get("message_id"),
                "create_time": msg.get("create_time"),
                "sender": msg.get("sender"),
                "sender_name": msg.get("sender_name"),
                "content": msg.get("content"),
                "refer_list": msg.get("refer_list", []),
            }
            if group_id:
                payload["group_id"] = group_id
            if group_name:
                payload["group_name"] = group_name

            try:
                resp = await client.post(api_url, json=payload)
                if resp.status_code == 200:
                    result["success"] += 1
                else:
                    result["errors"] += 1
            except Exception:
                result["errors"] += 1

            msg_progress.update(1)

    return result


async def run(input_path: str, api_url: str, scene: str, concurrency: int):
    path = Path(input_path)
    if not path.exists():
        print(f"File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    with open(path, encoding="utf-8") as f:
        groups = json.load(f)

    if not isinstance(groups, list):
        print(f"Expected JSON array, got {type(groups).__name__}", file=sys.stderr)
        sys.exit(1)

    total_groups = len(groups)
    total_messages = sum(len(g.get("conversation_list", [])) for g in groups)

    print(f"==> Ingesting {total_groups} groups, {total_messages} messages, concurrency={concurrency}")

    semaphore = asyncio.Semaphore(concurrency)

    group_bar = tqdm(total=total_groups, desc="Groups  ", unit="group", position=0)
    msg_bar = tqdm(total=total_messages, desc="Messages", unit="msg", position=1)

    start = time.monotonic()
    total_success = 0
    total_errors = 0

    async with httpx.AsyncClient(timeout=300.0) as client:
        tasks = [ingest_one_group(client, g, api_url, scene, semaphore, msg_bar) for g in groups]

        for coro in asyncio.as_completed(tasks):
            result = await coro
            total_success += result["success"]
            total_errors += result["errors"]
            group_bar.update(1)
            if result["errors"] > 0:
                tqdm.write(f"  WARN {result['group_id']}: {result['errors']} errors")

    group_bar.close()
    msg_bar.close()

    elapsed = time.monotonic() - start
    print(f"\n==> Done in {elapsed:.1f}s")
    print(f"  Groups:   {total_groups}")
    print(f"  Messages: {total_success} ok, {total_errors} errors")
    if total_messages > 0:
        print(f"  Speed:    {total_messages / elapsed:.0f} msg/s")


def main():
    parser = argparse.ArgumentParser(description="Batch-ingest GCF into EverMemOS")
    parser.add_argument("--input", default="data/gcf_all.json", help="Merged GCF JSON file")
    parser.add_argument("--api-url", default="http://localhost:1995/api/v1/memories", help="EverMemOS API URL")
    parser.add_argument("--scene", default="group_chat", help="Scene type (default: group_chat)")
    parser.add_argument("--concurrency", type=int, default=5, help="Max concurrent group ingestions (default: 5)")
    args = parser.parse_args()

    asyncio.run(run(args.input, args.api_url, args.scene, args.concurrency))


if __name__ == "__main__":
    main()
