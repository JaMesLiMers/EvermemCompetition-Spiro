# Demo Data Adaptation Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adapt task outputs to feed the app_demo frontend with static pre-generated JSON data, removing Gemini dependency and switching to English output.

**Architecture:** Modify 4 task prompts to output English with demo-aligned schemas. Create a merge script (`scripts/export_demo_data.py`) that reads task outputs, unifies IDs, computes reverse associations, and writes static JSON to `app_demo/data/`. Update demo components to import static data and render letter avatars.

**Tech Stack:** Python 3.10+ (merge script), React/TypeScript (demo), D3.js (relationship graph)

**Spec:** `docs/superpowers/specs/2026-03-14-demo-data-adaptation-design.md`

---

## Chunk 1: Task Prompt Modifications

### Task 1: Update event_cards prompt for demo-aligned DiaryEntry output

**Files:**
- Modify: `agent/tasks/event_cards.py`

- [ ] **Step 1: Update SYSTEM_PROMPT to English with new schema**

Replace the entire `SYSTEM_PROMPT` and `user_prompt_template` in `event_cards.py`:

```python
SYSTEM_PROMPT = """You are a memory analysis assistant that transforms conversation memories into readable event cards for a personal memory app.

You will receive pre-loaded episodic memory data. Read all memories carefully, then generate one event card for each meaningful event.

If you need more information, use these tools for supplementary searches:
- search_memory: Search memories. **Important: must provide group_id parameter**
- get_memories: Get memories by type. **Important: must provide group_id parameter**

Requirements:
1. Read all pre-loaded memories carefully
2. Identify each independent, meaningful event
3. Generate a concise, engaging English title and narrative content for each
4. Title should be short and evocative (under 10 words)
5. Content should clearly describe the key moments in 2-5 sentences, written as a personal diary narrative
6. Extract participants, time, location, and emotional tone
7. Order event cards chronologically
8. Use consistent English names for participants across all cards — the same person must always use the same name
9. Translate all Chinese content to natural English

**Output strict JSON only — no markdown, no extra text. Output a valid JSON object in this exact format:**

```json
{
  "diaries": [
    {
      "id": "ec_001",
      "title": "Short evocative title",
      "date": "Month Day, Year (e.g. March 10, 2026) or Season Year if exact date unknown",
      "content": "2-5 sentence narrative description written as a personal memory...",
      "peopleIds": ["person_name_snake_case", "another_person"],
      "tags": ["tag1", "tag2"],
      "sentiment": "positive/neutral/negative"
    }
  ]
}
```

For peopleIds, use snake_case English names (e.g. "the_architect", "grandma", "husband"). These must match the person names used in the relationships analysis."""
```

Update the class:

```python
@dataclass
class EventCardsTask(BaseTask):
    def __init__(self, user_id: str, group_id: str | None = None, prefetched_context: str = ""):
        super().__init__(
            name="event_cards",
            system_prompt=SYSTEM_PROMPT,
            user_prompt_template="Based on the group conversation memories, generate event cards for '{user_id}' — one card per significant event.",
            user_id=user_id,
            group_id=group_id,
            prefetched_context=prefetched_context,
        )
```

- [ ] **Step 2: Commit**

```bash
git add agent/tasks/event_cards.py
git commit -m "feat(event_cards): switch prompt to English, align output schema with demo DiaryEntry"
```

---

### Task 2: Update relationships prompt for demo-aligned Person output

**Files:**
- Modify: `agent/tasks/relationships.py`

- [ ] **Step 1: Update SYSTEM_PROMPT to English with new schema**

Replace the entire `SYSTEM_PROMPT` and class:

