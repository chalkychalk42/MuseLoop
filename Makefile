.PHONY: setup run test lint format typecheck docker-build docker-run clean

setup:
	uv sync

run:
	uv run museloop run $(BRIEF)

test:
	uv run pytest tests/ -v

test-unit:
	uv run pytest tests/unit/ -v

test-integration:
	uv run pytest tests/integration/ -v

test-cov:
	uv run pytest tests/ -v --cov=museloop --cov-report=html

lint:
	uv run ruff check src/ tests/

format:
	uv run ruff format src/ tests/

typecheck:
	uv run mypy src/

docker-build:
	docker compose build

docker-run:
	docker compose up

clean:
	rm -rf output/ dist/ build/ .coverage htmlcov/ .mypy_cache/ .pytest_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
