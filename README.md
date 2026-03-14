# EverMemOS Competition — Agent Memory Analysis

AI Agent 驱动的记忆分析系统。通过 [EverMemOS](https://github.com/anthropics/evermemos) 存储和检索对话记忆，利用 [opencode](https://opencode.ai) + Claude Sonnet 4.6 进行智能分析。

## 架构概览

```
data/*.json           原始对话事件数据 (832 events)
    │
    ▼
pipeline/             数据预处理
  generate_speaker_mapping.py → LLM 批量推断说话人角色 (gpt-4o-mini)
  convert_to_gcf.py           → 转换为 GroupChatFormat + 说话人标签丰富
    │
    ▼
data/gcf/             GCF 文件 (3089 groups, 141K messages)
data/gcf_all.json     合并后的单文件
    │
    ▼
pipeline/
  ingest_gcf.py       → 异步批量灌入 EverMemOS
    │
    ▼
EverMemOS/            记忆存储引擎 (Docker)
  MongoDB + Elasticsearch + Milvus + Redis
    │
    ▼
agent/                分析任务 (JSON 输出)
  cli.py                → opencode run + Claude Sonnet 4.6
  tasks/                → relationships / profiling / timeline / suggestions / event_cards
    │
    ▼
output/               分析结果 (.json)
```

## 目录结构

```
.
├── agent/                  # AI Agent 分析模块
│   ├── cli.py              #   CLI 入口，调用 opencode run 执行分析
│   ├── config.py           #   AgentConfig (从环境变量读取配置)
│   ├── setup_mcp.py        #   MCP 配置校验
│   └── tasks/              #   5 种分析任务 (JSON 输出)
│       ├── base.py         #     BaseTask 基类
│       ├── relationships.py#     人际关系分析
│       ├── profiling.py    #     用户画像分析
│       ├── timeline.py     #     时间线分析
│       ├── suggestions.py  #     智能建议
│       └── event_cards.py  #     事件卡片生成
├── pipeline/               # 数据预处理管道
│   ├── generate_speaker_mapping.py  # LLM 批量生成说话人角色映射
│   ├── convert_to_gcf.py   #   转换原始数据 → GroupChatFormat
│   ├── ingest_gcf.py       #   异步批量灌入 EverMemOS
│   ├── transcript_parser.py#   对话文本解析器
│   └── extract_transcript.py#  音频转录提取
├── mcp_server/             # MCP Server (EverMemOS ↔ Agent 桥梁)
│   └── server.py           #   5 个 MCP tools: search/get/store/delete/meta
├── shared/                 # 共享模块
│   └── evermemos_api.py    #   EverMemOS REST API 异步客户端
├── EverMemOS/              # EverMemOS 服务 (git submodule)
├── opencode/               # opencode CLI 源码 (git submodule)
├── data/                   # 数据
│   ├── basic_events_79ef7f17.json  # 原始数据集 (832 events, 含嵌入的说话人角色映射)
│   └── gcf_all.json                # GCF 合并文件
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

#### 3a. 生成说话人角色映射

使用 gpt-4o-mini 为每个事件的说话人推断具体角色（如 "说话人1" → "产品经理"）：

```bash
make generate-speaker-mappings INPUT=data/basic_events_79ef7f17.json
# 可选参数: MODEL=gpt-4o-mini  CONCURRENCY=10  DRY_RUN=1
```

输出 `data/speaker_mappings.json`，包含每个事件的说话人角色映射。支持断点续传（已处理的事件会跳过），使用 `--force` 强制重新生成。

#### 3b. 转换为 GCF

将原始事件数据转换为 GroupChatFormat，自动应用事件中嵌入的说话人角色映射：

```bash
make convert-gcf INPUT=data/basic_events_79ef7f17.json
# 可选参数: LIMIT=10  SPLIT_FRAGS=8  SPLIT_TURNS=100
```

### 4. 灌入数据

```bash
make ingest-gcf
# 可选参数: GCF_DIR=data/gcf/  API_URL=http://localhost:1995/api/v1/memories  CONCURRENCY=5
```

异步并发灌入，带双进度条（文件级 + 消息级），默认并发度 5。

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

# 事件卡片
make run-task TASK=event_cards USER_ID=79ef7f17-9d24-4a85-a6fe-de7d060bc090
```

可选参数：

| 参数 | 适用任务 | 说明 |
|------|----------|------|
| `FOCUS_PERSON=xxx` | relationships | 重点分析某人的关系 |
| `START_DATE=2024-01-01` | timeline | 起始日期 |
| `END_DATE=2024-12-31` | timeline | 结束日期 |
| `KEYWORDS="k1 k2"` | timeline | 关键词过滤 |

分析结果保存在 `output/` 目录下（JSON 格式，包含 metadata 信封）。

### 6. 停止服务

```bash
make stop
```

## 完整实验流程 (从零开始)

```bash
make init                  # 初始化环境
make deploy                # 启动所有服务
make status                # 确认服务就绪

# 数据预处理
make generate-speaker-mappings INPUT=data/basic_events_79ef7f17.json
make convert-gcf INPUT=data/basic_events_79ef7f17.json
make ingest-gcf            # 灌入 GCF 数据

# 运行全部分析任务
make run-task TASK=relationships USER_ID=79ef7f17-9d24-4a85-a6fe-de7d060bc090
make run-task TASK=profiling    USER_ID=79ef7f17-9d24-4a85-a6fe-de7d060bc090
make run-task TASK=timeline     USER_ID=79ef7f17-9d24-4a85-a6fe-de7d060bc090
make run-task TASK=suggestions  USER_ID=79ef7f17-9d24-4a85-a6fe-de7d060bc090
make run-task TASK=event_cards  USER_ID=79ef7f17-9d24-4a85-a6fe-de7d060bc090

make stop                  # 清理
```

## 说话人角色推断

原始数据中大量说话人标签是匿名的（如 "说话人1/女"、"未知参与者A"）。`generate_speaker_mapping.py` 通过以下方式解决：

1. 将每个事件的对话内容（含标题和类型）发送给 gpt-4o-mini
2. 模型根据对话上下文推断每个说话人的具体角色
3. 结果已嵌入 `data/basic_events_79ef7f17.json` 的 `event.object.speaker_mapping` 字段，GCF 转换时自动应用

示例映射：
- `说话人1/女` → `产品经理`
- `说话人2/男` → `后端工程师`
- `说话人1` → `丈夫`
- `未知参与者A` → `客户`

832 个事件中 765 个成功生成了具体角色标签，共 3975 个标签。

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
pip install -e ".[dev]"    # 安装开发依赖
make test                  # 运行测试
make lint                  # 代码检查
make clean                 # 清理缓存和临时文件
```

## 所有 Make 命令

```bash
make help                       # 显示所有可用命令
make init                       # 一键初始化：子模块 + 依赖 + env 模板
make deploy                     # 一键部署：Docker + EverMemOS + Worker
make stop                       # 停止所有服务
make status                     # 检查服务状态
make add-memory                 # 存入单条记忆
make generate-speaker-mappings  # LLM 批量生成说话人角色映射
make convert-gcf                # 转换数据为 GroupChatFormat
make ingest-gcf                 # 异步批量灌入 GCF 文件到 EverMemOS
make run-task                   # 运行分析任务
make lint                       # 代码检查
make test                       # 运行测试
make clean                      # 清理临时文件
```
