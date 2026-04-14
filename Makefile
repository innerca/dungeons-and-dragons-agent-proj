PROJECT_ROOT := $(shell pwd)
PROTO_DIR := $(PROJECT_ROOT)/proto
GATEWAY_GEN := $(PROJECT_ROOT)/gateway/gen
GAMESERVER_GEN := $(PROJECT_ROOT)/gameserver/gen
GOPATH_BIN := $(shell go env GOPATH)/bin

export GO111MODULE=on
export PATH := $(GOPATH_BIN):$(PATH)

.PHONY: proto-gen proto-go proto-py clean dev dev-down dev-logs help ingest-novels verify-vectordb start stop db-init test test-gateway test-gameserver test-frontend

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# --- One-click scripts ---

start: ## Start all services (auto-detect Docker/local)
	bash scripts/start.sh

stop: ## Stop all services
	bash scripts/stop.sh

start-docker: ## Start via Docker Compose
	bash scripts/start.sh docker

start-local: ## Start in local development mode
	bash scripts/start.sh local

# --- Proto generation ---

proto-gen: proto-go proto-py ## Generate all gRPC code

proto-go: ## Generate Go gRPC code
	@echo "Generating Go gRPC code..."
	@mkdir -p $(GATEWAY_GEN)/game/v1
	PATH=$(GOPATH_BIN):$$PATH protoc \
		--proto_path=$(PROTO_DIR) \
		--go_out=$(GATEWAY_GEN) \
		--go_opt=paths=source_relative \
		--go-grpc_out=$(GATEWAY_GEN) \
		--go-grpc_opt=paths=source_relative \
		game/v1/game_service.proto

proto-py: ## Generate Python gRPC code
	@echo "Generating Python gRPC code..."
	@mkdir -p $(GAMESERVER_GEN)/game/v1
	cd gameserver && uv run python -m grpc_tools.protoc \
		--proto_path=$(PROTO_DIR) \
		--python_out=$(GAMESERVER_GEN) \
		--grpc_python_out=$(GAMESERVER_GEN) \
		game/v1/game_service.proto
	@touch $(GAMESERVER_GEN)/__init__.py
	@touch $(GAMESERVER_GEN)/game/__init__.py
	@touch $(GAMESERVER_GEN)/game/v1/__init__.py

clean: ## Clean generated files
	rm -rf $(GATEWAY_GEN)/game
	rm -rf $(GAMESERVER_GEN)/game

# --- Docker ---

dev: ## Start all services via Docker Compose
	docker compose up --build

dev-down: ## Stop all Docker Compose services
	docker compose down

dev-logs: ## Tail logs from all Docker Compose services
	docker compose logs -f

# --- Local dev (individual services) ---

dev-gateway: ## Start Gateway only (local)
	cd gateway && REDIS_URL=redis://localhost:6379/0 GO111MODULE=on go run cmd/gateway/main.go

dev-gameserver: ## Start GameServer only (local)
	cd gameserver && PYTHONPATH=src:gen DATABASE_URL=postgresql://sao:sao_dev_password@localhost:5432/sao_game REDIS_URL=redis://localhost:6379/0 HF_ENDPOINT=https://hf-mirror.com uv run python -m gameserver.main

dev-frontend: ## Start Frontend only (local)
	cd frontend && npm run dev

# --- Testing ---

test: test-gateway test-gameserver test-frontend ## Run all tests

install-gameserver: ## Install GameServer dependencies
	@echo "Installing GameServer dependencies..."
	cd gameserver && uv sync --frozen
	@echo "Installation complete."

test-gateway: ## Run Gateway (Go) tests
	@echo "Running Gateway tests..."
	cd gateway && go test -v -race -coverprofile=coverage.out ./...
	@echo "Gateway tests completed."

test-gameserver: ## Run GameServer (Python) tests
	@echo "Running GameServer tests..."
	cd gameserver && uv run pytest tests/ -v --tb=short
	@echo "GameServer tests completed."

test-frontend: ## Run Frontend type check and build
	@echo "Running Frontend checks..."
	cd frontend && npx tsc --noEmit
	cd frontend && npm run build
	@echo "Frontend checks completed."

# --- Database ---

db-init: ## Initialize database schema (requires running PostgreSQL)
	PGPASSWORD=sao_dev_password psql -h localhost -U sao -d sao_game -f gameserver/scripts/init_db.sql

# --- Knowledge base ---

ingest-novels: ## Ingest SAO novels into ChromaDB
	cd gameserver && HF_ENDPOINT=https://hf-mirror.com uv run python -m scripts.ingest_novels

verify-vectordb: ## Verify ChromaDB ingestion results
	cd gameserver && HF_ENDPOINT=https://hf-mirror.com uv run python -m scripts.verify_vectordb