```python
SYSTEM_PROMPT = """You are a memory analysis assistant specialized in analyzing interpersonal relationships.

You will receive pre-loaded episodic memory data. Read all memories carefully, then perform deep analysis.

If you need more information, use these tools for supplementary searches:
- search_memory: Search memories (keyword/vector/hybrid). **Important: must provide group_id parameter**
- get_memories: Get memories by type. **Important: must provide group_id parameter**

Requirements:
1. Read all pre-loaded memories carefully
2. Identify all people mentioned and their relationships to the main user
3. Analyze each person's role, traits, and interaction patterns
4. **Critical: Each person must appear exactly once with a unique, consistent English name. Do NOT use role-based aliases — if someone is both "husband" and "male partner", pick ONE name and use it consistently.**
5. Translate all names and descriptions to English

**Output strict JSON only — no markdown, no extra text. Output a valid JSON object in this exact format:**

```json
{
  "people": [
    {
      "id": "snake_case_name",
      "name": "Display Name",
      "relationship": "Brief relationship description (e.g. Tech Lead & Mentor, Husband, Close Friend)",
      "key_traits": ["trait1", "trait2"]
    }
  ]
}
```

For the id field, use a snake_case version of the name (e.g. "the_architect", "grandma"). These IDs will be referenced by other analyses, so consistency is critical."""
```

Update the class:

```python
@dataclass
class RelationshipsTask(BaseTask):
    focus_person: str | None = None

    def __init__(
        self, user_id: str, focus_person: str | None = None, group_id: str | None = None, prefetched_context: str = ""
    ):
        self.focus_person = focus_person
        template = "Analyze the interpersonal relationship network of all participants in this group conversation, focusing on '{user_id}'."
        if focus_person:
            template = f"Focus on analyzing '{{user_id}}'s relationship with '{focus_person}', while mapping the broader social network."
        super().__init__(
            name="relationships",
            system_prompt=SYSTEM_PROMPT,
            user_prompt_template=template,
            user_id=user_id,
            group_id=group_id,
            prefetched_context=prefetched_context,
        )
```

- [ ] **Step 2: Commit**

```bash
git add agent/tasks/relationships.py
git commit -m "feat(relationships): switch prompt to English, align output schema with demo Person"
```

---

### Task 3: Update profiling prompt for LifeTopic output

**Files:**
- Modify: `agent/tasks/profiling.py`

- [ ] **Step 1: Replace SYSTEM_PROMPT with LifeTopic schema**

This is the largest prompt change — restructure from interests/traits/values/habits lists into aggregated life topics.

```python
SYSTEM_PROMPT = """You are a memory analysis assistant that identifies the major life themes and concerns from a person's conversation history.

You will receive pre-loaded episodic memory data. Read all memories carefully, then extract the dominant life topics.

If you need more information, use these tools for supplementary searches:
- search_memory: Search memories. **Important: must provide group_id parameter**
- get_memories: Get memories by type. **Important: must provide group_id parameter**

Requirements:
1. Read all pre-loaded memories carefully
2. Identify 5-8 major life topics/themes from the conversations
3. Each topic should aggregate related interests, values, habits, and personality traits
4. Assign a gravity score (0-100) representing how much this topic weighs on the person's life
5. Write a one-sentence poetic description for each topic
6. Choose an appropriate emoji icon
7. Color must be exactly one of: "blue", "purple", "emerald", "amber"
8. All output in English

**Output strict JSON only — no markdown, no extra text. Output a valid JSON object in this exact format:**

```json
{
  "life_topics": [
    {
      "id": "lt_001",
      "name": "Topic Name (e.g. Family & Nurturing)",
      "gravity": 85,
      "description": "A one-sentence poetic description of this life theme",
      "icon": "👶",
      "color": "blue"
    }
  ]
}
```

Distribute colors evenly across the 4 options (blue, purple, emerald, amber). Order topics by gravity (highest first)."""
```

Update the class:

