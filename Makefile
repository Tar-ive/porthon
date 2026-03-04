FRONTEND_DIR := src/frontend
BACKEND_DIR  := src/backend
STATIC_DIR   := $(BACKEND_DIR)/static

.PHONY: build dev install clean test test-live test-live-kg

## Install all dependencies
install:
	cd $(FRONTEND_DIR) && pnpm install
	cd $(BACKEND_DIR) && uv sync

## Build frontend — vite writes output directly to backend/static
build:
	cd $(FRONTEND_DIR) && pnpm build

## Build frontend then start the FastAPI server
dev: build
	cd $(BACKEND_DIR) && uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

## Run backend fast tests (default)
test:
	cd $(BACKEND_DIR) && uv run pytest -m "not live" -q

## Run backend live integration tests
test-live:
	cd $(BACKEND_DIR) && RUN_LIVE_TESTS=1 uv run pytest -m live -v -s

## Run live KG integration tests (requires Neo4j/Qdrant + binding keys)
test-live-kg:
	cd $(BACKEND_DIR) && RUN_LIVE_TESTS=1 RUN_LIVE_KG_TESTS=1 uv run pytest tests/live/test_live_kg.py -v -s

## Remove build artifacts
clean:
	rm -rf $(STATIC_DIR)
