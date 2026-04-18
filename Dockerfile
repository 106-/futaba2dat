FROM python:3.12-slim AS base
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

FROM base AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.12-slim AS runner
LABEL maintainer="106-"
LABEL description="Futaba to 2ch DAT format converter"
LABEL version="1.0"

RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash appuser

COPY --from=builder --chown=1000:1000 /app/.venv /app/.venv
ENV PATH=/app/.venv/bin:$PATH

WORKDIR /app

COPY --chown=1000:1000 ./futaba2dat ./futaba2dat
COPY --chown=1000:1000 ./static ./static
COPY --chown=1000:1000 ./templates ./templates

USER 1000:1000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:80/', timeout=5)" || exit 1

EXPOSE 80

ENTRYPOINT ["python", "-m", "uvicorn"]
CMD ["futaba2dat.main:app", "--host", "0.0.0.0", "--port", "80", "--proxy-headers", "--forwarded-allow-ips", "*"]
