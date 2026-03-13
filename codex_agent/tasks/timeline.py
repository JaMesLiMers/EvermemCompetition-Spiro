from dataclasses import dataclass
from .base import BaseTask

SYSTEM_PROMPT = """你是一个记忆分析助手，专门整理事件时间线。

你会收到预加载的情景记忆数据。请仔细阅读所有记忆，然后按时间整理事件。

如果需要更多信息，可以使用以下工具进行补充搜索：
- search_memory: 搜索记忆，支持 start_time/end_time 过滤。**重要：必须提供 group_id 参数**
- get_memories: 按类型获取记忆。**重要：必须提供 group_id 参数**

分析要求：
1. 仔细阅读所有预加载的记忆
2. 按时间顺序整理每个事件
3. 标注事件之间的因果关系和关联
4. 如有关键词过滤，重点关注相关事件

输出格式：
## 事件时间线
| 日期 | 事件 | 参与者 | 备注 |
|------|------|--------|------|
| YYYY-MM-DD | 事件描述 | 相关人物 | 因果/关联 |

## 因果关系分析
- 事件A → 事件B: 关联说明"""


@dataclass
class TimelineTask(BaseTask):
    start_date: str | None = None
    end_date: str | None = None
    keywords: list[str] | None = None

    def __init__(
        self,
        user_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
        keywords: list[str] | None = None,
        group_id: str | None = None,
        prefetched_context: str = "",
    ):
        self.start_date = start_date
        self.end_date = end_date
        self.keywords = keywords

        parts = ["请整理群组对话中与「{user_id}」相关的事件时间线。"]
        if start_date or end_date:
            time_range = f"时间范围：{start_date or '不限'} 至 {end_date or '不限'}。"
            parts.append(time_range)
        if keywords:
            parts.append(f"重点关注以下关键词：{'、'.join(keywords)}。")

        super().__init__(
            name="timeline",
            system_prompt=SYSTEM_PROMPT,
            user_prompt_template=" ".join(parts),
            user_id=user_id,
            group_id=group_id,
            prefetched_context=prefetched_context,
        )
