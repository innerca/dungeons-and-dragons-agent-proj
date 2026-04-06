PROJECT_ROOT := $(shell pwd)
PROTO_DIR := $(PROJECT_ROOT)/proto
GATEWAY_GEN := $(PROJECT_ROOT)/gateway/gen
GAMESERVER_GEN := $(PROJECT_ROOT)/gameserver/gen
GOPATH_BIN := $(shell go env GOPATH)/bin

export GO111MODULE=on
export PATH := $(GOPATH_BIN):$(PATH)

.PHONY: proto-gen proto-go proto-py clean dev dev-down dev-logs help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

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

dev: ## Start all services via Docker Compose
	docker compose up --build

dev-down: ## Stop all Docker Compose services
	docker compose down

dev-logs: ## Tail logs from all Docker Compose services
	docker compose logs -f

dev-gateway: ## Start Gateway only (local)
	cd gateway && GO111MODULE=on go run cmd/gateway/main.go

dev-gameserver: ## Start GameServer only (local)
	cd gameserver && PYTHONPATH=src:gen uv run python -m gameserver.main

dev-frontend: ## Start Frontend only (local)
	cd frontend && npm run dev
