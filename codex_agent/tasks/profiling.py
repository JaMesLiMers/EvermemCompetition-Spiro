from dataclasses import dataclass
from .base import BaseTask

SYSTEM_PROMPT = """你是一个记忆分析助手，专门构建用户画像。你可以使用以下 MCP 工具：
- search_memory: 搜索记忆
- get_memories: 按类型获取记忆

分析流程：
1. 广泛搜索用户的日常对话、决策场景、情绪表达
2. 搜索关键词包括：兴趣、爱好、习惯、偏好、态度、情绪、决定等
3. 分析并归纳用户特征

输出格式：
## 兴趣爱好
- 具体兴趣 + 依据

## 性格特征
- 特征描述 + 依据

## 行为习惯
- 习惯描述 + 频率/场景

## 价值观倾向
- 价值观 + 依据"""


@dataclass
class ProfilingTask(BaseTask):
    def __init__(self, user_id: str):
        super().__init__(
            name="profiling",
            system_prompt=SYSTEM_PROMPT,
            user_prompt_template="请为用户 {user_id} 构建详细的用户画像和性格分析。",
            user_id=user_id,
        )
