# codex_agent/runner.py
"""TaskRunner using OpenAI Chat Completions API with tool calling.

Replaces the Codex SDK approach (which requires /v1/responses) with direct
httpx calls to /v1/chat/completions, which is universally supported.
"""
import asyncio
import json
import os

import httpx

from scripts.evermemos_api import EverMemosClient

from .config import AgentConfig
from .tasks.base import BaseTask

# Tool definitions matching the MCP server tools
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_memory",
            "description": "Search EverMemOS memories using keyword, vector, hybrid, rrf, or agentic retrieval. At least one of user_id or group_id must be provided.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query text"},
                    "user_id": {"type": "string", "description": "User ID to filter by"},
                    "group_id": {"type": "string", "description": "Group ID to filter by"},
                    "retrieve_method": {
                        "type": "string",
                        "enum": ["keyword", "vector", "hybrid", "rrf", "agentic"],
                        "description": "Retrieval method (default: keyword)",
                    },
                    "memory_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Memory types: episodic_memory, foresight, event_log",
                    },
                    "top_k": {"type": "integer", "description": "Max results (default: 40)"},
                    "start_time": {"type": "string", "description": "Start time filter (ISO format)"},
                    "end_time": {"type": "string", "description": "End time filter (ISO format)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_memories",
            "description": "Fetch EverMemOS memories by type. At least one of user_id or group_id must be provided.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User ID to filter by"},
                    "group_id": {"type": "string", "description": "Group ID to filter by"},
                    "memory_type": {
                        "type": "string",
                        "description": "Memory type: profile, episodic_memory, foresight, event_log (default: episodic_memory)",
                    },
                    "limit": {"type": "integer", "description": "Max results (default: 40)"},
                    "offset": {"type": "integer", "description": "Pagination offset (default: 0)"},
                    "start_time": {"type": "string", "description": "Start time filter"},
                    "end_time": {"type": "string", "description": "End time filter"},
                },
            },
        },
    },
]


class TaskRunner:
    def __init__(self, config: AgentConfig):
        self.config = config
        self.evermemos_url = os.environ.get("EVERMEMOS_BASE_URL", "http://localhost:1995")

    async def _execute_tool(self, client: EverMemosClient, name: str, args: dict) -> str:
        """Execute a tool call against EverMemOS and return JSON string."""
        try:
            if name == "search_memory":
                result = await client.search_memory(**args)
            elif name == "get_memories":
                result = await client.get_memories(**args)
            else:
                return json.dumps({"error": f"Unknown tool: {name}"}, ensure_ascii=False)
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    async def _run_async(self, task: BaseTask) -> str:
        """Run the task with tool-calling loop."""
        evermemos = EverMemosClient(self.evermemos_url)
        http = httpx.AsyncClient(timeout=120.0)

        messages = [
            {"role": "system", "content": task.system_prompt},
            {"role": "user", "content": task.build_prompt()},
        ]

        url = f"{self.config.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        try:
            for _round in range(20):  # max 20 tool-calling rounds
                payload = {
                    "model": self.config.model,
                    "messages": messages,
                    "tools": TOOLS,
                    "temperature": 0.3,
                }
                resp = await http.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()

                choice = data["choices"][0]
                msg = choice["message"]
                messages.append(msg)

                # If no tool calls, we're done
                if not msg.get("tool_calls"):
                    return msg.get("content", "")

                # Execute each tool call
                print(f"  [Round {_round + 1}] LLM requested {len(msg['tool_calls'])} tool call(s)")
                for tc in msg["tool_calls"]:
                    fn = tc["function"]
                    tool_name = fn["name"]
                    tool_args = json.loads(fn["arguments"]) if isinstance(fn["arguments"], str) else fn["arguments"]
                    print(f"    → {tool_name}({json.dumps(tool_args, ensure_ascii=False)[:120]})")

                    tool_result = await self._execute_tool(evermemos, tool_name, tool_args)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": tool_result,
                    })

            return messages[-1].get("content", "[max rounds reached]")

        finally:
            await evermemos.close()
            await http.aclose()

    def run(self, task: BaseTask) -> str:
        return asyncio.run(self._run_async(task))
