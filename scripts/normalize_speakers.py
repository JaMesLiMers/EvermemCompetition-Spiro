"""Normalize transcript format in basic_events JSON.

1. Remove all timestamps from speaker lines
2. Replace generic speaker IDs with 说话人1/说话人2/说话人3 (per event, by appearance order)
3. Keep meaningful role labels (同事/朋友, 伴侣, etc.) as-is
4. Keep 用户 as-is
5. Ensure every dialogue line has a speaker label
6. Previous format fixes (Fragment headers, Format C, multi-speaker split, etc.)
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TIMEZONE = ZoneInfo("Asia/Shanghai")

# Patterns that indicate a generic/unnamed speaker needing replacement
_GENERIC_SPEAKER_PATTERNS = [
    re.compile(r'^unified_\d+'),
    re.compile(r'^SPEAKER_\d+'),
    re.compile(r'^Person\b'),
    re.compile(r'^Speaker\s*[A-Z]'),
    re.compile(r'^Individual\b'),
    re.compile(r'^Participant\b'),
    re.compile(r'^Unidentified\b'),
    re.compile(r'^unknown$', re.IGNORECASE),
]

# Speaker labels that should be kept as-is (meaningful roles)
_KEEP_SPEAKER = re.compile(r'^用户$')


def is_generic_speaker(label: str) -> bool:
    """Check if a speaker label is generic and needs replacement."""
    # Strip gender suffix for matching: unified_001/男 → unified_001
    base = label.split('/')[0].strip()
    return any(p.match(base) for p in _GENERIC_SPEAKER_PATTERNS)


def _epoch_to_datetime_str(epoch_str: str) -> str:
    """Convert epoch string to 'YYYY-MM-DD HH:MM' in Asia/Shanghai."""
    try:
        ts = int(float(epoch_str))
        dt = datetime.fromtimestamp(ts, tz=TIMEZONE)
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, OSError):
        return epoch_str


def _pad_timestamp(ts: str) -> str:
    """Pad timestamp to MM:SS format."""
    parts = ts.split(':')
    if len(parts) == 2:
        return f'{int(parts[0]):02d}:{int(parts[1]):02d}'
    return ts


def normalize_fragment_headers(transcript: str) -> str:
    """Convert epoch-based Fragment headers to datetime format."""
    def replace_epoch_fragment(m):
        prefix = m.group(1)
        t1 = _epoch_to_datetime_str(m.group(2).strip())
        t2 = _epoch_to_datetime_str(m.group(3).strip())
        suffix = m.group(4) or ""
        return f"{prefix} {t1} - {t2}]{suffix}"

    return re.sub(
        r'(\[Fragment \d+:)\s*(\d{10,})\s+-\s+(\d{10,})\](.*)',
        replace_epoch_fragment,
        transcript,
    )


def normalize_to_format_b(transcript: str) -> str:
    """Convert all dialogue lines to Format B: [speaker]: text.

    Handles:
    - Format A: [MM:SS][speaker]: text → [speaker]: text
    - Format C variants → [speaker]: text
    - Missing brackets: [MM:SS]speaker: → [speaker]:
    - Multi-speaker same line → split
    """
    lines = transcript.split('\n')
    new_lines = []

    # Format C with braces
    pat_c_braces = re.compile(
        r'^\[(\d+:\d+)-\d+:\d+\]\s+'
        r'(.+?)\s+'
        r'\{([^}]*)\}:\s*(.+)$'
    )
    # Format C no braces, normal timestamps
    pat_c_no_braces = re.compile(
        r'^\[(\d{1,2}:\d{2})-\d{1,2}:\d{2}\]\s+'
        r'([^\[\]:]+?):\s*(.+)$'
    )
    # Format C broken large timestamps
    pat_c_weird = re.compile(
        r'^\[(\d{4,}):\d+-\d+:\d+\]\s+'
        r'([^\[\]:]+?):\s*(.+)$'
    )
    # Format A: [MM:SS][speaker]: text
    pat_a = re.compile(r'^\[(\d{2}:\d{2})\]\[([^\]]+)\]:\s*(.+)$')
    # Multi-speaker on same line
    pat_multi = re.compile(r'\[(\d{2}:\d{2})\]\[([^\]]+)\]:')
    # Missing brackets: [MM:SS]speaker: text
    pat_missing = re.compile(r'^\[(\d{2}:\d{2})\]([^\[\]\s][^\[\]]*?):\s*(.+)$')
    # Metadata prefix
    pat_meta_prefix = re.compile(r'^【[^】]*】\s*')

    for line in lines:
        s = line.strip()

        # Strip 【...】 prefix from Format C lines
        pm = pat_meta_prefix.match(s)
        if pm and re.match(r'^\[\d+:\d+-', s[pm.end():]):
            s = s[pm.end():]

        # Check multi-speaker line first
        markers = list(pat_multi.finditer(s))
        if len(markers) > 1:
            for i, mk in enumerate(markers):
                start = mk.start()
                end = markers[i + 1].start() if i + 1 < len(markers) else len(s)
                seg = s[start:end].strip()
                # Each segment is Format A — strip timestamp
                m2 = pat_a.match(seg)
                if m2:
                    new_lines.append(f'[{m2.group(2)}]: {m2.group(3)}')
                else:
                    new_lines.append(seg)
            continue

        # Format C with braces
        m = pat_c_braces.match(s)
        if m:
            speaker_raw = m.group(2)
            display_info = m.group(3)
            text = m.group(4)
            display_name = display_info.split("|")[0].strip() if "|" in display_info else display_info.strip()
            if not display_name or display_name.lower().startswith("unknown"):
                display_name = speaker_raw
            display_name = re.sub(r'\(\d+%\s*conf to user\)', '', display_name).strip()
            new_lines.append(f'[{display_name}]: {text}')
            continue

        # Format C broken timestamps
        m = pat_c_weird.match(s)
        if m:
            speaker = re.sub(r'\(\d+%\s*conf to user\)', '', m.group(2)).strip()
            new_lines.append(f'[{speaker}]: {m.group(3)}')
            continue

        # Format C normal timestamps, no braces
        m = pat_c_no_braces.match(s)
        if m and not s.startswith('[Fragment'):
            speaker = re.sub(r'\(\d+%\s*conf to user\)', '', m.group(2)).strip()
            new_lines.append(f'[{speaker}]: {m.group(3)}')
            continue

        # Format A: [MM:SS][speaker]: text → [speaker]: text
        # Handle nested brackets in speaker names (e.g., [Media])
        m = re.match(r'^\[\d{2}:\d{2}\]\[(.+)\]:\s*(.+)$', s)
        if m:
            new_lines.append(f'[{m.group(1)}]: {m.group(2)}')
            continue

        # Timestamp-only annotation lines: [MM:SS][env desc] or [MM:SS] (desc)
        # Strip the timestamp prefix
        m = re.match(r'^\[\d{2}:\d{2}\](.+)$', s)
        if m:
            rest = m.group(1).strip()
            if rest:
                new_lines.append(rest)
            continue

        # Missing brackets: [MM:SS]speaker: text → [speaker]: text
        m = pat_missing.match(s)
        if m:
            new_lines.append(f'[{m.group(2)}]: {m.group(3)}')
            continue

        new_lines.append(line)

    return '\n'.join(new_lines)


def normalize_speaker_labels(transcript: str) -> str:
    """Normalize individual speaker labels (clean up formatting issues)."""
    # Patterns for both formats (now all should be Format B after normalize_to_format_b)
    pat = re.compile(r'^\[([^\]]+)\]:', re.MULTILINE)

    all_speakers = set()
    for m in pat.finditer(transcript):
        all_speakers.add(m.group(1))

    if not all_speakers:
        return transcript

    mapping = {}
    for speaker in all_speakers:
        normalized = speaker
        # user/User → 用户
        if normalized in ("user", "User"):
            normalized = "用户"
        # Strip confidence annotations
        normalized = re.sub(r'\(\d+%\s*conf to user\)', '', normalized).strip()
        # Strip parenthetical annotations from generic IDs
        normalized = re.sub(r'^((?:unified_\d+|SPEAKER_\d+))\s*\([^)]*\)', r'\1', normalized)
        # Remove /未知 suffix
        normalized = re.sub(r'^((?:unified_\d+|SPEAKER_\d+))/未知$', r'\1', normalized)
        # Normalize /男孩 → /男
        normalized = re.sub(r'^((?:unified_\d+|SPEAKER_\d+))/男孩$', r'\1/男', normalized)
        # Fix bare gender
        if normalized in ("/男", "/女"):
            normalized = f"unknown{normalized}"
        # Deduplicate role parts
        if '/' in normalized:
            parts = normalized.split('/')
            deduped = []
            for p in parts:
                p_stripped = p.strip()
                if p_stripped and p_stripped not in deduped:
                    deduped.append(p_stripped)
            if deduped != parts:
                normalized = '/'.join(deduped)

        if normalized != speaker:
            mapping[speaker] = normalized

    if not mapping:
        return transcript

    result = transcript
    for old, new in sorted(mapping.items(), key=lambda x: -len(x[0])):
        escaped = re.escape(old)
        result = re.sub(rf'\[{escaped}\]:', f'[{new}]:', result)

    return result


def replace_generic_speakers(transcript: str) -> str:
    """Replace generic speaker IDs with 说话人1/说话人2/... per event.

    Maintains consistent mapping: same generic ID → same 说话人N throughout the event.
    Preserves gender suffix: unified_001/男 → 说话人2/男
    """
    pat = re.compile(r'^\[([^\]]+)\]:', re.MULTILINE)

    # Collect all speakers in order of first appearance
    seen_order = []
    seen_set = set()
    for m in pat.finditer(transcript):
        spk = m.group(1)
        # Get the base label (strip gender suffix for grouping)
        base = spk
        gender_suffix = ''
        if '/' in spk:
            parts = spk.split('/')
            # Check if the base part is generic
            if is_generic_speaker(parts[0]):
                base = parts[0]
                gender_suffix = '/' + '/'.join(parts[1:])

        if base not in seen_set:
            seen_set.add(base)
            seen_order.append(base)

    # Build mapping: generic speakers → 说话人N
    mapping = {}
    counter = 1
    for base in seen_order:
        if is_generic_speaker(base):
            mapping[base] = f'说话人{counter}'
            counter += 1

    if not mapping:
        return transcript

    # Apply replacements (longest first to avoid partial matches)
    result = transcript
    for old_base, new_base in sorted(mapping.items(), key=lambda x: -len(x[0])):
        # Replace all variants: [old_base]: and [old_base/gender]:
        escaped = re.escape(old_base)
        # Match with optional gender/role suffix
        def replacer(m):
            full_label = m.group(1)
            if full_label == old_base:
                return f'[{new_base}]:'
            # Has suffix after base
            suffix = full_label[len(old_base):]
            return f'[{new_base}{suffix}]:'

        result = re.sub(rf'\[({escaped}(?:/[^\]]*)?)\]:', replacer, result)

    return result


def remove_dash_separators(transcript: str) -> str:
    """Remove lines that are just dashes."""
    lines = transcript.split('\n')
    return '\n'.join(l for l in lines if not re.match(r'^\s*-{5,}\s*$', l))


def process_event_transcript(transcript: str) -> str:
    """Process a single event's transcript with all normalizations."""
    result = transcript

    # 1. Fragment headers: epoch → datetime
    result = normalize_fragment_headers(result)

    # 2. Convert all formats to Format B and strip timestamps
    result = normalize_to_format_b(result)

    # 3. Remove dash separators
    result = remove_dash_separators(result)

    # 4. Clean up speaker labels (confidence, 未知, etc.)
    result = normalize_speaker_labels(result)

    # 5. Replace generic IDs with 说话人N
    result = replace_generic_speakers(result)

    return result


def main():
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/basic_events_79ef7f17.json")
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else input_path

    print(f"Reading {input_path}...")
    with open(input_path, "r", encoding="utf-8") as f:
        events = json.load(f)

    print(f"Processing {len(events)} events...")
    modified_count = 0

    for i, event in enumerate(events):
        transcript = event["object"].get("basic_transcript", "")
        if not transcript:
            continue

        new_transcript = process_event_transcript(transcript)
        if new_transcript != transcript:
            event["object"]["basic_transcript"] = new_transcript
            modified_count += 1

        if (i + 1) % 100 == 0:
            print(f"  [{i+1}/{len(events)}] processed...")

    print(f"\nModified {modified_count}/{len(events)} events")
    print(f"Writing to {output_path}...")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    print("Done!")


if __name__ == "__main__":
    main()
