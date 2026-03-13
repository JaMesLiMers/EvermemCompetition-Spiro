# Makefile 项目规范化与一键操作 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 统一 Makefile 实现项目初始化、env 配置、EverMemOS 部署、memory 操作和 task 运行的一键执行。

**Architecture:** 单一 Makefile 作为所有操作的入口，通过 shell 内联逻辑处理健康检查、服务管理等。三个 `.env.example` 模板文件分别服务根目录（Codex Agent）、EverMemOS、DataExtraction。

**Tech Stack:** GNU Make, Bash, curl, docker-compose, Python 3.10+

**Spec:** `docs/superpowers/specs/2026-03-14-makefile-standardization-design.md`

---

## Chunk 1: 项目规范化（.env.example + .gitignore + pyproject.toml）

### Task 1: 创建根目录 .env.example

**Files:**
- Create: `.env.example`

- [ ] **Step 1: Create `.env.example`**

```
# Codex Agent 配置
OPENAI_BASE_URL=https://your-uniapi.com/v1
OPENAI_API_KEY=sk-your-key-here
CODEX_MODEL=gpt-4o
CODEX_BIN=.codex-bin/codex
CODEX_HOME=.codex-local
EVERMEMOS_BASE_URL=http://localhost:1995
```

- [ ] **Step 2: Commit**

```bash
git add .env.example
git commit -m "chore: add root .env.example template for Codex Agent config"
```

### Task 2: 创建 EverMemOS/.env.example

**Files:**
- Create: `EverMemOS/.env.example`

- [ ] **Step 1: Create `EverMemOS/.env.example`**

```
# =====================================================
# EverMemOS Configuration
# =====================================================
# 你只需要填写下面标记为 sk-your-xxx-key 的 KEY 即可启动

# ===================
# LLM Configuration (UniAPI)
# ===================
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://your-uniapi.com/v1
LLM_API_KEY=sk-your-llm-key
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=16384

# ===================
# Vectorize (Embedding) - 硅基流动
# ===================
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

# Fallback - 禁用
VECTORIZE_FALLBACK_PROVIDER=none
VECTORIZE_FALLBACK_API_KEY=
VECTORIZE_FALLBACK_BASE_URL=

# ===================
# Rerank - 硅基流动
# ===================
RERANK_PROVIDER=vllm
RERANK_API_KEY=sk-your-rerank-key
RERANK_BASE_URL=https://api.siliconflow.cn/v1/rerank
RERANK_MODEL=Qwen/Qwen3-Reranker-4B

# Fallback - 禁用
RERANK_FALLBACK_PROVIDER=none
RERANK_FALLBACK_API_KEY=
RERANK_FALLBACK_BASE_URL=

# Common settings
RERANK_TIMEOUT=30
RERANK_MAX_RETRIES=3
RERANK_BATCH_SIZE=10
RERANK_MAX_CONCURRENT=5

# ===================
# Redis
# ===================
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=8
REDIS_SSL=false

# ===================
# MongoDB
# ===================
MONGODB_HOST=localhost
MONGODB_PORT=27017
MONGODB_USERNAME=admin
MONGODB_PASSWORD=memsys123
MONGODB_DATABASE=memsys
MONGODB_URI_PARAMS=socketTimeoutMS=15000&authSource=admin

# ===================
# Elasticsearch (端口 19200 是 docker-compose 的自定义映射)
# ===================
ES_HOSTS=http://localhost:19200
ES_USERNAME=
ES_PASSWORD=
ES_VERIFY_CERTS=false
SELF_ES_INDEX_NS=memsys

# ===================
# Milvus
# ===================
MILVUS_HOST=localhost
MILVUS_PORT=19530
SELF_MILVUS_COLLECTION_NS=memsys

# ===================
# API Server
# ===================
API_BASE_URL=http://localhost:1995

# ===================
# Environment
# ===================
LOG_LEVEL=INFO
ENV=dev
PYTHONASYNCIODEBUG=1
MEMORY_LANGUAGE=zh
```

- [ ] **Step 2: Commit**

```bash
git add EverMemOS/.env.example
git commit -m "chore: add EverMemOS .env.example template"
```

### Task 3: 创建 DataExtraction/.env.example

**Files:**
- Create: `DataExtraction/.env.example`

- [ ] **Step 1: Create `DataExtraction/.env.example`**

```
# 数据提取配置（用于音频转录）
# 注意：当前 extract_transcript.py 仅实际使用 LLM_API_KEY，其余为预留字段
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://your-uniapi.com/v1
LLM_API_KEY=sk-your-key-here
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=16384
```

