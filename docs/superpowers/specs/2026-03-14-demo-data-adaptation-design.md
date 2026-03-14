# Demo Data Adaptation Design

**Date**: 2026-03-14
**Status**: Approved
**Approach**: Adjust both task prompts and demo code (Option A — Unified Pipeline)

## Goal

Adapt the 5 task outputs (event_cards, relationships, profiling, suggestions, timeline) to feed the `app_demo/` frontend with static, pre-generated JSON data. Remove Gemini runtime dependency. Output everything in English.

---

## 1. Data File Structure

Static data lives in `app_demo/data/`, one file per concern:

```
app_demo/data/
├── people.json          # Person[]        ← relationships task
├── diaries.json         # DiaryEntry[]    ← event_cards task
├── life-topics.json     # LifeTopic[]     ← profiling task
├── insights.json        # Record<personId, Insight[]> ← suggestions task
└── meta.json            # generation timestamp, model info (optional)
```

Each file is independently importable. This allows per-task updates without touching other data.

---

## 2. Task Prompt Adjustments

All prompts switch to English output. Field names align with demo TypeScript interfaces.

### 2.1 `event_cards` → diaries.json

Output schema per item:

```json
{
  "id": "ec_001",
  "title": "Weekend Road Trip to Quzhou",
  "date": "March 10, 2026",
  "content": "2-5 sentence narrative description...",
  "peopleIds": ["the_architect", "wife"],
  "tags": ["travel", "family"],
  "sentiment": "positive"
}
```

Changes from current prompt:
- `body` → `content`
- `timestamp` → `date` (human-readable format, not ISO)
- `participants` → `peopleIds` (snake_case name references, resolved to IDs by merge script)
- Add `id` field with `ec_` prefix
- Do NOT output `audioSnippets` or `imageUrl` (filled by merge script)

### 2.2 `relationships` → people.json

Output schema per item:

```json
{
  "id": "the_architect",
  "name": "The Architect",
  "relationship": "Tech Lead & Mentor",
  "key_traits": ["analytical", "patient"]
}
```

Changes from current prompt:
- Add `id` field (snake_case of name)
- `role` → `relationship`
- **Explicit instruction**: each person appears exactly once with a unique, consistent English name. No role-based aliases (no "Husband" and "Male Partner" for the same person).
- Do NOT output `avatar`, `occurrenceCount`, `diaryIds` (computed by merge script)

### 2.3 `profiling` → life-topics.json

**Largest prompt change.** Current output (interests/traits/values/habits lists) restructured into aggregated life topics.

Output schema per item:

```json
{
  "id": "lt_001",
  "name": "Family & Nurturing",
  "gravity": 85,
  "description": "A quiet devotion to the small hands that hold tomorrow",
  "icon": "👶",
  "color": "blue"
}
```

Prompt requirements:
- Extract 5-8 life topics from memories
- `gravity`: 0-100 intensity/concern score
- `description`: one poetic sentence
- `icon`: single emoji
- `color`: must be one of `blue`, `purple`, `emerald`, `amber`

### 2.4 `suggestions` → insights.json

Output grouped by person name:

```json
{
  "The Architect": [
    {
      "id": "ins_001",
      "text": "Mentioned wanting to attend a Go conference next quarter",
      "type": "event"
    }
  ],
  "Wife": [
    {
      "id": "ins_002",
      "text": "Expressed concern about work-life balance recently",
      "type": "need"
    }
  ]
}
```

Changes from current prompt:
- Group by person instead of flat list
- Each insight has `type` constrained to: `birthday`, `event`, `personality`, `promise`, `need`
- Merge script maps person names → person IDs

### 2.5 `timeline` → No changes

Keep existing format. No direct demo view mapping. The merge script does NOT read timeline output — it is retained for standalone analysis use only.

---

## 3. Merge Script

New file: `scripts/export_demo_data.py`

Reads `output/*.json`, writes `app_demo/data/*.json`.

### Responsibilities

1. **ID unification**: Use relationships person `id` as canonical. Map event_cards `peopleIds` (names) to real IDs via normalized lowercase matching.
2. **Reverse association**: Traverse all diaries' `peopleIds`, populate each person's `diaryIds` array and compute `occurrenceCount`.
3. **Field completion**:
   - `DiaryEntry.audioSnippets` → omit entirely (field made optional in types.ts)
   - `DiaryEntry.imageUrl` → omit entirely (already optional)
   - `Person.avatar` → omit entirely (field made optional in types.ts, demo renders letter avatars)
