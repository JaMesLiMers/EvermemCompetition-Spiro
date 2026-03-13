from dataclasses import dataclass


@dataclass
class BaseTask:
    name: str
    system_prompt: str
    user_prompt_template: str
    user_id: str

    def build_prompt(self, **kwargs) -> str:
        return self.user_prompt_template.format(user_id=self.user_id, **kwargs)

    def parse_output(self, raw: str) -> str:
        return raw
