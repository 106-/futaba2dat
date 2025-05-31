FROM python:3.12 AS exporter
COPY ./poetry.lock /poetry.lock
COPY ./pyproject.toml /pyproject.toml
RUN pip install poetry \
    && poetry self add poetry-plugin-export
RUN poetry export -f requirements.txt --without-hashes > requirements.txt

FROM python:3.12 AS builder
COPY --from=exporter /requirements.txt /requirements.txt
RUN pip3 install -r requirements.txt

FROM python:3.12-slim AS runner
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn
WORKDIR /app
COPY ./futaba2dat /app/futaba2dat
COPY ./static /app/static
COPY ./templates /app/templates
EXPOSE 80
CMD ["/usr/local/bin/uvicorn", "futaba2dat.main:app", "--host", "0.0.0.0", "--port", "80", "--proxy-headers", "--forwarded-allow-ips", "*"]