.PHONY: play play-tui play-web test test-all bench clean setup coverage lint format check

play:
	uv run python main.py

play-tui:
	uv run python tui.py

play-web:
	uv run python web.py

test:
	uv run pytest -v -m "not slow"

test-all:
	uv run pytest -v

bench:
	uv run python ai_benchmark.py --strategy optimal --games 200

setup:
	uv sync --extra dev

setup-tui: setup
	uv sync --extra dev --extra tui

setup-web: setup
	uv sync --extra dev --extra web

setup-all:
	uv sync --extra dev --extra tui --extra web

lint:
	uv run ruff check .

format:
	uv run ruff format .

check:
	uv run ruff check . && uv run ruff format --check .

coverage:
	uv run pytest -m "not slow" --cov --cov-report=term-missing --cov-report=html

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
