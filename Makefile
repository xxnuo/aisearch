VERSION := $(shell grep -o '".*"' const.py | tr -d '"')

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
	docker run -it --rm xxnuo/aisearch:latest

push:
	docker buildx create --name aisearch-builder
	docker buildx build --builder aisearch-builder \
	--platform linux/amd64,linux/arm64 \
	-t xxnuo/aisearch:$(VERSION) \
	-t xxnuo/aisearch:latest \
	-t registry.lazycat.cloud/aisearch:$(VERSION) \
	-t registry.lazycat.cloud/aisearch:latest \
	--push .
	docker buildx rm aisearch-builder

default: dev

.PHONY: dev prod default