```python
@dataclass
class ProfilingTask(BaseTask):
    def __init__(self, user_id: str, group_id: str | None = None, prefetched_context: str = ""):
        super().__init__(
            name="profiling",
            system_prompt=SYSTEM_PROMPT,
            user_prompt_template="Extract the major life topics and themes for '{user_id}' from the group conversation memories.",
            user_id=user_id,
            group_id=group_id,
            prefetched_context=prefetched_context,
        )
```

- [ ] **Step 2: Commit**

```bash
git add agent/tasks/profiling.py
git commit -m "feat(profiling): restructure prompt from traits lists to aggregated LifeTopics"
```

---

### Task 4: Update suggestions prompt for per-person Insight output

**Files:**
- Modify: `agent/tasks/suggestions.py`

- [ ] **Step 1: Replace SYSTEM_PROMPT with Insight schema grouped by person**

```python
SYSTEM_PROMPT = """You are a memory analysis assistant that generates personal insights about the people in someone's life.

You will receive pre-loaded episodic memory data. Read all memories carefully, then generate insights grouped by person.

If you need more information, use these tools for supplementary searches:
- search_memory: Search memories. **Important: must provide group_id parameter**
- get_memories: Get memories by type (especially foresight type). **Important: must provide group_id parameter**

Requirements:
1. Read all pre-loaded memories carefully
2. For each person mentioned in the memories, generate 2-5 insights
3. Insights should capture promises, needs, personality observations, upcoming events, or birthdays
4. Each insight type must be exactly one of: "birthday", "event", "personality", "promise", "need"
5. Use the same person names (English) as used in the relationships analysis
6. All output in English

**Output strict JSON only — no markdown, no extra text. Output a valid JSON object in this exact format:**

```json
{
  "insights_by_person": {
    "Person Name": [
      {
        "id": "ins_001",
        "text": "Mentioned wanting to visit the ceramics market next month",
        "type": "event"
      }
    ],
    "Another Person": [
      {
        "id": "ins_002",
        "text": "Has been expressing concern about work-life balance",
        "type": "need"
      }
    ]
  }
}
```

Focus on actionable, meaningful insights — things the user would genuinely want to remember or act on."""
```

Update the class:

```python
@dataclass
class SuggestionsTask(BaseTask):
    def __init__(self, user_id: str, group_id: str | None = None, prefetched_context: str = ""):
        super().__init__(
            name="suggestions",
            system_prompt=SYSTEM_PROMPT,
            user_prompt_template="Generate personal insights about the people in '{user_id}''s life, grouped by person, based on group conversation memories.",
            user_id=user_id,
            group_id=group_id,
            prefetched_context=prefetched_context,
        )
```

- [ ] **Step 2: Commit**

```bash
git add agent/tasks/suggestions.py
git commit -m "feat(suggestions): restructure prompt to per-person Insights grouped by name"
```

---

### Task 5: Update base task prompt to English

**Files:**
- Modify: `agent/tasks/base.py`

- [ ] **Step 1: Change the prefetch context separator to English**

In `base.py`, update `build_prompt`:

```python
def build_prompt(self, **kwargs) -> str:
    prompt = self.user_prompt_template.format(user_id=self.user_id, **kwargs)
    if self.prefetched_context:
        prompt = f"{prompt}\n\n---\nBelow is pre-loaded memory data. Analyze based on this data:\n\n{self.prefetched_context}"
    return prompt
```

- [ ] **Step 2: Commit**

```bash
git add agent/tasks/base.py
git commit -m "feat(base): switch prefetch context separator to English"
```

---

## Chunk 2: Merge Script

### Task 6: Create the export_demo_data.py merge script

**Files:**
- Create: `scripts/export_demo_data.py`

- [ ] **Step 1: Write the merge script**

