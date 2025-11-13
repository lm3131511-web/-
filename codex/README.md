# Codex v2.2

Codex is a risk and news intelligence module that validates trading features, aggregates sentiment, and requests
LLM verdicts with a strict JSON contract. This repository contains the reference implementation for version 2.2 of the
service, including configuration, prompts, docker manifests, and automated tests that cover the major acceptance
criteria.

The service is model-agnostic and ships with Claude Sonnet as the primary provider. Alternative providers can be
configured without code changes.

## Project layout
- Код пакета: `codex/src/codex/...`
- Конфиги: `codex/configs/*.yaml`
- Промпты и схемы: `codex/prompts/...`
- Документация: `codex/docs/...`
- Тесты: `codex/tests/...`
- Инфраструктура: `codex/docker/*`, `codex/docker-compose.yml`

## Quick start (локально)
# Команды предполагают запуск из корня монорепозитория (на уровень выше `codex/`).

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[test]
cp codex/.env.example .env  # populate provider credentials via vault/sops
PYTHONPATH=codex/src python codex/scripts/check_config.py
PYTHONPATH=codex/src pytest -q
uvicorn codex.app:app --reload
curl -s http://localhost:8000/health
```

## Docker
```bash
docker compose -f codex/docker-compose.yml up --build
curl -s http://localhost:8000/health
curl -s http://localhost:8000/metrics | head
```

## Data directories
Рабочие файлы создаются на лету:
- `codex/data/logs/decisions.jsonl`
- `codex/data/logs/news_ingest.jsonl`
- `codex/data/cache/codex_cache.db`

В репозитории лежат `.gitkeep`, чтобы каталоги существовали в чистом клоне.

## Tests

The suite covers unit, integration, stress, and property tests.

```bash
PYTHONPATH=codex/src pytest
```
