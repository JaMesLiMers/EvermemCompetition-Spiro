# EverMemOS Competition — Agent Memory Analysis

AI Agent 驱动的记忆分析系统。通过 [EverMemOS](https://github.com/anthropics/evermemos) 存储和检索对话记忆，利用 [opencode](https://opencode.ai) + Claude Sonnet 4.6 进行智能分析。

## 架构概览

```
data/*.json           原始对话事件数据
    │
    ▼
pipeline/             数据预处理
  convert_to_gcf.py     → 转换为 GroupChatFormat
    │
    ▼
EverMemOS/            记忆存储引擎 (Docker)
  MongoDB + Elasticsearch + Milvus + Redis
    │
    ▼
mcp_server/           MCP Server (记忆查询桥梁)
  server.py             → search_memory / get_memories / store_message / ...
    │
    ▼
agent/                分析任务
  cli.py                → opencode run + Claude Sonnet 4.6
  tasks/                → relationships / profiling / timeline / suggestions
    │
    ▼
output/               分析结果 (.md)
```

## 目录结构

```
.
├── agent/                  # AI Agent 分析模块
│   ├── cli.py              #   CLI 入口，调用 opencode run 执行分析
│   ├── config.py           #   AgentConfig (从环境变量读取配置)
│   ├── setup_mcp.py        #   MCP 配置校验
│   └── tasks/              #   4 种分析任务
│       ├── base.py         #     BaseTask 基类
│       ├── relationships.py#     人际关系分析
│       ├── profiling.py    #     用户画像分析
│       ├── timeline.py     #     时间线分析
│       └── suggestions.py  #     智能建议
├── pipeline/               # 数据预处理管道
│   ├── convert_to_gcf.py   #   转换原始数据 → GroupChatFormat
│   ├── transcript_parser.py#   对话文本解析器
│   └── extract_transcript.py#  音频转录提取
├── mcp_server/             # MCP Server (EverMemOS ↔ Agent 桥梁)
│   └── server.py           #   5 个 MCP tools: search/get/store/delete/meta
├── shared/                 # 共享模块
│   └── evermemos_api.py    #   EverMemOS REST API 异步客户端
├── EverMemOS/              # EverMemOS 服务 (git submodule)
├── opencode/               # opencode CLI 源码 (git submodule)
├── data/                   # 原始数据集
│   └── basic_events_79ef7f17.json
├── tests/                  # 测试
├── opencode.json           # opencode 配置 (provider + MCP)
├── pyproject.toml          # Python 项目配置
├── Makefile                # 一键操作命令
└── .env                    # 环境变量 (不提交)
```

## 快速开始

### 前置条件

- Docker & Docker Compose
- Python >= 3.10
- [opencode CLI](https://opencode.ai) (`npm i -g @anthropic-ai/opencode` 或 `curl -fsSL https://opencode.ai/install | bash`)

### 1. 初始化

```bash
make init
```

编辑 `.env`，填入 API Key：

```bash
# .env
AGENT_MODEL=anthropic/claude-sonnet-4-6
EVERMEMOS_BASE_URL=http://localhost:1995
OPENCODE_API_KEY=your-api-key-here
```

### 2. 部署服务

```bash
make deploy
```

启动 Docker 基础设施 (Redis/MongoDB/Elasticsearch/Milvus) + EverMemOS 服务 + arq Worker。

验证服务状态：

```bash
make status
```

### 3. 准备数据

将原始事件数据转换为 GroupChatFormat：

```bash
make convert-gcf INPUT=data/basic_events_79ef7f17.json
# 可选参数: LIMIT=10 (限制转换数量)
```

### 4. 灌入数据

```bash
make ingest-gcf
# 可选参数: GCF_DIR=data/gcf/ API_URL=http://localhost:1995/api/v1/memories
```

### 5. 运行分析

```bash
# 人际关系分析
make run-task TASK=relationships USER_ID=79ef7f17-9d24-4a85-a6fe-de7d060bc090

# 用户画像
make run-task TASK=profiling USER_ID=79ef7f17-9d24-4a85-a6fe-de7d060bc090

# 时间线
make run-task TASK=timeline USER_ID=79ef7f17-9d24-4a85-a6fe-de7d060bc090

# 智能建议
make run-task TASK=suggestions USER_ID=79ef7f17-9d24-4a85-a6fe-de7d060bc090
```

可选参数：

| 参数 | 适用任务 | 说明 |
|------|----------|------|
| `FOCUS_PERSON=xxx` | relationships | 重点分析某人的关系 |
| `START_DATE=2024-01-01` | timeline | 起始日期 |
| `END_DATE=2024-12-31` | timeline | 结束日期 |
| `KEYWORDS="k1 k2"` | timeline | 关键词过滤 |

分析结果保存在 `output/` 目录下。

### 6. 停止服务

```bash
make stop
```

## 完整实验流程 (从零开始)

```bash
make init                  # 初始化环境
make deploy                # 启动所有服务
make status                # 确认服务就绪

make convert-gcf INPUT=data/basic_events_79ef7f17.json LIMIT=10   # 转换前 10 个事件
make ingest-gcf            # 灌入 GCF 数据

make run-task TASK=relationships USER_ID=79ef7f17-9d24-4a85-a6fe-de7d060bc090
make run-task TASK=profiling    USER_ID=79ef7f17-9d24-4a85-a6fe-de7d060bc090
make run-task TASK=timeline     USER_ID=79ef7f17-9d24-4a85-a6fe-de7d060bc090
make run-task TASK=suggestions  USER_ID=79ef7f17-9d24-4a85-a6fe-de7d060bc090

make stop                  # 清理
```

## 配置说明

### 环境变量 (`.env`)

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `AGENT_MODEL` | opencode 使用的模型 | `anthropic/claude-sonnet-4-6` |
| `EVERMEMOS_BASE_URL` | EverMemOS API 地址 | `http://localhost:1995` |
| `OPENCODE_API_KEY` | API Key (通过 uniapi 代理) | 无 |

### opencode 配置 (`opencode.json`)

```json
{
  "provider": {
    "anthropic": {
      "options": {
        "apiKey": "{env:OPENCODE_API_KEY}",
        "baseURL": "https://api.uniapi.io/claude/v1"
      },
      "models": {
        "claude-sonnet-4-6": { "name": "Claude Sonnet 4.6" }
      }
    }
  },
  "mcp": {
    "evermemos": {
      "type": "local",
      "command": ["python", "-m", "mcp_server.server"]
    }
  }
}
```

- `provider.anthropic`: 通过 uniapi 代理访问 Claude API
- `mcp.evermemos`: 自动启动 MCP Server，Agent 可通过 MCP tools 查询 EverMemOS 记忆

### MCP Tools

Agent 在分析时可通过 MCP 调用以下工具：

| Tool | 说明 |
|------|------|
| `search_memory` | 搜索记忆 (keyword/vector/hybrid/rrf/agentic) |
| `get_memories` | 按类型获取记忆 (episodic/profile/foresight/event_log) |
| `store_message` | 存入新消息 |
| `get_conversation_meta` | 获取对话元数据 |
| `delete_memories` | 删除记忆 |

## 基础设施

Docker 服务 (通过 `EverMemOS/docker-compose.yaml`)：

| 服务 | 端口 | 用途 |
|------|------|------|
| Redis | 6379 | 缓存 + 任务队列 |
| MongoDB | 27017 | 文档存储 |
| Elasticsearch | 19200 | 全文检索 |
| Milvus | 19530 | 向量检索 |
| EverMemOS | 1995 | 记忆管理 API |

## 开发

```bash
pip install -e .           # 安装开发依赖
python -m pytest tests/    # 运行测试
make clean                 # 清理缓存和临时文件
```

## 所有 Make 命令

```bash
make help          # 显示所有可用命令
make init          # 一键初始化：子模块 + 依赖 + env 模板
make deploy        # 一键部署：Docker + EverMemOS + Worker
make stop          # 停止所有服务
make status        # 检查服务状态
make add-memory    # 存入单条记忆
make convert-gcf   # 转换数据为 GroupChatFormat
make ingest-gcf    # 灌入 GCF 文件到 EverMemOS
make run-task      # 运行分析任务
make clean         # 清理临时文件
```
