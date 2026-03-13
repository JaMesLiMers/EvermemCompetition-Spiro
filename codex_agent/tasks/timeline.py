from dataclasses import dataclass
from .base import BaseTask

SYSTEM_PROMPT = """你是一个记忆分析助手，专门整理事件时间线。你可以使用以下 MCP 工具：
- search_memory: 搜索记忆，支持 start_time/end_time 过滤
- get_memories: 按类型获取记忆

分析流程：
1. 使用 search_memory 按时间范围搜索相关事件
2. 如有关键词，使用关键词进一步过滤
3. 按时间顺序整理事件，标注因果关系

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
    ):
        self.start_date = start_date
        self.end_date = end_date
        self.keywords = keywords

        parts = ["请整理用户 {user_id} 的事件时间线。"]
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
        )
