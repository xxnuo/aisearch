FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Install base dependencies (cached layer)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Install Playwright browsers + system deps (cached layer if pyproject/lock don't change)
# Combine with crawl4ai setup if possible, or keep separate if needed
RUN uv run python -m playwright install --with-deps --force chromium
RUN uv run crawl4ai-setup

# Copy application code
COPY . .

# Install project dependencies (including the project itself)
# This layer changes when code or deps change
RUN uv sync --frozen --no-dev

# Set PATH to include virtual environment binaries
# This is good practice, especially if you might `docker exec` into the container
# `uv run` in ENTRYPOINT makes this less critical for the entrypoint itself, but still useful.
ENV PATH="/app/.venv/bin:$PATH"

# PYTHONPATH is often unnecessary when WORKDIR is set correctly, removing it.
# ENV PYTHONPATH=/app

EXPOSE 3000

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

# Use uv run to execute uvicorn within the virtual environment
# Uvicorn should find `main.py` in the current WORKDIR (/app)
ENTRYPOINT [ "uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3000" ]