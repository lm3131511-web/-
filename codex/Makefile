.PHONY: up down rebuild logs test

up:
	docker compose up -d

down:
	docker compose down

rebuild:
	docker compose down || true
	docker compose build --no-cache
	docker compose up -d

logs:
	docker compose logs -f codex-app

test:
	PYTHONPATH=src pytest -q
