.PHONY: help install dev test lint format migrate migrate-create run clean

help:
	@echo "RMS Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install      - Install dependencies"
	@echo "  make install-dev  - Install with dev dependencies"
	@echo ""
	@echo "Database:"
	@echo "  make migrate      - Run pending migrations"
	@echo "  make migrate-make - Create new migration (use NAME=description)"
	@echo ""
	@echo "Development:"
	@echo "  make run          - Start dev server"
	@echo "  make test         - Run tests"
	@echo "  make test-watch   - Run tests in watch mode"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint         - Run linters (ruff, mypy)"
	@echo "  make format       - Format code (black, ruff)"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean        - Remove build artifacts and caches"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

migrate:
	alembic upgrade head

migrate-make:
	@if [ -z "$(NAME)" ]; then \
		echo "Usage: make migrate-make NAME='description of migration'"; \
		exit 1; \
	fi
	alembic revision --autogenerate -m "$(NAME)"

run:
	python -m app.main

test:
	pytest tests/ -v

test-watch:
	pytest tests/ -v --tb=short -s

lint:
	ruff check app tests
	mypy app

format:
	black app tests
	ruff check --fix app tests

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name *.egg-info -exec rm -rf {} +
	find . -type f -name .DS_Store -delete
