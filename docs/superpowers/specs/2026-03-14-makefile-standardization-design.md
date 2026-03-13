# Makefile 项目规范化与一键操作设计

## 概述

将项目的初始化、环境配置、服务部署、数据操作和任务运行统一整合到一个 Makefile 中，实现所有核心操作的一键执行。同时规范化 `.env` 管理，防止 API Key 泄露。

## 1. 项目规范化

### 1.1 .env 管理

**问题：** `DataExtraction/.env` 和 `EverMemOS/.env` 包含真实 API Key 且已被 git 追踪。

**改动：**

- 为每个 `.env` 位置创建 `.env.example` 模板（key 值用占位符）
- 更新 `.gitignore` 排除所有 `.env` 文件（保留 `.env.example`）
- `git rm --cached` 移除已追踪的 `.env` 文件
- 三个 `.env.example` 位置：
  - `.env.example` — Codex Agent 配置（OPENAI_BASE_URL、OPENAI_API_KEY、CODEX_MODEL、EVERMEMOS_BASE_URL）
  - `EverMemOS/.env.example` — 完整基础设施配置（LLM/Vectorize/Rerank key 留空，基础设施连接保持默认值对应 docker-compose）
  - `DataExtraction/.env.example` — 数据提取 LLM 配置（仅 LLM_BASE_URL、LLM_API_KEY）

### 1.2 pyproject.toml

补全实际依赖：`httpx`、`mcp` 等。

## 2. Makefile 命令设计

### 命令总览

| 命令 | 功能 |
|------|------|
| `make help` | 显示所有可用命令（自动从注释生成） |
| `make init` | 一键初始化项目：拉取子模块 → 安装 Python 依赖 → 下载 Codex binary → 生成 .env 模板 |
| `make init-env` | 生成 .env 模板文件（已存在则跳过，不覆盖） |
| `make deploy` | 一键部署：docker-compose up -d → 健康检查等待 → 后台启动 EverMemOS 服务 |
| `make stop` | 停止所有服务：杀 EverMemOS 进程 + docker-compose down |
| `make status` | 检查服务状态：docker 容器 + EverMemOS API 可达性 |
| `make add-memory` | 单条消息存入：`make add-memory CONTENT="..." SENDER="user1"` |
| `make ingest-data` | 批量数据灌入：`make ingest-data INPUT=Dataset/xxx.json` |
| `make run-task` | 运行分析任务：`make run-task TASK=relationships USER_ID=xxx` |
| `make clean` | 清理构建产物 |

### 实现细节

- **`make deploy` 健康检查：** shell 循环 curl 检测各服务端口（MongoDB 27017、ES 19200、Milvus 19530、Redis 6379），超时 120 秒自动退出报错。
- **EverMemOS 后台启动：** `nohup uv run python src/run.py &`，PID 写入 `.evermemos.pid`，供 `make stop` 使用。
- **`make add-memory`：** 直接用 `curl` 调用 EverMemOS REST API `POST /api/v1/memories`，不依赖 Python 环境。需要参数 `CONTENT` 和 `SENDER`，可选 `GROUP_ID`。
- **`make ingest-data`：** 调用 `python -m scripts.ingest_data --input $(INPUT)`，支持可选参数 `LIMIT` 和 `RESUME=1`。
- **`make run-task`：** 调用 `python -m codex_agent.cli $(TASK) --user-id $(USER_ID)`，支持可选参数 `FOCUS_PERSON`、`START_DATE`、`END_DATE`、`KEYWORDS`。
- **`make init-env`：** 对每个位置检查 `.env` 是否存在，不存在则从 `.env.example` 复制，已存在则打印跳过提示。

## 3. .env.example 模板内容

### `.env.example`（根目录）

```
# Codex Agent 配置
OPENAI_BASE_URL=https://your-uniapi.com/v1
OPENAI_API_KEY=sk-your-key-here
CODEX_MODEL=gpt-4o
EVERMEMOS_BASE_URL=http://localhost:1995
```

### `EverMemOS/.env.example`

```
# LLM Configuration (UniAPI)
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://your-uniapi.com/v1
LLM_API_KEY=sk-your-llm-key
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=16384

# Vectorize (Embedding) - 硅基流动
VECTORIZE_PROVIDER=vllm
VECTORIZE_API_KEY=sk-your-vectorize-key
VECTORIZE_BASE_URL=https://api.siliconflow.cn/v1
VECTORIZE_MODEL=Qwen/Qwen3-Embedding-4B
VECTORIZE_DIMENSIONS=1024
VECTORIZE_TIMEOUT=30
VECTORIZE_MAX_RETRIES=3
VECTORIZE_BATCH_SIZE=10
VECTORIZE_MAX_CONCURRENT=5
VECTORIZE_ENCODING_FORMAT=float

VECTORIZE_FALLBACK_PROVIDER=none
VECTORIZE_FALLBACK_API_KEY=
VECTORIZE_FALLBACK_BASE_URL=

# Rerank - 硅基流动
RERANK_PROVIDER=vllm
RERANK_API_KEY=sk-your-rerank-key
RERANK_BASE_URL=https://api.siliconflow.cn/v1/rerank
RERANK_MODEL=Qwen/Qwen3-Reranker-4B

RERANK_FALLBACK_PROVIDER=none
RERANK_FALLBACK_API_KEY=
RERANK_FALLBACK_BASE_URL=

RERANK_TIMEOUT=30
RERANK_MAX_RETRIES=3
RERANK_BATCH_SIZE=10
RERANK_MAX_CONCURRENT=5

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=8
REDIS_SSL=false

# MongoDB
MONGODB_HOST=localhost
MONGODB_PORT=27017
MONGODB_USERNAME=admin
MONGODB_PASSWORD=memsys123
MONGODB_DATABASE=memsys
MONGODB_URI_PARAMS=socketTimeoutMS=15000&authSource=admin

# Elasticsearch
ES_HOSTS=http://localhost:19200
ES_USERNAME=
ES_PASSWORD=
ES_VERIFY_CERTS=false
SELF_ES_INDEX_NS=memsys

# Milvus
MILVUS_HOST=localhost
MILVUS_PORT=19530
SELF_MILVUS_COLLECTION_NS=memsys

# API Server
API_BASE_URL=http://localhost:1995

# Environment
LOG_LEVEL=INFO
ENV=dev
PYTHONASYNCIODEBUG=1
MEMORY_LANGUAGE=zh
```

### `DataExtraction/.env.example`

```
# 数据提取 LLM 配置（用于音频转录）
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://your-uniapi.com/v1
LLM_API_KEY=sk-your-key-here
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=16384
```

## 4. 文件变更清单

| 文件 | 操作 |
|------|------|
| `Makefile` | 重写，整合所有一键命令 |
| `.env.example` | 新建 |
| `EverMemOS/.env.example` | 新建 |
| `DataExtraction/.env.example` | 新建 |
| `.gitignore` | 添加 .env 排除规则 |
| `pyproject.toml` | 补全依赖 |
| `DataExtraction/.env` | git rm --cached（停止追踪，文件保留） |
| `EverMemOS/.env` | git rm --cached（停止追踪，文件保留） |
