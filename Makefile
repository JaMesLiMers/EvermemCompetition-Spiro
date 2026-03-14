SHELL := /bin/bash
.PHONY: help init init-env deploy stop status add-memory convert-gcf generate-speaker-mappings ingest-gcf run-task lint test clean

# Auto-load .env if it exists
ifneq (,$(wildcard .env))
include .env
export
endif

PROJECT_DIR := $(shell pwd)
EVERMEMOS_PID := $(PROJECT_DIR)/.evermemos.pid
WORKER_PID := $(PROJECT_DIR)/.worker.pid
EVERMEMOS_URL ?= http://localhost:1995
REQUIRED_PYTHON_MINOR := 10

help: ## 显示所有可用命令
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

init: ## 一键初始化：子模块 + 依赖 + env 模板
	@echo "==> 检查 Python 版本..."
	@python3 -c "import sys; v=sys.version_info; exit(0 if v >= (3,$(REQUIRED_PYTHON_MINOR)) else 1)" 2>/dev/null \
		&& echo "  ✓ Python $$(python3 --version)" \
		|| { echo "  ✗ 需要 Python >= 3.$(REQUIRED_PYTHON_MINOR)，当前: $$(python3 --version 2>&1)"; exit 1; }
	@echo "==> 拉取 git 子模块..."
	@git submodule update --init --recursive
	@echo "==> 安装 Python 依赖..."
	@if command -v uv &>/dev/null; then \
		uv pip install -e ".[dev]"; \
	else \
		echo "  WARN uv 未安装，使用 pip 作为后备"; \
		pip install -e ".[dev]" 2>/dev/null || true; \
	fi
	@$(MAKE) init-env
	@echo "==> 检查 opencode..."
	@if command -v opencode &>/dev/null; then \
		echo "  ✓ opencode 已安装 ($$(opencode --version))"; \
	else \
		echo "  ✗ opencode 未安装，请先安装: https://opencode.ai"; \
	fi
	@echo ""
	@echo "✓ 初始化完成！请编辑以下 .env 文件："
	@echo "  - .env                  (Agent 配置)"
	@echo "  - EverMemOS/.env        (EverMemOS 服务)"

init-env: ## 生成 .env 模板文件（已存在则跳过）
	@for target in .env EverMemOS/.env; do \
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

deploy: ## 一键部署：启动基础设施 + EverMemOS 服务
	@echo "==> 启动基础设施 (docker compose)..."
	@docker compose -f EverMemOS/docker-compose.yaml up -d
	@echo "==> 等待服务就绪..."
	@timeout=120; elapsed=0; \
	while [ $$elapsed -lt $$timeout ]; do \
		all_ready=true; \
		for port in 6379 27017 19200 19530; do \
			if ! (echo > /dev/tcp/localhost/$$port) 2>/dev/null; then \
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
		echo "\n  ✗ 超时！部分服务未就绪，请检查 docker compose 日志"; \
		exit 1; \
	fi
	@echo "==> 启动 EverMemOS 服务..."
	@mkdir -p logs
	@cd EverMemOS && nohup uv run python src/run.py > ../logs/evermemos.log 2>&1 & echo $$! > $(EVERMEMOS_PID)
	@echo "==> 启动 arq Worker（后台记忆处理）..."
	@cd EverMemOS && nohup .venv/bin/arq src.task.WorkerSettings > ../logs/worker.log 2>&1 & echo $$! > $(WORKER_PID)
	@sleep 5
	@if curl -sf $(EVERMEMOS_URL)/api/v1/memories/conversation-meta > /dev/null 2>&1; then \
		echo "  ✓ EverMemOS 已启动 (PID: $$(cat $(EVERMEMOS_PID)))"; \
	else \
		echo "  ⚠ EverMemOS 进程已启动但 API 尚未响应，请检查 logs/evermemos.log"; \
	fi
	@if kill -0 $$(cat $(WORKER_PID)) 2>/dev/null; then \
		echo "  ✓ arq Worker 已启动 (PID: $$(cat $(WORKER_PID)))"; \
	else \
		echo "  ✗ arq Worker 启动失败，请检查 logs/worker.log"; \
	fi

