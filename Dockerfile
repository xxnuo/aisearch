FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH"

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

RUN python3 -m playwright install --with-deps --force chromium
RUN crawl4ai-setup

COPY . .

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --compile-bytecode --no-dev

EXPOSE 3000

RUN apt update && apt install -y curl

ENTRYPOINT [ "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3000" ]