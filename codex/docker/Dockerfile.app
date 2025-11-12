FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CODEX_ENV=live

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
COPY prompts ./prompts
COPY configs ./configs
COPY taxonomy ./taxonomy
COPY docs ./docs
COPY scripts ./scripts

RUN pip install --upgrade pip \
    && pip install .

EXPOSE 8000

CMD ["uvicorn", "codex.app:app", "--host", "0.0.0.0", "--port", "8000"]
