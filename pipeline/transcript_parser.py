import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

TURN_PATTERN_A = re.compile(r"^\[(\d+):(\d+)\]\[([^\]]+)\]:\s*(.+)$")
TURN_PATTERN_B = re.compile(r"^\[([^\]]+)\]:\s*(.+)$")
# Format C: [MM:SS-MM:SS] SPEAKER_XX {display_name | confidence}: text
TURN_PATTERN_C = re.compile(
    r"^\[(\d+):(\d+)-\d+:\d+\]\s+"
    r"(SPEAKER_\d+)\s+"
    r"\{([^}]*)\}:\s*(.+)$"
)
ANNOTATION_KEYWORDS = re.compile(
    r"\["
    r"(?:[^\[\]]*(?:音调|语速|语气|停顿|音量|说明|理解|引导|列举|表示|肯定|犹豫|思考|认真|专业|正常|平稳|较快|稍快|平缓|上扬|降低|恢复)[^\[\]]*)"
    r"\]\s*"
)
FRAGMENT_PATTERN = re.compile(r"^\[Fragment \d+:\s*(.+?)\s*-\s*(.+?)\](?:\s+.*)?$")
SEGMENT_PATTERN = re.compile(r"^\[Segment \d+:")
METADATA_LINE = re.compile(r"^【.+】")
TITLE_PATTERN = re.compile(r"^标题:\s*(.+)$")
TYPE_PATTERN = re.compile(r"^类型:\s*(.+)$")
TIMEZONE = ZoneInfo("Asia/Shanghai")


def parse_speaker_turns(
    lines: list[str],
    fragment_base_epoch: int,
    fragment_duration: int = 0,
) -> list[dict]:
    """Parse transcript lines into speaker turns with absolute timestamps.

    Supports Format A ([MM:SS][speaker]: text) and Format B ([speaker]: text).
    Format B turns get interpolated timestamps across the fragment duration.
    """
    turns = []
    format_b_indices: list[int] = []

    for line in lines:
        stripped = line.strip()
        # Skip metadata lines (【转录】, 【总结】, [Segment ...], etc.)
        if METADATA_LINE.match(stripped) or SEGMENT_PATTERN.match(stripped):
            continue

        # Try Format C first: [MM:SS-MM:SS] SPEAKER_XX {display | conf}: text
        m = TURN_PATTERN_C.match(stripped)
        if m:
            minutes, seconds = int(m.group(1)), int(m.group(2))
            speaker_label = m.group(3)
            display_info = m.group(4)
            # Extract display name from "{display_name | confidence}"
            display_name = display_info.split("|")[0].strip() if "|" in display_info else display_info.strip()
            if display_name:
                speaker_label = display_name
            raw_content = m.group(5)
            content = ANNOTATION_KEYWORDS.sub("", raw_content).strip()
            if not content:
                continue
            offset_seconds = minutes * 60 + seconds
            turns.append({
                "speaker_label": speaker_label,
                "content": content,
                "offset_seconds": offset_seconds,
                "absolute_epoch": fragment_base_epoch + offset_seconds,
            })
            continue

        # Try Format A: [MM:SS][speaker]: text
        m = TURN_PATTERN_A.match(stripped)
        if m:
            minutes, seconds = int(m.group(1)), int(m.group(2))
            speaker_label = m.group(3)
            raw_content = m.group(4)
            content = ANNOTATION_KEYWORDS.sub("", raw_content).strip()
            if not content:
                continue
            offset_seconds = minutes * 60 + seconds
            turns.append({
                "speaker_label": speaker_label,
                "content": content,
                "offset_seconds": offset_seconds,
                "absolute_epoch": fragment_base_epoch + offset_seconds,
            })
            continue

        # Fallback to Format B
        m = TURN_PATTERN_B.match(stripped)
        if m:
            speaker_label = m.group(1)
            raw_content = m.group(2)
            # Skip Fragment headers and metadata lines that match the pattern
            if speaker_label.startswith("Fragment "):
                continue
            content = ANNOTATION_KEYWORDS.sub("", raw_content).strip()
            if not content:
                continue
            turns.append({
                "speaker_label": speaker_label,
                "content": content,
                "offset_seconds": 0,
                "absolute_epoch": fragment_base_epoch,
            })
            format_b_indices.append(len(turns) - 1)

    # Interpolate Format B timestamps evenly across fragment duration
    if format_b_indices and fragment_duration > 0:
        count = len(format_b_indices)
        for i, idx in enumerate(format_b_indices):
            offset = int(fragment_duration * i / max(count, 1))
            turns[idx]["offset_seconds"] = offset
            turns[idx]["absolute_epoch"] = fragment_base_epoch + offset
    elif format_b_indices:
        # No duration info: assign 1s increments
        for i, idx in enumerate(format_b_indices):
            turns[idx]["offset_seconds"] = i
            turns[idx]["absolute_epoch"] = fragment_base_epoch + i

    return turns


def parse_fragment_time(time_str: str, event_start_epoch: int) -> int:
    """Parse a Fragment header time string to epoch seconds.

    Handles formats: human-readable '2026-02-23 06:13', epoch '1766845585',
    and short HH:MM like '08:51' (treated as offset hours:minutes from event start)."""
    time_str = time_str.strip()
    if time_str.isdigit() or (len(time_str) > 5 and time_str.replace(".", "").isdigit()):
        return int(float(time_str))
    # Short HH:MM format — treat as hour:minute offset from event start date
    short_hm = re.match(r"^(\d{1,2}):(\d{2})$", time_str)
    if short_hm:
        hours, minutes = int(short_hm.group(1)), int(short_hm.group(2))
        return event_start_epoch + hours * 3600 + minutes * 60
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
    current_fragment_end = event_start_epoch
    title = None
    types = []

    for line in lines:
        stripped = line.strip()

        fm = FRAGMENT_PATTERN.match(stripped)
        if fm:
            if current_fragment_lines:
                duration = max(0, current_fragment_end - current_fragment_base)
                all_turns.extend(parse_speaker_turns(
                    current_fragment_lines, current_fragment_base, duration
                ))
                current_fragment_lines = []
            current_fragment_base = parse_fragment_time(fm.group(1), event_start_epoch)
            current_fragment_end = parse_fragment_time(fm.group(2), current_fragment_base)
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
        duration = max(0, current_fragment_end - current_fragment_base)
        all_turns.extend(parse_speaker_turns(
            current_fragment_lines, current_fragment_base, duration
        ))

    speakers = list({t["speaker_label"] for t in all_turns})

    return {
        "turns": all_turns,
        "title": title,
        "types": types,
        "speakers": speakers,
    }
