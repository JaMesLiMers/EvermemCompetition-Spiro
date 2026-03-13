from dataclasses import dataclass

from .base import BaseTask

SYSTEM_PROMPT = """你是一个记忆分析助手，专门构建用户画像。

你会收到预加载的情景记忆数据。请仔细阅读所有记忆，然后进行深入分析。

如果需要更多信息，可以使用以下工具进行补充搜索：
- search_memory: 搜索记忆。**重要：必须提供 group_id 参数**
- get_memories: 按类型获取记忆。**重要：必须提供 group_id 参数**

分析要求：
1. 仔细阅读所有预加载的记忆
2. 从对话内容中提取人物特征、兴趣、习惯、性格等信息
3. 注意区分不同参与者的特征
4. 用具体的对话内容作为依据

输出格式：
## 兴趣爱好
- 具体兴趣 + 来源依据（引用具体记忆）

## 性格特征
- 特征描述 + 来源依据

## 行为习惯
- 习惯描述 + 频率/场景

## 价值观倾向
- 价值观 + 依据"""


@dataclass
class ProfilingTask(BaseTask):
    def __init__(self, user_id: str, group_id: str | None = None, prefetched_context: str = ""):
        super().__init__(
            name="profiling",
            system_prompt=SYSTEM_PROMPT,
            user_prompt_template="请为「{user_id}」构建详细的用户画像和性格分析，基于群组对话记忆。",
            user_id=user_id,
            group_id=group_id,
            prefetched_context=prefetched_context,
        )
