VERSION := $(shell grep -o '".*"' const.py | tr -d '"')

dev:
	uv run uvicorn main:app --reload

setup:
	uv sync --frozen
	uv run crawl4ai-setup
	uv run crawl4ai-doctor

builder:
	docker buildx create --name aisearch-builder

destroy:
	docker buildx rm aisearch-builder

build:
	docker buildx build --builder aisearch-builder \
	--platform linux/amd64,linux/arm64 \
	-t xxnuo/aisearch:$(VERSION) .
	docker tag xxnuo/aisearch:$(VERSION) xxnuo/aisearch:latest
	
test:
	docker compose --env-file .env up

push:
	docker push xxnuo/aisearch:$(VERSION)
	docker push xxnuo/aisearch:latest

default: dev

.PHONY: dev prod default
