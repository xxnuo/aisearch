dev:
	uv run main.py

setup:
	uv sync --frozen
	uv run crawl4ai-setup
	uv run crawl4ai-doctor

default: dev

.PHONY: dev prod default