4. **Insights remapping**: Convert `{"person_name": [...]}` → `{"person_id": [...]}` using the same name→ID mapping.
5. **Fuzzy name matching**: Normalize names (lowercase, strip "the", trim) before matching to handle minor LLM inconsistencies. Matching order: exact match → normalized match → log warning for unresolved names.
6. **Color validation**: If profiling task outputs an invalid color (not in `blue`/`purple`/`emerald`/`amber`), default to `blue`.

### What it does NOT do

- No translation (prompts already output English)
- No content generation
- No image URL generation

### Invocation

```bash
make export-demo
# or
python scripts/export_demo_data.py
```

---

## 4. Demo Code Changes

### 4.1 Data Loading

`App.tsx`:
- Remove hardcoded `INITIAL_PEOPLE` and `DIARIES` constants
- Import static JSON:
  ```ts
  import people from './data/people.json'
  import diaries from './data/diaries.json'
  import lifeTopics from './data/life-topics.json'
  import insightsData from './data/insights.json'
  ```
- Remove `useEffect` calling `analyzeLifeTopics()` — initialize state with imported `lifeTopics`
- Remove `generateDiaryBackground` call and refresh button

### 4.2 Gemini Service

- `analyzeLifeTopics` and `generatePersonInsights` no longer imported/called
- `queryPersonHistory` retained as optional feature in TimeRiver chat box — add try-catch with graceful fallback message when no API key

### 4.3 TimeRiver Changes

- Remove `generatePersonInsights` call
- Read insights from `insightsData[person.id]` (passed via props or direct import)

### 4.4 Avatar → Letter Avatars

`types.ts`: Change `avatar: string` → `avatar?: string`, change `audioSnippets: AudioSnippet[]` → `audioSnippets?: AudioSnippet[]`

`RelationshipGraph.tsx`: Replace `node.append('image')` (lines 190-196) with SVG circle + text rendering:
- Circle with deterministic color based on person name hash
- Text showing first letter of name

### 4.5 UI Internationalization

| File | Location | Chinese | English |
|---|---|---|---|
| RelationshipGraph.tsx | center node | `'我'` | `'Me'` |
| RelationshipGraph.tsx | tooltip | `记忆` | `memories` |
| RelationshipGraph.tsx | menu header | `记忆操作` | `Actions` |
| RelationshipGraph.tsx | menu item | `探索 Spiro` | `Explore Spiro` |
| RelationshipGraph.tsx | menu item | `编辑档案` | `Edit Profile` |
| TimeRiver.tsx | subtitle | `共同经历了 X 个瞬间` | `${occurrenceCount} shared moments` |
| TimeRiver.tsx | empty state | `星河静谧...` | `The stars are quiet — no deeper bonds decoded yet...` |
| TimeRiver.tsx | input placeholder | `问问"${name}曾经提到过..."` | `Ask about ${person.name}...` |

---

## 5. End-to-End Workflow

```
1. Modify 4 task prompts (English + field alignment)
          ↓
2. Run tasks → output/ generates new JSON files
          ↓
3. python scripts/export_demo_data.py
   Reads output/*.json → merge/associate/complete → writes app_demo/data/
          ↓
4. Demo imports data/*.json → static display
```

### Makefile additions

- `make export-demo` → run merge script
- `make demo` → `cd app_demo && npm run dev` (optional convenience)

### Bootstrap

For initial demo, manually convert existing `output/` data into `app_demo/data/*.json` format. Subsequent runs use `make export-demo`.

---

## 6. Known Issues & Mitigations

| Issue | Impact | Mitigation |
|---|---|---|
| Cross-task ID referencing | Data integrity | Merge script handles name→ID mapping with fuzzy match |
| `avatar` required field | Compile error | Make optional in types.ts, render letter avatars |
| `audioSnippets` required | Compile error | Make optional in types.ts, omit from data files |
| Gemini runtime dependency | Crash on load | Remove calls, use static data |
| Person deduplication | Data redundancy | Prompt instructs unique names + merge script fuzzy match |
| Hardcoded Chinese UI | Display inconsistency | English string replacements |
| Per-person insights | Missing functionality | Pre-generate in insights.json keyed by person ID |
| Invalid LifeTopic color | Rendering issue | Merge script defaults to `blue` for invalid values |
