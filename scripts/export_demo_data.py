#!/usr/bin/env python3
"""Export task outputs to app_demo/data/ for static demo display.

Reads the latest task output JSON files from output/, unifies person IDs,
computes reverse associations, and writes static JSON to app_demo/data/.

Usage:
    python scripts/export_demo_data.py [--output-dir app_demo/data] [--input-dir output]
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

VALID_COLORS = {"blue", "purple", "emerald", "amber"}


def normalize_name(name: str) -> str:
    """Normalize a name for fuzzy matching: lowercase, strip 'the', trim."""
    n = name.lower().strip()
    n = re.sub(r"^the\s+", "", n)
    n = re.sub(r"\s+", "_", n)
    return n


def find_latest_output(input_dir: Path, task_name: str) -> Path | None:
    """Find the most recent output file for a given task name."""
    pattern = f"{task_name}_*.json"
    files = sorted(input_dir.glob(pattern), reverse=True)
    return files[0] if files else None


def load_task_result(filepath: Path) -> dict:
    """Load a task output JSON and extract the result field."""
    with open(filepath) as f:
        data = json.load(f)
    result = data.get("result", {})
    # event_cards result is sometimes a stringified JSON
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except json.JSONDecodeError:
            # Common issue: unescaped double quotes inside string values
            # (e.g. Chinese text using ASCII " instead of Unicode " ")
            # Fix by escaping inner quotes that appear within JSON string values
            fixed = _fix_inner_quotes(result)
            try:
                result = json.loads(fixed)
            except json.JSONDecodeError as e:
                print(f"ERROR: Cannot parse result from {filepath.name}: {e}", file=sys.stderr)
                result = {}
    return result


def _fix_inner_quotes(s: str) -> str:
    """Fix unescaped double quotes inside JSON string values.

    Walks the string character by character, tracking whether we're inside
    a JSON string value. Escapes any unescaped " that appears in the middle
    of a string value (not at the boundary).
    """
    result = []
    i = 0
    in_string = False
    while i < len(s):
        c = s[i]
        if c == '\\' and in_string:
            # Escaped character — pass through both chars
            result.append(c)
            if i + 1 < len(s):
                i += 1
                result.append(s[i])
            i += 1
            continue
        if c == '"':
            if not in_string:
                in_string = True
                result.append(c)
            else:
                # Check if this quote ends the string value:
                # Look ahead past whitespace for , } ] : or end of string
                rest = s[i + 1:].lstrip()
                if not rest or rest[0] in ',}]:':
                    # This is a real closing quote
                    in_string = False
                    result.append(c)
                else:
                    # This is an inner quote — escape it
                    result.append('\\"')
        else:
            result.append(c)
        i += 1
    return ''.join(result)


def build_name_to_id_map(people: list[dict]) -> dict[str, str]:
    """Build a mapping from normalized person name to person ID."""
    mapping = {}
    for person in people:
        pid = person["id"]
        name = person["name"]
        # Exact name → id
        mapping[name] = pid
        # Normalized name → id
        mapping[normalize_name(name)] = pid
        # Also map the id itself
        mapping[pid] = pid
        mapping[normalize_name(pid)] = pid
    return mapping


def resolve_person_id(name: str, name_map: dict[str, str]) -> str | None:
    """Resolve a person name/id to canonical person ID."""
    if name in name_map:
        return name_map[name]
    normalized = normalize_name(name)
    if normalized in name_map:
        return name_map[normalized]
    return None


def export(input_dir: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- Load relationships → people.json ---
    rel_path = find_latest_output(input_dir, "relationships")
    if not rel_path:
        print("ERROR: No relationships output found", file=sys.stderr)
        sys.exit(1)
    rel_data = load_task_result(rel_path)
    # Handle both old schema ("persons") and new schema ("people")
    raw_people = rel_data.get("people", []) or rel_data.get("persons", [])

    # Normalize to new schema: ensure id, relationship fields exist
    people = []
    for p in raw_people:
        person = {
            "id": p.get("id") or normalize_name(p.get("name", "")),
            "name": p.get("name", ""),
            "relationship": p.get("relationship") or p.get("role", ""),
        }
        people.append(person)
    print(f"Loaded {len(people)} people from {rel_path.name}")

    name_map = build_name_to_id_map(people)

    # --- Load event_cards → diaries.json ---
    ec_path = find_latest_output(input_dir, "event_cards")
    if not ec_path:
        print("ERROR: No event_cards output found", file=sys.stderr)
        sys.exit(1)
    ec_data = load_task_result(ec_path)
    # Handle both old schema ("event_cards") and new schema ("diaries")
    raw_cards = ec_data.get("diaries", []) or ec_data.get("event_cards", [])

    # Normalize to new schema: remap field names
    diaries = []
    for i, card in enumerate(raw_cards, 1):
        diaries.append({
            "id": card.get("id") or f"ec_{i:03d}",
            "title": card.get("title", ""),
            "date": card.get("date") or card.get("timestamp", ""),
            "content": card.get("content") or card.get("body", ""),
            "peopleIds": card.get("peopleIds") or card.get("participants", []),
            "tags": card.get("tags", []),
            "sentiment": card.get("sentiment", "neutral"),
        })
    print(f"Loaded {len(diaries)} diaries from {ec_path.name}")

    # Resolve peopleIds in diaries
    unresolved_names = set()
    for diary in diaries:
        resolved_ids = []
        for pid in diary.get("peopleIds", []):
            resolved = resolve_person_id(pid, name_map)
            if resolved:
                resolved_ids.append(resolved)
            else:
                unresolved_names.add(pid)
                resolved_ids.append(normalize_name(pid))
        diary["peopleIds"] = resolved_ids

    if unresolved_names:
        print(f"WARNING: Unresolved person names in diaries: {unresolved_names}", file=sys.stderr)

    # --- Compute reverse associations: diaryIds + occurrenceCount ---
    for person in people:
        person_id = person["id"]
        diary_ids = [d["id"] for d in diaries if person_id in d.get("peopleIds", [])]
        person["diaryIds"] = diary_ids
        person["occurrenceCount"] = len(diary_ids)

    # --- Load profiling → life-topics.json ---
    prof_path = find_latest_output(input_dir, "profiling")
    life_topics = []
    if prof_path:
        prof_data = load_task_result(prof_path)
        life_topics = prof_data.get("life_topics", [])
        # If old format (interests/traits/values), life_topics will be empty
        if not life_topics and any(k in prof_data for k in ("interests", "personality_traits", "values")):
            print("WARNING: Profiling output uses old schema (interests/traits/values). "
                  "Re-run profiling task for LifeTopic format.", file=sys.stderr)
        # Validate colors
        for topic in life_topics:
            if topic.get("color") not in VALID_COLORS:
                topic["color"] = "blue"
        print(f"Loaded {len(life_topics)} life topics from {prof_path.name}")
    else:
        print("WARNING: No profiling output found, life-topics.json will be empty", file=sys.stderr)

    # --- Load suggestions → insights.json ---
    sug_path = find_latest_output(input_dir, "suggestions")
    insights = {}
    if sug_path:
        sug_data = load_task_result(sug_path)
        raw_insights = sug_data.get("insights_by_person", {})
        # If old format (follow_up_items/periodic_reminders), warn
        if not raw_insights and any(k in sug_data for k in ("follow_up_items", "periodic_reminders")):
            print("WARNING: Suggestions output uses old schema (follow_up_items). "
                  "Re-run suggestions task for per-person Insights.", file=sys.stderr)
        # Remap person names → person IDs
        for person_name, person_insights in raw_insights.items():
            person_id = resolve_person_id(person_name, name_map)
            if person_id:
                insights[person_id] = person_insights
            else:
                normalized = normalize_name(person_name)
                insights[normalized] = person_insights
                print(f"WARNING: Could not resolve insight person '{person_name}', "
                      f"using '{normalized}'", file=sys.stderr)
        print(f"Loaded insights for {len(insights)} people from {sug_path.name}")
    else:
        print("WARNING: No suggestions output found, insights.json will be empty", file=sys.stderr)

    # --- Write output files ---
    def write_json(filename: str, data):
        path = output_dir / filename
        with open(path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  Wrote {path}")

    write_json("people.json", people)
    write_json("diaries.json", diaries)
    write_json("life-topics.json", life_topics)
    write_json("insights.json", insights)
    write_json("meta.json", {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_files": {
            "relationships": rel_path.name if rel_path else None,
            "event_cards": ec_path.name if ec_path else None,
            "profiling": prof_path.name if prof_path else None,
            "suggestions": sug_path.name if sug_path else None,
        },
    })

    print(f"\nDone! {len(people)} people, {len(diaries)} diaries, "
          f"{len(life_topics)} topics, {len(insights)} insight groups")


def main():
    parser = argparse.ArgumentParser(description="Export task outputs to app_demo data files")
    parser.add_argument("--input-dir", default="output", help="Directory containing task output JSON files")
    parser.add_argument("--output-dir", default="app_demo/data", help="Directory to write demo data files")
    args = parser.parse_args()
    export(Path(args.input_dir), Path(args.output_dir))


if __name__ == "__main__":
    main()