stop: ## 停止所有服务
	@echo "==> 停止 arq Worker..."
	@if [ -f $(WORKER_PID) ]; then \
		pid=$$(cat $(WORKER_PID)); \
		kill -TERM $$pid 2>/dev/null; \
		for i in $$(seq 1 10); do \
			kill -0 $$pid 2>/dev/null || break; \
			sleep 1; \
		done; \
		kill -0 $$pid 2>/dev/null && kill -KILL $$pid 2>/dev/null; \
		echo "  ✓ arq Worker 已停止"; \
		rm -f $(WORKER_PID); \
	else \
		echo "  未找到 PID 文件，跳过"; \
	fi
	@echo "==> 停止 EverMemOS..."
	@if [ -f $(EVERMEMOS_PID) ]; then \
		pid=$$(cat $(EVERMEMOS_PID)); \
		kill -TERM $$pid 2>/dev/null; \
		for i in $$(seq 1 10); do \
			kill -0 $$pid 2>/dev/null || break; \
			sleep 1; \
		done; \
		kill -0 $$pid 2>/dev/null && kill -KILL $$pid 2>/dev/null; \
		echo "  ✓ EverMemOS 已停止"; \
		rm -f $(EVERMEMOS_PID); \
	else \
		echo "  未找到 PID 文件，跳过"; \
	fi
	@echo "==> 停止基础设施..."
	@docker compose -f EverMemOS/docker-compose.yaml down
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
	@if [ -f $(WORKER_PID) ] && kill -0 $$(cat $(WORKER_PID)) 2>/dev/null; then \
		printf "  \033[32m✓\033[0m %-20s PID: %s\n" "arq Worker" "$$(cat $(WORKER_PID))"; \
	else \
		printf "  \033[31m✗\033[0m %-20s\n" "arq Worker"; \
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

convert-gcf: ## 转换数据集为 GroupChatFormat (INPUT=path/to/data.json [LIMIT=N])
	@if [ -z "$(INPUT)" ]; then \
		echo "用法: make convert-gcf INPUT=data/basic_events_79ef7f17.json"; \
		echo "可选: LIMIT=5  SPLIT_FRAGS=8  SPLIT_TURNS=100"; \
		exit 1; \
	fi
	python -m pipeline.convert_to_gcf --input $(INPUT) --output data/gcf_all.json \
		$(if $(SPLIT_FRAGS),--split-threshold-fragments $(SPLIT_FRAGS)) \
		$(if $(SPLIT_TURNS),--split-threshold-turns $(SPLIT_TURNS)) \
		$(if $(LIMIT),--limit $(LIMIT))

generate-speaker-mappings: ## 用 LLM 批量生成说话人映射 (INPUT=path/to/data.json [MODEL=gpt-4o-mini])
	@if [ -z "$(INPUT)" ]; then \
		echo "用法: make generate-speaker-mappings INPUT=data/basic_events_79ef7f17.json"; \
		echo "可选: MODEL=gpt-4o-mini  CONCURRENCY=10  DRY_RUN=1"; \
		exit 1; \
	fi
	python -m pipeline.generate_speaker_mapping --input $(INPUT) --output data/speaker_mappings.json \
		--model $${MODEL:-gpt-4o-mini} \
		--concurrency $${CONCURRENCY:-10} \
		$(if $(DRY_RUN),--dry-run)

ingest-gcf: ## 批量灌入 GCF 数据 ([INPUT=data/gcf_all.json] [API_URL=...] [CONCURRENCY=5])
	python -m pipeline.ingest_gcf \
		--input $${INPUT:-data/gcf_all.json} \
		--api-url $${API_URL:-$(EVERMEMOS_URL)/api/v1/memories} \
		--concurrency $${CONCURRENCY:-5}

run-task: ## 运行分析任务 (TASK=relationships|profiling|timeline|suggestions USER_ID=xxx)
	@if [ -z "$(TASK)" ] || [ -z "$(USER_ID)" ]; then \
		echo "用法: make run-task TASK=relationships USER_ID=user123"; \
		echo "任务类型: relationships | profiling | timeline | suggestions"; \
		echo "可选: FOCUS_PERSON=xxx  START_DATE=xxx  END_DATE=xxx  KEYWORDS=\"k1 k2\""; \
		exit 1; \
	fi
	python -m agent.cli $(TASK) --user-id $(USER_ID) \
		$(if $(FOCUS_PERSON),--focus-person $(FOCUS_PERSON)) \
		$(if $(START_DATE),--start-date $(START_DATE)) \
		$(if $(END_DATE),--end-date $(END_DATE)) \
		$(if $(KEYWORDS),--keywords $(KEYWORDS))

lint: ## 运行代码检查
	ruff check .
	ruff format --check .

test: ## 运行测试
	pytest

clean: ## 清理构建产物和运行时文件
	rm -f data/gcf_all.json
	rm -f $(EVERMEMOS_PID) $(WORKER_PID)
	rm -f pipeline/ingestion_progress.json
	find . -type d -name __pycache__ -not -path './EverMemOS/*' -not -path './opencode/*' -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ 已清理"
