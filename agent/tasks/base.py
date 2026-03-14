from dataclasses import dataclass


@dataclass
class BaseTask:
    name: str
    system_prompt: str
    user_prompt_template: str
    user_id: str
    group_id: str | None = None
    prefetched_context: str = ""

    def build_prompt(self, **kwargs) -> str:
        prompt = self.user_prompt_template.format(user_id=self.user_id, **kwargs)
        if self.prefetched_context:
            prompt = f"{prompt}\n\n---\nBelow is pre-loaded memory data. Analyze based on this data:\n\n{self.prefetched_context}"
        return prompt

    def parse_output(self, raw: str) -> str:
        return raw
