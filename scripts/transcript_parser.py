import re
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

TURN_PATTERN = re.compile(r"^\[(\d+):(\d+)\]\[([^\]]+)\]:\s*(.+)$")
ANNOTATION_PATTERN = re.compile(r"\[[^\[\]]{1,20}\]\s*")
FRAGMENT_PATTERN = re.compile(r"^\[Fragment \d+:\s*(.+?)\s*-\s*(.+?)\]$")
TITLE_PATTERN = re.compile(r"^标题:\s*(.+)$")
TYPE_PATTERN = re.compile(r"^类型:\s*(.+)$")
TIMEZONE = ZoneInfo("Asia/Shanghai")


def parse_speaker_turns(lines: list[str], fragment_base_epoch: int) -> list[dict]:
    """Parse transcript lines into speaker turns with absolute timestamps."""
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
    """Parse a Fragment header time string to epoch seconds.

    Handles two formats: human-readable '2026-02-23 06:13' and epoch '1766845585'."""
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
    """Parse a full transcript into speaker turns with absolute timestamps.

    Handles multiple Fragments, each with their own base time."""
    result = parse_transcript_with_metadata(transcript, event_start_epoch)
    return result["turns"]


def parse_transcript_with_metadata(transcript: str, event_start_epoch: int) -> dict:
    """Parse a full transcript, extracting both speaker turns and metadata.

    Returns dict with:
      - turns: list of speaker turn dicts
      - title: first Fragment's title (from '标题:' line), or None
      - types: first Fragment's types (from '类型:' line), or []
      - speakers: set of unique speaker labels found
    """
    lines = transcript.split("\n")
    all_turns = []
    current_fragment_lines = []
    current_fragment_base = event_start_epoch
    title = None
    types = []

    for line in lines:
        stripped = line.strip()

        fm = FRAGMENT_PATTERN.match(stripped)
        if fm:
            if current_fragment_lines:
                all_turns.extend(parse_speaker_turns(current_fragment_lines, current_fragment_base))
                current_fragment_lines = []
            current_fragment_base = parse_fragment_time(fm.group(1), event_start_epoch)
            continue

        # Extract title from first occurrence
        if title is None:
            tm = TITLE_PATTERN.match(stripped)
            if tm:
                title = tm.group(1).strip()
                continue

        # Extract types from first occurrence
        if not types:
            tp = TYPE_PATTERN.match(stripped)
            if tp:
                types = [t.strip() for t in tp.group(1).split(",")]
                continue

        current_fragment_lines.append(line)

    if current_fragment_lines:
        all_turns.extend(parse_speaker_turns(current_fragment_lines, current_fragment_base))

    speakers = list({t["speaker_label"] for t in all_turns})

    return {
        "turns": all_turns,
        "title": title,
        "types": types,
        "speakers": speakers,
    }


def parse_speaker_analysis(speaker_analysis_json) -> list[dict]:
    """Parse the basic_speaker_analysis into a list of speaker info dicts.

    Handles both JSON string and pre-parsed list inputs."""
    if not speaker_analysis_json:
        return []
    if isinstance(speaker_analysis_json, list):
        return speaker_analysis_json
    try:
        return json.loads(speaker_analysis_json)
    except (json.JSONDecodeError, TypeError):
        return []


def match_speaker(speaker_label: str, speakers: list[dict]) -> dict | None:
    """Match a transcript speaker label to a speaker analysis entry.

    Uses substring matching on identity and relation_to_user fields."""
    for s in speakers:
        identity = s.get("identity", "")
        relation = s.get("relation_to_user", "")
        if identity and (identity in speaker_label or speaker_label in identity):
            return s
        if relation and (relation in speaker_label or speaker_label in relation):
            return s
    return None