```python
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
        result = json.loads(result)
    return result


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
    # Try exact match
    if name in name_map:
        return name_map[name]
    # Try normalized match
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
        # Remove key_traits (not in demo Person interface)
        person.pop("key_traits", None)

    # --- Load profiling → life-topics.json ---
    prof_path = find_latest_output(input_dir, "profiling")
    life_topics = []
    if prof_path:
        prof_data = load_task_result(prof_path)
        life_topics = prof_data.get("life_topics", [])
        # If old format (interests/traits/values), life_topics will be empty — that's OK
        if not life_topics and any(k in prof_data for k in ("interests", "personality_traits", "values")):
            print("WARNING: Profiling output uses old schema (interests/traits/values). Re-run profiling task for LifeTopic format.", file=sys.stderr)
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
            print("WARNING: Suggestions output uses old schema (follow_up_items). Re-run suggestions task for per-person Insights.", file=sys.stderr)
        # Remap person names → person IDs
        for person_name, person_insights in raw_insights.items():
            person_id = resolve_person_id(person_name, name_map)
            if person_id:
                insights[person_id] = person_insights
            else:
                normalized = normalize_name(person_name)
                insights[normalized] = person_insights
                print(f"WARNING: Could not resolve insight person '{person_name}', using '{normalized}'", file=sys.stderr)
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

    print(f"\nDone! {len(people)} people, {len(diaries)} diaries, {len(life_topics)} topics, {len(insights)} insight groups")


def main():
    parser = argparse.ArgumentParser(description="Export task outputs to app_demo data files")
    parser.add_argument("--input-dir", default="output", help="Directory containing task output JSON files")
    parser.add_argument("--output-dir", default="app_demo/data", help="Directory to write demo data files")
    args = parser.parse_args()
    export(Path(args.input_dir), Path(args.output_dir))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify script runs (with current outputs, expect warnings about schema mismatch)**

```bash
python scripts/export_demo_data.py --input-dir output --output-dir app_demo/data
```

Expected: Runs but warns about missing `diaries` key (current output uses `event_cards` key — script handles both).

- [ ] **Step 3: Commit**

```bash
git add scripts/export_demo_data.py
git commit -m "feat: add export_demo_data.py merge script for static demo data"
```

---

### Task 7: Add Makefile targets

**Files:**
- Modify: `Makefile`

- [ ] **Step 1: Add export-demo and demo targets**

Append to the end of the Makefile:

```makefile
export-demo: ## Export task outputs to app_demo/data/ for static demo
	python scripts/export_demo_data.py --input-dir output --output-dir app_demo/data

demo: ## Start the demo app (requires npm)
	cd app_demo && npm run dev
```

- [ ] **Step 2: Commit**

```bash
git add Makefile
git commit -m "feat: add export-demo and demo Makefile targets"
```

---

## Chunk 3: Demo Code Changes

### Task 8: Update TypeScript types (make avatar and audioSnippets optional)

**Files:**
- Modify: `app_demo/types.ts`

- [ ] **Step 1: Make avatar and audioSnippets optional**

In `types.ts`:
- Change `avatar: string;` → `avatar?: string;`
- Change `audioSnippets: AudioSnippet[];` → `audioSnippets?: AudioSnippet[];`

- [ ] **Step 2: Commit**

```bash
git add app_demo/types.ts
git commit -m "feat(types): make avatar and audioSnippets optional for static data support"
```

---

### Task 9: Update App.tsx — replace hardcoded data with static JSON imports

**Files:**
- Modify: `app_demo/App.tsx`

- [ ] **Step 1: Replace data imports and remove Gemini calls**

At the top of `App.tsx`:
- Remove `import { generateDiaryBackground, analyzeLifeTopics } from './services/geminiService';`
- Add static imports:
  ```ts
  import peopleData from './data/people.json';
  import diariesData from './data/diaries.json';
  import lifeTopicsData from './data/life-topics.json';
  import insightsData from './data/insights.json';
  ```

- [ ] **Step 2: Remove INITIAL_PEOPLE and DIARIES constants**

Delete the `INITIAL_PEOPLE` array (lines ~11-17) and `DIARIES` array (lines ~19-182).

- [ ] **Step 3: Update initial state to use imported data**

Replace the `useState<AppState>` initialization:

```ts
const [state, setState] = useState<AppState>({
  currentDiary: diariesData[0] as DiaryEntry,
  diaries: diariesData as DiaryEntry[],
  people: peopleData as Person[],
  view: 'home',
  lifeTopics: lifeTopicsData as LifeTopic[],
});
```

- [ ] **Step 4: Remove the useEffect that calls analyzeLifeTopics**

Delete the `useEffect` block (lines ~201-211) that calls `analyzeLifeTopics`. Also remove the `isAnalyzing` state variable if no longer referenced.

- [ ] **Step 5: Remove handleRegenerateBackground function**

Delete the `handleRegenerateBackground` function and any UI button that calls it.

- [ ] **Step 6: Pass insightsData to TimeRiver (or let it import directly)**

When rendering `TimeRiver`, pass insights as a prop. Add to TimeRiver usage:
```tsx
<TimeRiver
  person={selectedPerson}
  diaries={state.diaries}
  insights={insightsData[selectedPerson.id] || []}
  onBack={...}
  onEdit={...}
