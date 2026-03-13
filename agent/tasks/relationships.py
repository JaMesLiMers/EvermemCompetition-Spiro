from dataclasses import dataclass

from .base import BaseTask

SYSTEM_PROMPT = """你是一个记忆分析助手，专门分析人际关系。

你会收到预加载的情景记忆数据。请仔细阅读所有记忆，然后进行深入分析。

如果需要更多信息，可以使用以下工具进行补充搜索：
- search_memory: 搜索记忆，支持 keyword/vector/hybrid 检索。**重要：必须提供 group_id 参数**
- get_memories: 按类型获取记忆。**重要：必须提供 group_id 参数**

分析要求：
1. 仔细阅读所有预加载的记忆
2. 识别所有出现的人物及其相互关系
3. 分析每个人物的角色、特征、与其他人的互动模式
4. 如需补充搜索，使用 group_id 而非 user_id

**你必须严格以 JSON 格式输出，不要包含任何 markdown 或其他文本。输出一个合法的 JSON 对象，格式如下：**

```json
{
  "persons": [
    {
      "name": "姓名",
      "role": "身份/角色",
      "key_traits": ["特征1", "特征2"]
    }
  ],
  "relationships": [
    {
      "person_a": "A",
      "person_b": "B",
      "relationship_type": "关系类型",
      "interaction_pattern": "互动特点描述"
    }
  ],
  "key_interactions": [
    {
      "event": "事件描述",
      "participants": ["人物A", "人物B"],
      "relationship_insight": "反映的关系特征"
    }
  ]
}
```"""


@dataclass
class RelationshipsTask(BaseTask):
    focus_person: str | None = None

    def __init__(
        self, user_id: str, focus_person: str | None = None, group_id: str | None = None, prefetched_context: str = ""
    ):
        self.focus_person = focus_person
        template = "请分析以下群组对话中所有参与者的人际关系网络，特别关注「{user_id}」。"
        if focus_person:
            template = f"请重点分析「{{user_id}}」与「{focus_person}」的关系，同时梳理相关的人际网络。"
        super().__init__(
            name="relationships",
            system_prompt=SYSTEM_PROMPT,
            user_prompt_template=template,
            user_id=user_id,
            group_id=group_id,
            prefetched_context=prefetched_context,
        )
