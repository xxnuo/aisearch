dev:
	uv run uvicorn main:app --reload \
		--host 0.0.0.0 \
		--port 8000 \
		--env-file .env.dev \
		--log-level debug

prod:
	uv run uvicorn main:app \
		--host 0.0.0.0 \
		--port 8000 \
		--log-level warning

setup:
	uv sync --frozen
	uv run crawl4ai-setup
	uv run crawl4ai-doctor

default: dev

.PHONY: dev prod default