- [ ] **Step 2: Commit**

```bash
git add DataExtraction/.env.example
git commit -m "chore: add DataExtraction .env.example template"
```

### Task 4: 更新 .gitignore 和 pyproject.toml

**Files:**
- Modify: `.gitignore:216` — 在末尾追加项目特有排除项
- Modify: `pyproject.toml` — 补全依赖

- [ ] **Step 1: 在 `.gitignore` 末尾追加项目特有排除项**

在现有内容末尾添加：

```
# EverMemOS runtime
.evermemos.pid
logs/

# Ingestion progress
scripts/ingestion_progress.json
```

注意：`.env` 已在 line 138 被排除，无需重复。

- [ ] **Step 2: 更新 `pyproject.toml` 依赖**

```toml
[project]
name = "codex-agent"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "httpx>=0.27",
    "mcp>=1.0",
]

[project.scripts]
codex-agent = "codex_agent.cli:main"

[tool.setuptools.packages.find]
include = ["codex_agent*", "mcp_server*", "scripts*"]
```

- [ ] **Step 3: Commit**

```bash
git add .gitignore pyproject.toml
git commit -m "chore: update gitignore and add missing dependencies to pyproject.toml"
```

---

## Chunk 2: Makefile 重写

### Task 5: 重写 Makefile — 完整文件

**Files:**
- Modify: `Makefile` — 完全重写

- [ ] **Step 1: 写完整 Makefile**

将以下内容写入 `Makefile`（完全覆盖原内容）：

