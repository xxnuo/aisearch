VERSION := $(shell grep -o 'version = ".*"' pyproject.toml | cut -d'"' -f2)

dev:
	uv run uvicorn main:app --reload

setup:
	uv sync --frozen
	uv run crawl4ai-setup
	uv run crawl4ai-doctor

build:
	docker build --load \
	-t xxnuo/aisearch:$(VERSION) \
	-t xxnuo/aisearch:latest \
	-t registry.lazycat.cloud/aisearch:$(VERSION) \
	-t registry.lazycat.cloud/aisearch:latest \
	.

test:
	docker compose up

push-prepare:
	docker buildx create --name aisearch-builder

push:
	docker buildx build --builder aisearch-builder \
	--platform linux/amd64,linux/arm64 \
	-t xxnuo/aisearch:$(VERSION) \
	-t xxnuo/aisearch:latest \
	--push .

push-lm:
	docker buildx build --builder aisearch-builder \
	--platform linux/amd64,linux/arm64 \
	-t registry.lazycat.cloud/aisearch:$(VERSION) \
	-t registry.lazycat.cloud/aisearch:latest \
	--push .

push-clean:
	docker buildx rm aisearch-builder

default: dev

.PHONY: dev prod default
