# Codex v2.2

Codex is a risk and news intelligence module that validates trading features, aggregates sentiment, and requests
LLM verdicts with a strict JSON contract. This repository contains the reference implementation for version 2.2 of the
service, including configuration, prompts, docker manifests, and automated tests that cover the major acceptance
criteria.

The service is model-agnostic and ships with Claude Sonnet as the primary provider. Alternative providers can be
configured without code changes.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[test]
cp .env.example .env  # populate provider credentials via vault/sops
python scripts/check_config.py
pytest
```

To run the API locally:

```bash
uvicorn codex.app:app --reload
```

## Docker

The repository ships with production-ready Dockerfiles for the API and the optional news ingest worker. A local stack is
available via docker-compose:

```bash
docker compose up --build
```

This starts the FastAPI service, the ingest worker, Redis, and Prometheus. Health is exposed at `http://localhost:8000/health`
and metrics at `http://localhost:8000/metrics`.

## Tests

The suite covers unit, integration, stress, and property tests.

```bash
PYTHONPATH=src pytest
```