```makefile
.PHONY: help init init-env deploy stop status add-memory ingest-data run-task clean codex-bin codex-config

PROJECT_DIR := $(shell pwd)
CODEX_BIN_DIR := $(PROJECT_DIR)/.codex-bin
CODEX_BIN := $(CODEX_BIN_DIR)/codex
CODEX_HOME := $(PROJECT_DIR)/.codex-local
CONFIG_FILE := $(CODEX_HOME)/config.toml
EVERMEMOS_PID := $(PROJECT_DIR)/.evermemos.pid
EVERMEMOS_URL ?= http://localhost:1995

help: ## 显示所有可用命令
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

init: ## 一键初始化：子模块 + 依赖 + Codex + env 模板
	@echo "==> 拉取 git 子模块..."
	@git submodule update --init --recursive
	@echo "==> 安装 Python 依赖..."
	@pip install -e . 2>/dev/null || true
	@pip install -e codex/sdk/python/ 2>/dev/null || true
	@$(MAKE) codex-bin
	@$(MAKE) codex-config
	@$(MAKE) init-env
	@echo ""
	@echo "✓ 初始化完成！请编辑以下 .env 文件填入你的 API Key："
	@echo "  - .env                  (Codex Agent)"
	@echo "  - EverMemOS/.env        (EverMemOS 服务)"
	@echo "  - DataExtraction/.env   (数据提取)"

init-env: ## 生成 .env 模板文件（已存在则跳过）
	@for target in .env EverMemOS/.env DataExtraction/.env; do \
		if [ -f "$$target" ]; then \
			echo "  SKIP $$target (已存在)"; \
		else \
			example="$$(dirname $$target)/.env.example"; \
			if [ "$$example" = "./.env.example" ]; then example=".env.example"; fi; \
			if [ -f "$$example" ]; then \
				cp "$$example" "$$target"; \
				echo "  CREATE $$target"; \
			else \
				echo "  WARN 未找到 $$example 模板"; \
			fi; \
		fi; \
	done

codex-bin: $(CODEX_BIN) ## 下载 Codex binary

$(CODEX_BIN):
	@echo "==> 下载 Codex binary..."
	@mkdir -p $(CODEX_BIN_DIR)
	@npm pack @openai/codex --pack-destination $(CODEX_BIN_DIR) 2>/dev/null
	@cd $(CODEX_BIN_DIR) && tar xzf openai-codex-*.tgz --strip-components=1 && rm -f openai-codex-*.tgz
	@if [ -f "$(CODEX_BIN_DIR)/bin/codex" ]; then \
		ln -sf $(CODEX_BIN_DIR)/bin/codex $(CODEX_BIN); \
	elif [ -f "$(CODEX_BIN_DIR)/bin/codex.js" ]; then \
		echo '#!/bin/sh' > $(CODEX_BIN) && echo 'exec node "$(CODEX_BIN_DIR)/bin/codex.js" "$$@"' >> $(CODEX_BIN) && chmod +x $(CODEX_BIN); \
	else \
		echo '#!/bin/sh' > $(CODEX_BIN) && echo 'exec npx -y @openai/codex "$$@"' >> $(CODEX_BIN) && chmod +x $(CODEX_BIN); \
	fi
	@echo "  Codex binary: $(CODEX_BIN)"

codex-config: $(CONFIG_FILE) ## 生成 Codex MCP 配置

$(CONFIG_FILE):
	@echo "==> 生成 Codex 配置..."
	@mkdir -p $(CODEX_HOME)
	@printf '[mcp_servers.evermemos]\ncommand = "python"\nargs = ["-m", "mcp_server.server"]\n' > $(CONFIG_FILE)
	@echo "  Config: $(CONFIG_FILE)"

deploy: ## 一键部署：启动基础设施 + EverMemOS 服务
	@echo "==> 启动基础设施 (docker-compose)..."
	@docker-compose -f EverMemOS/docker-compose.yaml up -d
	@echo "==> 等待服务就绪..."
	@timeout=120; elapsed=0; \
	while [ $$elapsed -lt $$timeout ]; do \
		all_ready=true; \
		for port in 6379 27017 19200 19530; do \
			if ! curl -sf -o /dev/null --connect-timeout 1 http://localhost:$$port 2>/dev/null && \
			   ! (echo > /dev/tcp/localhost/$$port) 2>/dev/null; then \
				all_ready=false; \
				break; \
			fi; \
		done; \
		if $$all_ready; then \
			echo "  ✓ 所有基础设施已就绪"; \
			break; \
		fi; \
		sleep 2; \
		elapsed=$$((elapsed + 2)); \
		printf "\r  等待中... %ds/%ds" $$elapsed $$timeout; \
	done; \
	if [ $$elapsed -ge $$timeout ]; then \
		echo "\n  ✗ 超时！部分服务未就绪，请检查 docker-compose 日志"; \
		exit 1; \
	fi
	@echo "==> 启动 EverMemOS 服务..."
	@mkdir -p logs
	@cd EverMemOS && nohup uv run python src/run.py > ../logs/evermemos.log 2>&1 & echo $$! > $(EVERMEMOS_PID)
	@sleep 3
	@if curl -sf $(EVERMEMOS_URL)/api/v1/memories/conversation-meta > /dev/null 2>&1; then \
		echo "  ✓ EverMemOS 已启动 (PID: $$(cat $(EVERMEMOS_PID)))"; \
	else \
		echo "  ⚠ EverMemOS 进程已启动但 API 尚未响应，请检查 logs/evermemos.log"; \
	fi

stop: ## 停止所有服务
	@echo "==> 停止 EverMemOS..."
	@if [ -f $(EVERMEMOS_PID) ]; then \
		kill $$(cat $(EVERMEMOS_PID)) 2>/dev/null && echo "  ✓ EverMemOS 已停止" || echo "  进程已不存在"; \
		rm -f $(EVERMEMOS_PID); \
	else \
		echo "  未找到 PID 文件，跳过"; \
	fi
	@echo "==> 停止基础设施..."
	@docker-compose -f EverMemOS/docker-compose.yaml down
	@echo "  ✓ 所有服务已停止"

status: ## 检查所有服务状态
	@echo "=== 服务状态 ==="
	@for svc in "Redis:6379" "MongoDB:27017" "Elasticsearch:19200" "Milvus:19530"; do \
		name=$$(echo $$svc | cut -d: -f1); \
		port=$$(echo $$svc | cut -d: -f2); \
		if (echo > /dev/tcp/localhost/$$port) 2>/dev/null; then \
			printf "  \033[32m✓\033[0m %-20s localhost:%s\n" "$$name" "$$port"; \
		else \
			printf "  \033[31m✗\033[0m %-20s localhost:%s\n" "$$name" "$$port"; \
		fi; \
	done
	@if [ -f $(EVERMEMOS_PID) ] && kill -0 $$(cat $(EVERMEMOS_PID)) 2>/dev/null; then \
		printf "  \033[32m✓\033[0m %-20s %s (PID: %s)\n" "EverMemOS" "$(EVERMEMOS_URL)" "$$(cat $(EVERMEMOS_PID))"; \
	else \
		printf "  \033[31m✗\033[0m %-20s %s\n" "EverMemOS" "$(EVERMEMOS_URL)"; \
	fi

add-memory: ## 存入单条记忆 (CONTENT="..." SENDER="user1" [GROUP_ID=...])
	@if [ -z "$(CONTENT)" ] || [ -z "$(SENDER)" ]; then \
		echo "用法: make add-memory CONTENT=\"消息内容\" SENDER=\"发送者ID\""; \
		echo "可选: GROUP_ID=\"群组ID\" GROUP_NAME=\"群组名\""; \
		exit 1; \
	fi
	@curl -sf -X POST $(EVERMEMOS_URL)/api/v1/memories \
		-H "Content-Type: application/json" \
		-d "{\"message_id\":\"$$(uuidgen 2>/dev/null || python3 -c 'import uuid;print(uuid.uuid4())')\",\"create_time\":\"$$(date -u +%Y-%m-%dT%H:%M:%S+00:00)\",\"sender\":\"$(SENDER)\",\"sender_name\":\"$(SENDER)\",\"content\":\"$(CONTENT)\",\"role\":\"user\"}" \
		| python3 -m json.tool 2>/dev/null || echo "  ✗ 请求失败，请确认 EverMemOS 是否正在运行"

ingest-data: ## 批量灌入数据 (INPUT=path/to/data.json [LIMIT=N] [RESUME=1] [API_URL=...])
	@if [ -z "$(INPUT)" ]; then \
		echo "用法: make ingest-data INPUT=Dataset/basic_events_79ef7f17.json"; \
		echo "可选: LIMIT=10  RESUME=1  API_URL=http://localhost:1995"; \
		exit 1; \
	fi
	python -m scripts.ingest_data --input $(INPUT) \
		$(if $(API_URL),--api-url $(API_URL)) \
		$(if $(LIMIT),--limit $(LIMIT)) \
		$(if $(RESUME),--resume)

run-task: ## 运行分析任务 (TASK=relationships|profiling|timeline|suggestions USER_ID=xxx)
	@if [ -z "$(TASK)" ] || [ -z "$(USER_ID)" ]; then \
		echo "用法: make run-task TASK=relationships USER_ID=user123"; \
		echo "任务类型: relationships | profiling | timeline | suggestions"; \
		echo "可选: FOCUS_PERSON=xxx  START_DATE=xxx  END_DATE=xxx  KEYWORDS=\"k1 k2\""; \
		exit 1; \
	fi
	python -m codex_agent.cli $(TASK) --user-id $(USER_ID) \
		$(if $(FOCUS_PERSON),--focus-person $(FOCUS_PERSON)) \
		$(if $(START_DATE),--start-date $(START_DATE)) \
		$(if $(END_DATE),--end-date $(END_DATE)) \
		$(if $(KEYWORDS),--keywords $(KEYWORDS))

clean: ## 清理构建产物和运行时文件
	rm -rf $(CODEX_BIN_DIR) $(CODEX_HOME)
	rm -f $(EVERMEMOS_PID)
	rm -f scripts/ingestion_progress.json
	find . -type d -name __pycache__ -not -path './EverMemOS/*' -not -path './codex/*' -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ 已清理"
```

