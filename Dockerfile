FROM python:3.12-slim AS base
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

FROM base AS poetry-exporter
WORKDIR /tmp
COPY poetry.lock pyproject.toml ./
RUN pip install --no-cache-dir poetry>=2.0.0 \
    && poetry self add poetry-plugin-export \
    && poetry export -f requirements.txt --without-hashes > requirements.txt

FROM base AS builder
COPY --from=poetry-exporter /tmp/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.12-slim AS runner
LABEL maintainer="106-"
LABEL description="Futaba to 2ch DAT format converter"
LABEL version="1.0"

RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash appuser

COPY --from=builder --chown=1000:1000 /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH

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