/>
```

- [ ] **Step 7: Commit**

```bash
git add app_demo/App.tsx
git commit -m "feat(App): replace hardcoded data with static JSON imports, remove Gemini dependency"
```

---

### Task 10: Update TimeRiver — use static insights, make chat optional

**Files:**
- Modify: `app_demo/components/TimeRiver.tsx`

- [ ] **Step 1: Add insights prop, remove Gemini insight generation**

Update the props interface:
```ts
interface TimeRiverProps {
  person: Person;
  diaries: DiaryEntry[];
  insights?: Insight[];
  onBack: () => void;
  onEdit: () => void;
}
```

Update the component signature:
```ts
const TimeRiver: React.FC<TimeRiverProps> = ({ person, diaries, insights: propInsights, onBack, onEdit }) => {
```

Remove the `generatePersonInsights` import and call (line 110). Initialize insights from props:
```ts
const [insights, setInsights] = useState<Insight[]>(propInsights || []);
```

Remove the `useEffect` line that calls `generatePersonInsights`.

- [ ] **Step 2: Make queryPersonHistory call optional with try-catch**

Wrap the `handleAsk` function's API call in try-catch:
```ts
const handleAsk = async (e: React.FormEvent) => {
  e.preventDefault();
  if (!question.trim() || isAnswering) return;
  setIsAnswering(true);
  setAnswer(null);
  try {
    const contextTexts = personDiaries.map(d => d.content);
    const result = await queryPersonHistory(person.name, contextTexts, question);
    setAnswer(result);
  } catch {
    setAnswer("AI chat requires a Gemini API key. Set VITE_GEMINI_API_KEY in your environment.");
  }
  setIsAnswering(false);
  setQuestion('');
};
```

- [ ] **Step 3: Translate Chinese UI strings**

Replace these strings in `TimeRiver.tsx`:
- `共同经历了 {person.occurrenceCount} 个瞬间` → `${person.occurrenceCount} shared moments`
- `星河静谧，暂未解析出更深层的羁绊...` → `The stars are quiet — no deeper bonds decoded yet...`
- `问问"${person.name}曾经提到过想要什么..."` → `Ask about ${person.name}...`
- `Spiro 助手 · AI 洞察` → `Spiro · AI Insights`

- [ ] **Step 4: Commit**

```bash
git add app_demo/components/TimeRiver.tsx
git commit -m "feat(TimeRiver): use static insights prop, make chat optional, translate to English"
```

---

### Task 11: Update RelationshipGraph — letter avatars + English UI

**Files:**
- Modify: `app_demo/components/RelationshipGraph.tsx`

- [ ] **Step 1: Replace image avatars with SVG letter circles**

Replace the `node.append('image')` block (lines 190-196) with:

```ts
// Letter avatar colors — deterministic by name
const avatarColors = ['#3B82F6', '#8B5CF6', '#10B981', '#F59E0B', '#EF4444', '#EC4899', '#6366F1', '#14B8A6'];
function nameColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return avatarColors[Math.abs(hash) % avatarColors.length];
}

