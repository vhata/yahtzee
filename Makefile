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
	uv pip install "textual>=0.50.0"

setup-web: setup
	uv pip install "flask>=3.0.0" "flask-sock>=0.7.0"

setup-all:
	uv sync --extra dev
	uv pip install "textual>=0.50.0" "flask>=3.0.0" "flask-sock>=0.7.0"

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
