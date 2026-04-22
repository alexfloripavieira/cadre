FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential curl \
 && rm -rf /var/lib/apt/lists/*

COPY services/runtime/pyproject.toml /app/services/runtime/pyproject.toml
COPY services/runtime/cadre /app/services/runtime/cadre

WORKDIR /app/services/runtime

RUN pip install --upgrade pip \
 && pip install -e ".[dev]" || pip install fastapi uvicorn pydantic litellm

EXPOSE 8000

CMD ["uvicorn", "cadre.api:app", "--host", "0.0.0.0", "--port", "8000"]
