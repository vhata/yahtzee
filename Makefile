.PHONY: play test test-all bench clean setup

play:
	uv run python main.py

test:
	uv run pytest -v -m "not slow"

test-all:
	uv run pytest -v

bench:
	uv run python ai_benchmark.py --strategy optimal --games 200

setup:
	uv sync --extra dev

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