关键设计决策：
- `init` 不用 prerequisite 依赖，而是在 recipe body 中按顺序调用 `$(MAKE)`，确保子模块先拉取、依赖先安装，再下载 Codex、生成 env
- `deploy` 健康检查使用 bash `/dev/tcp` 而非 `nc`，更便携
- `add-memory` 使用纯 curl + shell 命令构建 JSON（单行），不依赖 Python。可选的 GROUP_ID/GROUP_NAME 未包含在基础 curl 中以保持简洁
- `codex-config` 使用 `printf` 而非 heredoc 写入 TOML，避免 Makefile 中 heredoc 的兼容性问题

- [ ] **Step 2: 验证 Makefile 语法**

Run: `make help`
Expected: 输出所有 11 个命令（help, init, init-env, codex-bin, codex-config, deploy, stop, status, add-memory, ingest-data, run-task, clean）

- [ ] **Step 3: Commit**

```bash
git add Makefile
git commit -m "feat: rewrite Makefile with one-click init, deploy, memory and task commands"
```

---

## Chunk 3: 最终验证

### Task 6: 端到端验证

- [ ] **Step 1: 验证 `make help` 输出所有命令**

Run: `make help`
Expected: 12 个命令全部显示

- [ ] **Step 2: 验证 `make init-env` 能正确生成 .env**

Run: `make init-env`
Expected: 3 个 .env 文件被创建（或跳过，如果已存在）

- [ ] **Step 3: 验证 `make status` 正常运行（即使服务未启动）**

Run: `make status`
Expected: 显示 5 个服务状态（全部 ✗ 如果服务未启动）

- [ ] **Step 4: Final commit（如有遗留修改）**
