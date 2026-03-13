"""Convert competition dataset events to EverMemOS GroupChatFormat JSON files.

Usage:
    python scripts/convert_to_gcf.py --input Dataset/basic_events_79ef7f17.json --output data/gcf/
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from scripts.transcript_parser import (
    FRAGMENT_PATTERN,
    TITLE_PATTERN,
    TYPE_PATTERN,
    parse_fragment_time,
    parse_speaker_turns,
)

TIMEZONE = ZoneInfo("Asia/Shanghai")

# Speakers that match any of these substrings are skipped
_SKIP_SPEAKER_KEYWORDS = ("背景", "环境", "路人", "无关人员", "Media_Guest")

# Main user aliases → normalized ID
_MAIN_USER_ALIASES = {"user", "用户", "User"}

PASSIVE_MEDIA_MARKER = "被动媒体，转录内容已略过"

_TURN_WINDOW_SIZE = 100  # For windowed splitting of single large fragments


def normalize_speaker(speaker: str) -> str:
    """Normalize main-user aliases to 'user_main'. Others unchanged."""
    return "user_main" if speaker in _MAIN_USER_ALIASES else speaker


def should_skip_speaker(speaker: str) -> bool:
    """Return True if this speaker label should be filtered out."""
    return any(kw in speaker for kw in _SKIP_SPEAKER_KEYWORDS)


def _epoch_to_iso(epoch: int) -> str:
    """Convert epoch seconds to ISO 8601 with Asia/Shanghai timezone."""
    return datetime.fromtimestamp(epoch, tz=TIMEZONE).isoformat()


def parse_fragments(transcript: str, event_start_epoch: int) -> list[dict]:
    """Parse transcript into per-fragment dicts.

    Each dict has:
      - title: str | None
      - types: list[str]
      - base_epoch: int
      - end_epoch: int
      - turns: list[dict]  (from parse_speaker_turns)
    """
    lines = transcript.split("\n")

    # Collect raw fragment boundaries and their lines
    fragments_raw: list[dict] = []
    current: dict | None = None

    for line in lines:
        stripped = line.strip()
        fm = FRAGMENT_PATTERN.match(stripped)
        if fm:
            if current is not None:
                fragments_raw.append(current)
            base = parse_fragment_time(fm.group(1), event_start_epoch)
            end = parse_fragment_time(fm.group(2), base)
            current = {
                "base_epoch": base,
                "end_epoch": end,
                "title": None,
                "types": [],
                "lines": [],
                "is_passive": False,
            }
            continue

        if current is None:
            # No Fragment header seen yet — start implicit fragment
            current = {
                "base_epoch": event_start_epoch,
                "end_epoch": event_start_epoch,
                "title": None,
                "types": [],
                "lines": [],
                "is_passive": False,
            }

        # Check for passive media
        if PASSIVE_MEDIA_MARKER in stripped:
            current["is_passive"] = True
            continue

        # Extract per-fragment title
        if current["title"] is None:
            tm = TITLE_PATTERN.match(stripped)
            if tm:
                current["title"] = tm.group(1).strip()
                continue

        # Extract per-fragment types
        if not current["types"]:
            tp = TYPE_PATTERN.match(stripped)
            if tp:
                current["types"] = [t.strip() for t in tp.group(1).split(",")]
                continue

        current["lines"].append(line)

    if current is not None:
        fragments_raw.append(current)

    # Parse turns and filter passive fragments
    result = []
    for frag in fragments_raw:
        if frag["is_passive"]:
            continue
        duration = max(0, frag["end_epoch"] - frag["base_epoch"])
        turns = parse_speaker_turns(frag["lines"], frag["base_epoch"], duration)
        if not turns:
            continue
        result.append({
            "title": frag["title"],
            "types": frag["types"],
            "base_epoch": frag["base_epoch"],
            "end_epoch": frag["end_epoch"],
            "turns": turns,
        })

    return result


# --- GCF builder ---


def _build_user_details(speakers: set[str]) -> dict:
    """Build GCF user_details from a set of normalized speaker IDs."""
    details = {}
    for s in sorted(speakers):
        if s == "user_main":
            details[s] = {"full_name": "主用户", "role": "user", "custom_role": "记录者"}
        else:
            details[s] = {"full_name": s, "role": "user"}
    return details


def _build_conversation_list(turns: list[dict], group_id: str) -> list[dict]:
    """Convert parsed turns into GCF conversation_list messages."""
    messages = []
    msg_idx = 0
    for turn in turns:
        speaker = turn["speaker_label"]
        if should_skip_speaker(speaker):
            continue
        normalized = normalize_speaker(speaker)
        msg_id = f"{group_id}_{msg_idx}"
        messages.append({
            "message_id": msg_id,
            "create_time": _epoch_to_iso(turn["absolute_epoch"]),
            "sender": normalized,
            "sender_name": speaker,
            "role": "user",
            "type": "text",
            "content": turn["content"],
            "refer_list": [],
        })
        msg_idx += 1
    return messages


def _build_single_gcf(
    group_id: str,
    title: str | None,
    types: list[str],
    base_epoch: int,
    messages: list[dict],
) -> dict:
    """Build a complete GCF dict from components."""
    speakers = {m["sender"] for m in messages}
    return {
        "version": "1.0.0",
        "conversation_meta": {
            "group_id": group_id,
            "name": title or "Untitled",
            "description": title or "",
            "scene": "group_chat",
            "scene_desc": {
                "description": title or "",
                "type": types[0] if types else "unknown",
            },
            "created_at": _epoch_to_iso(base_epoch),
            "default_timezone": "Asia/Shanghai",
            "user_details": _build_user_details(speakers),
            "tags": types,
        },
        "conversation_list": messages,
    }


def build_gcf_groups(
    event_id: str,
    event_start_epoch: int,
    fragments: list[dict],
    split_frag_threshold: int = 8,
    split_turn_threshold: int = 100,
) -> list[dict]:
    """Build GCF group dicts from parsed fragments with smart splitting.

    Returns a list of GCF dicts (each is a complete GroupChatFormat JSON structure).
    """
    total_turns = sum(len(f["turns"]) for f in fragments)
    needs_split = len(fragments) > split_frag_threshold or total_turns > split_turn_threshold

    # Special case: single fragment with lots of turns → window split
    if len(fragments) == 1 and total_turns > 200:
        frag = fragments[0]
        groups = []
        turns = frag["turns"]
        for part_idx in range(0, len(turns), _TURN_WINDOW_SIZE):
            window = turns[part_idx : part_idx + _TURN_WINDOW_SIZE]
            gid = f"{event_id}_part{part_idx // _TURN_WINDOW_SIZE}"
            msgs = _build_conversation_list(window, gid)
            if msgs:
                groups.append(_build_single_gcf(gid, frag["title"], frag["types"], frag["base_epoch"], msgs))
        return groups

    if not needs_split:
        # Merge all fragments into one group
        all_turns = []
        for f in fragments:
            all_turns.extend(f["turns"])
        msgs = _build_conversation_list(all_turns, event_id)
        if not msgs:
            return []
        title = fragments[0]["title"] if fragments else None
        types = fragments[0]["types"] if fragments else []
        base = fragments[0]["base_epoch"] if fragments else event_start_epoch
        return [_build_single_gcf(event_id, title, types, base, msgs)]

    # Split: one group per fragment
    groups = []
    for part_idx, frag in enumerate(fragments):
        gid = f"{event_id}_part{part_idx}"
        msgs = _build_conversation_list(frag["turns"], gid)
        if msgs:
            groups.append(_build_single_gcf(gid, frag["title"], frag["types"], frag["base_epoch"], msgs))
    return groups


# --- Event conversion + CLI ---


def convert_event(
    event: dict,
    split_frag_threshold: int = 8,
    split_turn_threshold: int = 100,
) -> list[dict]:
    """Convert a single dataset event to a list of GCF group dicts.

    Returns empty list if the event should be skipped (empty/passive).
    """
    transcript = event["object"].get("basic_transcript", "")
    if not transcript or not transcript.strip():
        return []

    event_id = event["meta"]["basic_event_id"]
    start_epoch = event["meta"]["basic_start_time"]

    fragments = parse_fragments(transcript, start_epoch)
    if not fragments:
        return []

    return build_gcf_groups(event_id, start_epoch, fragments, split_frag_threshold, split_turn_threshold)


def main():
    parser = argparse.ArgumentParser(description="Convert dataset to GroupChatFormat JSON files")
    parser.add_argument("--input", required=True, help="Path to dataset JSON file")
    parser.add_argument("--output", required=True, help="Output directory for GCF files")
    parser.add_argument("--split-threshold-fragments", type=int, default=8, help="Split events with more fragments than this")
    parser.add_argument("--split-threshold-turns", type=int, default=100, help="Split events with more total turns than this")
    parser.add_argument("--limit", type=int, default=0, help="Process only N events (0 = all)")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(input_path, "r", encoding="utf-8") as f:
        events = json.load(f)

    events.sort(key=lambda e: e["meta"]["basic_start_time"])
    if args.limit > 0:
        events = events[: args.limit]

    total = len(events)
    skipped = 0
    split_count = 0
    total_groups = 0
    total_messages = 0

    for i, event in enumerate(events):
        groups = convert_event(event, args.split_threshold_fragments, args.split_threshold_turns)

        if not groups:
            skipped += 1
            continue

        if len(groups) > 1:
            split_count += 1

        for gcf in groups:
            gid = gcf["conversation_meta"]["group_id"]
            out_path = output_dir / f"{gid}.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(gcf, f, ensure_ascii=False, indent=2)
            total_groups += 1
            total_messages += len(gcf["conversation_list"])

        if (i + 1) % 50 == 0:
            print(f"  [{i+1}/{total}] processed...")

    print(f"\nConversion complete:")
    print(f"  Events processed: {total}")
    print(f"  Events skipped:   {skipped}")
    print(f"  Events split:     {split_count}")
    print(f"  GCF files output: {total_groups}")
    print(f"  Total messages:   {total_messages}")
    print(f"  Output directory: {output_dir}")


if __name__ == "__main__":
    main()
