.PHONY: help install dev lint test build clean docker-build run

help:
	@echo "CineOps Guardian — Development Commands"
	@echo "========================================"
	@echo "make install      Install backend and frontend dependencies"
	@echo "make dev          Run backend and frontend concurrently"
	@echo "make test         Run backend tests"
	@echo "make lint         Run backend linting (ruff)"
	@echo "make build        Build frontend and bundle static assets"
	@echo "make docker-build Build unified production Docker container"
	@echo "make clean        Clean build and cache artifacts"

install:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -e ".[dev]"
	npm install

dev:
	.venv/bin/uvicorn backend.app.main:app --reload --port 8080 & cd frontend && npm run dev

lint:
	.venv/bin/ruff check backend/
	.venv/bin/ruff format --check backend/

test:
	.venv/bin/pytest backend/tests/

build:
	cd frontend && npm run build

docker-build:
	docker build -t cineops-guardian:latest .

clean:
	rm -rf .venv node_modules frontend/node_modules frontend/dist .pytest_cache .ruff_cache
