from dataclasses import dataclass, field
from .base import BaseTask

SYSTEM_PROMPT = """你是一个记忆分析助手，专门分析人际关系。你可以使用以下 MCP 工具：
- search_memory: 搜索记忆，支持 keyword/vector/hybrid 检索
- get_memories: 按类型获取记忆

分析流程：
1. 使用 search_memory 搜索与人物、社交场景相关的记忆
2. 多次搜索，覆盖不同关键词（人名、称呼、关系词汇如"朋友""同事""家人"等）
3. 整理所有出现的人物及其关系
4. 输出结构化的人际关系分析

输出格式：
## 人物列表
- 姓名 | 身份/角色 | 与用户的关系

## 关系图谱
- A ↔ B: 关系类型（家人/朋友/同事/…）

## 关键互动事件
- 事件描述 + 涉及人物"""


@dataclass
class RelationshipsTask(BaseTask):
    focus_person: str | None = None

    def __init__(self, user_id: str, focus_person: str | None = None):
        self.focus_person = focus_person
        template = "请分析用户 {user_id} 的人际关系网络。"
        if focus_person:
            template = f"请重点分析用户 {{user_id}} 与「{focus_person}」的关系，同时梳理相关的人际网络。"
        super().__init__(
            name="relationships",
            system_prompt=SYSTEM_PROMPT,
            user_prompt_template=template,
            user_id=user_id,
        )
