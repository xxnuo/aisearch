FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV DEBIAN_FRONTEND=noninteractive

RUN sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list.d/debian.sources

RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt/lists \
    apt-get update && \
    apt-get install -y --no-install-recommends curl

RUN mkdir -p /root/.config/uv && \
    printf '%s\n' \
    '[[index]]' \
    'url = "https://mirrors.ustc.edu.cn/pypi/simple"' \
    'default = true' \
    > /root/.config/uv/uv.toml

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH"

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev
    
RUN --mount=type=cache,target=/root/.crawl4ai \
    --mount=type=cache,target=/root/.cache/ms-playwright \
    crawl4ai-setup

COPY . .

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --compile-bytecode --no-dev

EXPOSE 3000

ENTRYPOINT [ "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3000", "--log-level", "warning" ]