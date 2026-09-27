.PHONY: up install docker-up docker-down

install:
	uv sync

up: install
	uv run reflex run

docker-up:
	docker compose -f docker/docker-compose.yaml --env-file .env up -d --build

docker-down:
	docker compose -f docker/docker-compose.yaml --env-file .env down
