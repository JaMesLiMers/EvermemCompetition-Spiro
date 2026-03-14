from dataclasses import dataclass

from .base import BaseTask

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
