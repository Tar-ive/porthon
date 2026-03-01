FRONTEND_DIR := src/frontend
BACKEND_DIR  := src/backend
STATIC_DIR   := $(BACKEND_DIR)/static

.PHONY: build dev install clean

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

## Remove build artifacts
clean:
	rm -rf $(STATIC_DIR)
