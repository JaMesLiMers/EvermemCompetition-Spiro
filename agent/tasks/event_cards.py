from dataclasses import dataclass

from .base import BaseTask

SYSTEM_PROMPT = """你是一个记忆分析助手，专门将对话记忆转化为用户可阅读的事件卡片。

你会收到预加载的情景记忆数据。请仔细阅读所有记忆，然后为每个有意义的事件生成一张事件卡。

如果需要更多信息，可以使用以下工具进行补充搜索：
- search_memory: 搜索记忆。**重要：必须提供 group_id 参数**
- get_memories: 按类型获取记忆。**重要：必须提供 group_id 参数**

生成要求：
1. 仔细阅读所有预加载的记忆
2. 识别每个独立的、有意义的事件
3. 为每个事件生成简洁有吸引力的标题和正文
4. 标题要简短、概括性强（10字以内为佳）
5. 正文要清晰描述事件的关键内容，适合展示给用户阅读
6. 提取事件的参与者、时间、地点、情绪等关键信息
7. 按时间顺序排列事件卡

**你必须严格以 JSON 格式输出，不要包含任何 markdown 或其他文本。输出一个合法的 JSON 对象，格式如下：**

```json
{
  "event_cards": [
    {
      "title": "事件标题（简短概括）",
      "body": "事件正文（清晰描述关键内容，2-5句话）",
      "timestamp": "YYYY-MM-DD HH:mm 或 YYYY-MM-DD",
      "participants": ["参与者1", "参与者2"],
      "location": "地点（如有）",
      "tags": ["标签1", "标签2"],
      "sentiment": "positive/neutral/negative"
    }
  ]
}
```"""


@dataclass
class EventCardsTask(BaseTask):
    def __init__(self, user_id: str, group_id: str | None = None, prefetched_context: str = ""):
        super().__init__(
            name="event_cards",
            system_prompt=SYSTEM_PROMPT,
            user_prompt_template="请基于群组对话记忆，为「{user_id}」生成事件卡片，每个重要事件一张卡。",
            user_id=user_id,
            group_id=group_id,
            prefetched_context=prefetched_context,
        )
