from dataclasses import dataclass

from .base import BaseTask

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
