.PHONY: setup codex-bin codex-config install help

PROJECT_DIR := $(shell pwd)
CODEX_BIN_DIR := $(PROJECT_DIR)/.codex-bin
CODEX_BIN := $(CODEX_BIN_DIR)/codex
CODEX_HOME := $(PROJECT_DIR)/.codex-local
CONFIG_FILE := $(CODEX_HOME)/config.toml

# Detect OS and arch
UNAME_S := $(shell uname -s)
UNAME_M := $(shell uname -m)

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: codex-bin codex-config install ## Full setup: download codex, generate config, install deps
	@echo ""
	@echo "Setup complete! Add these to your shell environment:"
	@echo "  export CODEX_BIN=$(CODEX_BIN)"
	@echo "  export CODEX_HOME=$(CODEX_HOME)"
	@echo "  export OPENAI_BASE_URL=<your-uniapi-url>"
	@echo "  export OPENAI_API_KEY=<your-uniapi-key>"
	@echo ""
	@echo "Or use the .env file: source .env"

codex-bin: $(CODEX_BIN) ## Download Codex binary via npm

$(CODEX_BIN):
	@echo "Downloading Codex binary..."
	@mkdir -p $(CODEX_BIN_DIR)
	@npm pack @openai/codex --pack-destination $(CODEX_BIN_DIR) 2>/dev/null
	@cd $(CODEX_BIN_DIR) && tar xzf openai-codex-*.tgz --strip-components=1 && rm -f openai-codex-*.tgz
	@# Find the actual binary inside the npm package
	@if [ -f "$(CODEX_BIN_DIR)/bin/codex" ]; then \
		ln -sf $(CODEX_BIN_DIR)/bin/codex $(CODEX_BIN); \
	elif [ -f "$(CODEX_BIN_DIR)/bin/codex.js" ]; then \
		echo '#!/bin/sh' > $(CODEX_BIN) && echo 'exec node "$(CODEX_BIN_DIR)/bin/codex.js" "$$@"' >> $(CODEX_BIN) && chmod +x $(CODEX_BIN); \
	else \
		echo "Codex binary not found in npm package. Trying npx..."; \
		echo '#!/bin/sh' > $(CODEX_BIN) && echo 'exec npx -y @openai/codex "$$@"' >> $(CODEX_BIN) && chmod +x $(CODEX_BIN); \
	fi
	@echo "Codex binary installed at $(CODEX_BIN)"

codex-config: $(CONFIG_FILE) ## Generate local Codex config with EverMemOS MCP

$(CONFIG_FILE):
	@echo "Generating Codex config..."
	@mkdir -p $(CODEX_HOME)
	@cat > $(CONFIG_FILE) <<'TOML'
# Codex local config for EverMemOS integration
# CODEX_HOME should point to this directory: $(CODEX_HOME)

[mcp_servers.evermemos]
command = "python"
args = ["-m", "mcp_server.server"]
TOML
	@echo "Config written to $(CONFIG_FILE)"

install: ## Install Python dependencies
	@pip install -e codex/sdk/python/ 2>/dev/null || true
	@pip install -e . 2>/dev/null || true
	@echo "Python packages installed"

env-file: ## Generate .env file template
	@cat > .env <<'EOF'
# Codex Agent environment variables
export CODEX_BIN=$(PROJECT_DIR)/.codex-bin/codex
export CODEX_HOME=$(PROJECT_DIR)/.codex-local
export OPENAI_BASE_URL=https://your-uniapi.com/v1
export OPENAI_API_KEY=sk-your-key-here
export CODEX_MODEL=gpt-4o
EOF
	@echo ".env file created. Edit it with your UniAPI credentials, then: source .env"

clean: ## Remove downloaded Codex binary and local config
	rm -rf $(CODEX_BIN_DIR) $(CODEX_HOME)
	@echo "Cleaned up"
