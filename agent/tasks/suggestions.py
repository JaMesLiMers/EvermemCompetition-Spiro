from dataclasses import dataclass

from .base import BaseTask

SYSTEM_PROMPT = """你是一个记忆分析助手，专门生成主动建议和提醒。

你会收到预加载的情景记忆数据。请仔细阅读所有记忆，然后生成有用的建议。

如果需要更多信息，可以使用以下工具进行补充搜索：
- search_memory: 搜索记忆。**重要：必须提供 group_id 参数**
- get_memories: 按类型获取记忆（特别关注 foresight 类型）。**重要：必须提供 group_id 参数**

分析要求：
1. 仔细阅读所有预加载的记忆
2. 识别未完成事项、约定、承诺、计划
3. 识别周期性事件、生日、纪念日等
4. 评估紧急程度和重要性
5. 生成具体、可执行的建议

输出格式：
## 待跟进事项
| 优先级 | 事项 | 建议行动 | 相关上下文 |
|--------|------|----------|------------|
| 高/中/低 | 事项描述 | 建议的下一步 | 来源记忆摘要 |

## 周期性提醒
- 提醒内容 + 建议时间"""


@dataclass
class SuggestionsTask(BaseTask):
    def __init__(self, user_id: str, group_id: str | None = None, prefetched_context: str = ""):
        super().__init__(
            name="suggestions",
            system_prompt=SYSTEM_PROMPT,
            user_prompt_template="请为「{user_id}」生成主动建议和待办提醒，基于群组对话记忆。",
            user_id=user_id,
            group_id=group_id,
            prefetched_context=prefetched_context,
        )
