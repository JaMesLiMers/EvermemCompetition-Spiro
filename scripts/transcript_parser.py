import re
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

TURN_PATTERN = re.compile(r"^\[(\d+):(\d+)\]\[([^\]]+)\]:\s*(.+)$")
ANNOTATION_PATTERN = re.compile(r"\[[^\[\]]{1,20}\]\s*")
FRAGMENT_PATTERN = re.compile(r"^\[Fragment \d+:\s*(.+?)\s*-\s*(.+?)\]$")
TIMEZONE = ZoneInfo("Asia/Shanghai")


def parse_speaker_turns(lines: list[str], fragment_base_epoch: int) -> list[dict]:
    turns = []
    for line in lines:
        m = TURN_PATTERN.match(line.strip())
        if not m:
            continue
        minutes, seconds = int(m.group(1)), int(m.group(2))
        speaker_label = m.group(3)
        raw_content = m.group(4)
        content = ANNOTATION_PATTERN.sub("", raw_content).strip()
        if not content:
            continue
        offset_seconds = minutes * 60 + seconds
        absolute_epoch = fragment_base_epoch + offset_seconds
        turns.append({
            "speaker_label": speaker_label,
            "content": content,
            "offset_seconds": offset_seconds,
            "absolute_epoch": absolute_epoch,
        })
    return turns


def parse_fragment_time(time_str: str, event_start_epoch: int) -> int:
    time_str = time_str.strip()
    if time_str.isdigit() or (len(time_str) > 5 and time_str.replace(".", "").isdigit()):
        return int(float(time_str))
    try:
        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        dt = dt.replace(tzinfo=TIMEZONE)
        return int(dt.timestamp())
    except ValueError:
        return event_start_epoch


def parse_transcript(transcript: str, event_start_epoch: int) -> list[dict]:
    lines = transcript.split("\n")
    all_turns = []
    current_fragment_base = event_start_epoch
    for line in lines:
        fm = FRAGMENT_PATTERN.match(line.strip())
        if fm:
            current_fragment_base = parse_fragment_time(fm.group(1), event_start_epoch)
            continue
        m = TURN_PATTERN.match(line.strip())
        if not m:
            continue
        minutes, seconds = int(m.group(1)), int(m.group(2))
        speaker_label = m.group(3)
        raw_content = m.group(4)
        content = ANNOTATION_PATTERN.sub("", raw_content).strip()
        if not content:
            continue
        offset_seconds = minutes * 60 + seconds
        absolute_epoch = current_fragment_base + offset_seconds
        all_turns.append({
            "speaker_label": speaker_label,
            "content": content,
            "offset_seconds": offset_seconds,
            "absolute_epoch": absolute_epoch,
        })
    return all_turns


def parse_speaker_analysis(speaker_analysis_json) -> list[dict]:
    if not speaker_analysis_json:
        return []
    if isinstance(speaker_analysis_json, list):
        return speaker_analysis_json
    try:
        return json.loads(speaker_analysis_json)
    except (json.JSONDecodeError, TypeError):
        return []


def match_speaker(speaker_label: str, speakers: list[dict]) -> dict | None:
    for s in speakers:
        identity = s.get("identity", "")
        relation = s.get("relation_to_user", "")
        if identity and (identity in speaker_label or speaker_label in identity):
            return s
        if relation and (relation in speaker_label or speaker_label in relation):
            return s
    return None
