FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CODEX_ENV=live \
    CODEX_CONFIG_DIR=/app/configs

WORKDIR /app

COPY pyproject.toml ./

RUN apt-get update \
    && apt-get install -y --no-install-recommends wget \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --upgrade pip \
    && pip install --no-cache-dir \
        "fastapi==0.115.2" \
        "starlette==0.40.0" \
        "uvicorn[standard]==0.32.0" \
        "anyio==4.6.2.post1" \
        "prometheus-client>=0.20.0,<0.22" \
        "PyYAML>=6.0.2,<7"

COPY src ./src
COPY prompts ./prompts
COPY configs ./configs
COPY taxonomy ./taxonomy
COPY docs ./docs
COPY scripts ./scripts

RUN pip install --no-cache-dir .

# Offline build example:
# COPY vendor_wheels /tmp/vendor_wheels
# RUN pip install --no-index --find-links=/tmp/vendor_wheels \
#     fastapi==0.115.2 starlette==0.40.0 uvicorn[standard]==0.32.0 anyio==4.6.2.post1 \
#     "prometheus-client>=0.20.0,<0.22" "PyYAML>=6.0.2,<7"
# RUN pip install --no-index --find-links=/tmp/vendor_wheels .

EXPOSE 8000

CMD ["uvicorn", "codex.app:app", "--host", "0.0.0.0", "--port", "8000"]