// Background circle for letter avatar
node.append('circle')
  .attr('class', 'avatar-bg')
  .attr('r', d => (d as any).type === 'author' ? 45 : 35)
  .attr('fill', (d: any) => d.type === 'author' ? '#1E3A5F' : nameColor(d.name));

// Letter text
node.append('text')
  .attr('class', 'avatar-letter')
  .text((d: any) => d.name.charAt(0).toUpperCase())
  .attr('text-anchor', 'middle')
  .attr('dy', '0.35em')
  .attr('fill', '#fff')
  .attr('font-size', d => (d as any).type === 'author' ? '28px' : '22px')
  .attr('font-weight', '700')
  .style('pointer-events', 'none');
```

- [ ] **Step 2: Translate Chinese UI strings**

Replace these strings:
- `name: '我'` → `name: 'Me'`
- `记忆` (in tooltip) → `memories`
- `记忆操作` → `Actions`
- `探索 Spiro` → `Explore Spiro`
- `编辑档案` → `Edit Profile`

- [ ] **Step 3: Remove the image import/usage for the "me" node**

In the nodes array creation, remove the `avatar` field from the "me" node:
```ts
const nodes = [
  { id: 'me', name: 'Me', type: 'author' },
  ...people.map(p => ({ ...p, type: 'person' }))
];
```

- [ ] **Step 4: Commit**

```bash
git add app_demo/components/RelationshipGraph.tsx
git commit -m "feat(RelationshipGraph): replace image avatars with letter circles, translate to English"
```

---

## Chunk 4: Generate Initial Demo Data

### Task 12: Generate initial static data from existing outputs

**Files:**
- Create: `app_demo/data/people.json`
- Create: `app_demo/data/diaries.json`
- Create: `app_demo/data/life-topics.json`
- Create: `app_demo/data/insights.json`
- Create: `app_demo/data/meta.json`

- [ ] **Step 1: Run the merge script against existing output/**

```bash
python scripts/export_demo_data.py --input-dir output --output-dir app_demo/data
```

Note: Existing outputs use the old Chinese schema. The script handles the old `event_cards` key as fallback. The data will have Chinese content — this is acceptable for initial demo; re-running tasks with new prompts will produce English data.

- [ ] **Step 2: Verify the generated files look reasonable**

```bash
python -c "
import json
for f in ['people', 'diaries', 'life-topics', 'insights']:
    data = json.load(open(f'app_demo/data/{f}.json'))
    if isinstance(data, list):
        print(f'{f}.json: {len(data)} items')
    else:
        print(f'{f}.json: {len(data)} keys')
"
```

- [ ] **Step 3: Verify the demo starts without errors**

```bash
cd app_demo && npm install && npm run dev
```

Expected: App loads with real data, no Gemini API errors on startup.

- [ ] **Step 4: Commit all generated data**

```bash
git add app_demo/data/
git commit -m "feat: add initial static demo data generated from task outputs"
```

---

## Task Dependency Summary

```
Task 1-4 (prompts)     → independent, can be parallel
Task 5 (base.py)       → independent
Task 6 (merge script)  → independent
Task 7 (Makefile)       → depends on Task 6
Task 8 (types.ts)      → independent
Task 9 (App.tsx)        → depends on Task 8, Task 12 (data files exist)
Task 10 (TimeRiver)    → depends on Task 8, Task 9 (insights prop)
Task 11 (RelGraph)     → depends on Task 8
Task 12 (gen data)     → depends on Task 6
```

Optimal execution order: Tasks 1-6, 8 in parallel → Task 7, 11 → Task 12 → Task 9 → Task 10
