# scripts/ingest_data.py
"""
Batch ingest Dataset events into EverMemOS.

Usage:
    python scripts/ingest_data.py --input Dataset/basic_events_79ef7f17.json --limit 2
    python scripts/ingest_data.py --input Dataset/basic_events_79ef7f17.json --resume
"""

import argparse
import asyncio
import json
import sys
import httpx
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from scripts.transcript_parser import parse_transcript_with_metadata
from scripts.evermemos_api import EverMemosClient

TIMEZONE = ZoneInfo("Asia/Shanghai")
PROGRESS_FILE = Path("scripts/ingestion_progress.json")


def epoch_to_iso(epoch: int) -> str:
    """Convert epoch seconds to ISO 8601 with Asia/Shanghai timezone."""
    return datetime.fromtimestamp(epoch, tz=TIMEZONE).isoformat()


def build_user_details(speaker_labels: list[str]) -> dict:
    """Build user_details dict for conversation-meta from transcript speaker labels."""
    details = {}
    for label in speaker_labels:
        details[label] = {
            "full_name": label,
            "role": "user",
        }
    return details


def load_progress() -> dict:
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    return {"completed": [], "failed": {}}


def save_progress(progress: dict):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)


async def ingest_event(client: EverMemosClient, event: dict, progress: dict) -> bool:
    """Ingest a single event into EverMemOS. Returns True on success."""
    meta = event["meta"]
    obj = event["object"]
    event_id = meta["basic_event_id"]

    transcript = obj.get("basic_transcript", "")
    if not transcript or not transcript.strip():
        print(f"  SKIP (empty transcript): {event_id}")
        return True

    parsed = parse_transcript_with_metadata(transcript, meta["basic_start_time"])
    turns = parsed["turns"]
    if not turns:
        print(f"  SKIP (no valid turns): {event_id}")
        return True

    # Use metadata from transcript Fragment headers (fallback for missing object fields)
    title = obj.get("basic_title") or parsed["title"] or "Untitled"
    basic_types = obj.get("basic_type") or parsed["types"] or []
    scene_desc = {
        "description": obj.get("basic_scene", ""),
        "type": basic_types[0] if basic_types else "unknown",
    }
    user_details = build_user_details(parsed["speakers"])

    try:
        await client.create_conversation_meta(
            group_id=event_id,
            name=title,
            scene="group_chat",
            scene_desc=scene_desc,
            user_details=user_details,
            created_at=epoch_to_iso(meta["basic_start_time"]),
        )
    except Exception as e:
        print(f"  ERROR (conversation-meta): {e}")
        return False

    # Send each turn as a message
    failed_turns = []
    for idx, turn in enumerate(turns):
        sender = turn["speaker_label"]
        sender_name = turn["speaker_label"]

        try:
            await client.store_message(
                message_id=f"{event_id}_{idx}",
                create_time=epoch_to_iso(turn["absolute_epoch"]),
                sender=sender,
                sender_name=sender_name,
                content=turn["content"],
                group_id=event_id,
                group_name=title,
                role="user",
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code >= 500:
                success = False
                for delay in [1, 2, 4]:
                    await asyncio.sleep(delay)
                    try:
                        await client.store_message(
                            message_id=f"{event_id}_{idx}",
                            create_time=epoch_to_iso(turn["absolute_epoch"]),
                            sender=sender, sender_name=sender_name,
                            content=turn["content"], group_id=event_id,
                            group_name=title, role="user",
                        )
                        success = True
                        break
                    except Exception:
                        continue
                if not success:
                    print(f"  ERROR (turn {idx}, 5xx after 3 retries): {e}")
                    failed_turns.append(idx)
            else:
                print(f"  ERROR (turn {idx}, {e.response.status_code}): {e}")
                failed_turns.append(idx)
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            await asyncio.sleep(1)
            try:
                await client.store_message(
                    message_id=f"{event_id}_{idx}",
                    create_time=epoch_to_iso(turn["absolute_epoch"]),
                    sender=sender, sender_name=sender_name,
                    content=turn["content"], group_id=event_id,
                    group_name=title, role="user",
                )
            except Exception:
                print(f"  ERROR (turn {idx}, network): {e}")
                failed_turns.append(idx)
        except Exception as e:
            print(f"  ERROR (turn {idx}): {e}")
            failed_turns.append(idx)

        await asyncio.sleep(0.01)

    if failed_turns:
        progress["failed"][event_id] = failed_turns
        return False
    return True


async def main():
    parser = argparse.ArgumentParser(description="Ingest dataset into EverMemOS")
    parser.add_argument("--input", required=True, help="Path to dataset JSON file")
    parser.add_argument("--api-url", default="http://localhost:1995", help="EverMemOS base URL")
    parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint")
    parser.add_argument("--limit", type=int, default=0, help="Process only N events (0 = all)")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        events = json.load(f)

    # Sort events chronologically
    events.sort(key=lambda e: e["meta"]["basic_start_time"])

    print(f"Loaded {len(events)} events from {input_path}")

    progress = load_progress() if args.resume else {"completed": [], "failed": {}}
    completed_set = set(progress["completed"])

    total = len(events)
    if args.limit > 0:
        events = events[:args.limit]
        total = len(events)

    success_count = 0
    skip_count = 0
    fail_count = 0

    async with EverMemosClient(args.api_url) as client:
        for i, event in enumerate(events):
            event_id = event["meta"]["basic_event_id"]
            if event_id in completed_set:
                skip_count += 1
                continue

            title = event["object"].get("basic_title", "")
            print(f"[{i+1}/{total}] {event_id[:12]}... {title[:40]}")

            ok = await ingest_event(client, event, progress)
            if ok:
                success_count += 1
                progress["completed"].append(event_id)
            else:
                fail_count += 1

            if (i + 1) % 10 == 0:
                save_progress(progress)

    save_progress(progress)
    print(f"\nDone: {success_count} succeeded, {fail_count} failed, {skip_count} skipped (already done)")


if __name__ == "__main__":
    asyncio.run(main())
