from dataclasses import dataclass

from .base import BaseTask

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
