FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/ src/
COPY gen/ gen/
COPY config/ config/

RUN uv sync --frozen --no-dev

FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/gen /app/gen
COPY --from=builder /app/config /app/config

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src:/app/gen"
ENV PYTHONUNBUFFERED=1

EXPOSE 50051

CMD ["python", "-m", "gameserver.main"]
