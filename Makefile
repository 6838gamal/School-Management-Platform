# ============================================================
# School Management Platform — Developer shortcuts
# ============================================================

.PHONY: install dev test lint migrate up down patch

install:            ## Install all dependencies
	pip install -r requirements.txt -r requirements-dev.txt

dev:                ## Run the dev server with auto-reload
	uvicorn app.main:app --reload --port 8000

test:               ## Run unit tests
	python -m pytest tests -v

lint:               ## Lint with Ruff
	ruff check app tests

migrate:            ## Apply database migrations
	alembic upgrade head

up:                 ## Start full stack via Docker Compose
	docker compose up -d --build

down:               ## Stop Docker Compose stack
	docker compose down
